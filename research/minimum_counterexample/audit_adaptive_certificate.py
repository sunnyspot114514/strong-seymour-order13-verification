#!/usr/bin/env python3
"""Strictly audit one adaptive SAT-certificate tree."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


HEADER = re.compile(r"^p cnf ([1-9][0-9]*) ([0-9]+)$")
ROUND_DIRECTORY = re.compile(r"^round_([0-9]+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return payload


def require_file(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"missing required file: {path}")


def require_sha256(path: Path, expected: object, label: str) -> str:
    if not isinstance(expected, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected
    ):
        raise ValueError(f"{label} has no valid SHA-256")
    actual = sha256(path)
    if actual != expected:
        raise ValueError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def read_cubes(path: Path) -> list[tuple[int, ...]]:
    require_file(path)
    cubes: list[tuple[int, ...]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="ascii").splitlines(), start=1
    ):
        if not line.startswith("a "):
            continue
        tokens = line.split()
        if len(tokens) < 2 or tokens[0] != "a" or tokens[-1] != "0":
            raise ValueError(f"malformed cube at {path}:{line_number}")
        try:
            cube = tuple(int(token) for token in tokens[1:-1])
        except ValueError as error:
            raise ValueError(
                f"non-integer cube literal at {path}:{line_number}"
            ) from error
        assignments: dict[int, bool] = {}
        for literal in cube:
            if literal == 0:
                raise ValueError(f"zero cube literal at {path}:{line_number}")
            variable = abs(literal)
            value = literal > 0
            if variable in assignments:
                raise ValueError(
                    f"duplicate/complementary literal at {path}:{line_number}"
                )
            assignments[variable] = value
        cubes.append(cube)
    if not cubes:
        raise ValueError(f"cube file has no a-lines: {path}")
    return cubes


def canonical(cube: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(cube, key=abs))


@functools.lru_cache(maxsize=None)
def covers_boolean_space(cubes: tuple[tuple[int, ...], ...]) -> bool:
    if any(not cube for cube in cubes):
        return True
    if not cubes:
        return False
    variable = abs(min(cubes, key=len)[0])
    results = []
    for value in (False, True):
        literal = variable if value else -variable
        opposite = -literal
        restricted: set[tuple[int, ...]] = set()
        for cube in cubes:
            if opposite in cube:
                continue
            if literal in cube:
                restricted.add(tuple(item for item in cube if item != literal))
            else:
                restricted.add(cube)
        results.append(covers_boolean_space(tuple(sorted(restricted))))
    return all(results)


def verify_coverage(
    coverage: dict[str, Any],
    parents: list[tuple[int, ...]],
    children: list[tuple[int, ...]],
    parents_path: Path,
    children_path: Path,
) -> None:
    if coverage.get("verified") is not True:
        raise ValueError("coverage is not marked verified")
    if coverage.get("parents_sha256") != sha256(parents_path):
        raise ValueError("coverage does not bind parents.cubes")
    if coverage.get("children_sha256") != sha256(children_path):
        raise ValueError("coverage does not bind children.cubes")
    if int(coverage.get("parent_count", -1)) != len(parents):
        raise ValueError("coverage parent_count mismatch")
    if int(coverage.get("child_count", -1)) != len(children):
        raise ValueError("coverage child_count mismatch")
    records = coverage.get("records")
    if not isinstance(records, list) or len(records) != len(parents):
        raise ValueError("coverage records do not enumerate every parent")

    unused = set(range(len(children)))
    for parent_index, parent in enumerate(parents):
        record = records[parent_index]
        if not isinstance(record, dict):
            raise ValueError("coverage record is not an object")
        parent_set = set(parent)
        child_indices = [
            index
            for index, child in enumerate(children)
            if parent_set.issubset(child)
        ]
        if not child_indices:
            raise ValueError(f"parent {parent_index} has no children")
        suffixes = []
        for index in child_indices:
            unused.discard(index)
            suffixes.append(
                canonical(
                    tuple(
                        literal
                        for literal in children[index]
                        if literal not in parent_set
                    )
                )
            )
        covered = covers_boolean_space(tuple(sorted(set(suffixes))))
        if (
            int(record.get("parent", -1)) != parent_index
            or int(record.get("child_count", -1)) != len(child_indices)
            or record.get("covered") is not True
            or not covered
        ):
            raise ValueError(f"coverage record {parent_index} is invalid")
    if unused:
        raise ValueError(f"{len(unused)} children match no parent")


def parse_parent_cnf(path: Path) -> tuple[list[str], int, int, int]:
    require_file(path)
    lines = path.read_text(encoding="ascii").splitlines()
    headers = [
        (index, HEADER.fullmatch(line))
        for index, line in enumerate(lines)
        if line.startswith("p ")
    ]
    if len(headers) != 1 or headers[0][1] is None:
        raise ValueError("parent CNF must have exactly one valid header")
    header_index, match = headers[0]
    assert match is not None
    variables, clauses = map(int, match.groups())
    actual_clauses = sum(
        bool(line) and not line.startswith(("c", "p")) for line in lines
    )
    if actual_clauses != clauses:
        raise ValueError("parent CNF clause count mismatch")
    return lines, header_index, variables, clauses


def leaf_cnf_sha256(
    parent: tuple[list[str], int, int, int], cube: tuple[int, ...]
) -> str:
    lines, header_index, variables, clauses = parent
    if any(abs(literal) > variables for literal in cube):
        raise ValueError("cube literal exceeds parent CNF variable count")
    leaf_lines = list(lines)
    leaf_lines[header_index] = f"p cnf {variables} {clauses + len(cube)}"
    payload = (
        "\n".join(leaf_lines)
        + "\n"
        + "".join(f"{literal} 0\n" for literal in cube)
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def exact_int_set(records: object, label: str) -> tuple[list[dict[str, Any]], set[int]]:
    if not isinstance(records, list):
        raise ValueError(f"{label} is not a list")
    typed: list[dict[str, Any]] = []
    indices: set[int] = set()
    for item in records:
        if not isinstance(item, dict):
            raise ValueError(f"{label} contains a non-object")
        index = int(item.get("cube_index", -1))
        if index < 0 or index in indices:
            raise ValueError(f"{label} contains an invalid/duplicate cube index")
        indices.add(index)
        typed.append(item)
    return typed, indices


def verify_certificate_manifest(
    path: Path,
    manifest: dict[str, Any],
    parent_cnf: Path,
    parent_cnf_sha256: str,
    parent_cnf_parsed: tuple[list[str], int, int, int],
    children_path: Path,
    children: list[tuple[int, ...]],
    coverage_path: Path,
    round_solver_kind: str | None,
    root_proof_mode: str,
) -> tuple[list[int], int, int]:
    if manifest.get("base_cnf_sha256") != parent_cnf_sha256:
        raise ValueError(f"certificate manifest does not bind {parent_cnf}")
    if manifest.get("cubes_sha256") != sha256(children_path):
        raise ValueError("certificate manifest does not bind children.cubes")
    if manifest.get("coverage_sha256") != sha256(coverage_path):
        raise ValueError("certificate manifest does not bind coverage.json")
    if manifest.get("complete_partition") is not True:
        raise ValueError("certificate manifest is not a complete partition")
    if int(manifest.get("total_cube_count", -1)) != len(children):
        raise ValueError("certificate total_cube_count mismatch")
    if int(manifest.get("shards", -1)) != 1 or int(
        manifest.get("shard_index", -1)
    ) != 0:
        raise ValueError("adaptive certificate must be one complete shard")
    certificate_solver_kind = manifest.get("solver_kind")
    if certificate_solver_kind not in (None, "gimsatul", "cadical", "kissat"):
        raise ValueError("certificate has an invalid solver_kind")
    if (
        round_solver_kind is not None
        and certificate_solver_kind not in (None, round_solver_kind)
    ):
        raise ValueError("certificate solver_kind mismatch")
    if manifest.get("proof_mode") not in (None, root_proof_mode):
        raise ValueError("certificate proof_mode mismatch")
    selected = manifest.get("selected_cube_indices")
    if selected != list(range(len(children))):
        raise ValueError("certificate selected indices are incomplete")

    records, verified = exact_int_set(manifest.get("records"), "records")
    failures, failed = exact_int_set(
        manifest.get("failed_cubes"), "failed_cubes"
    )
    all_indices = set(range(len(children)))
    if verified & failed or verified | failed != all_indices:
        raise ValueError("verified and failed indices do not partition children")
    if int(manifest.get("verified_cube_count", -1)) != len(records):
        raise ValueError("certificate verified_cube_count mismatch")

    expected_proofs: set[str] = set()
    for record in records:
        index = int(record["cube_index"])
        if record.get("literals") != list(children[index]):
            raise ValueError(f"cube {index} literal binding mismatch")
        if record.get("leaf_cnf_sha256") != leaf_cnf_sha256(
            parent_cnf_parsed, children[index]
        ):
            raise ValueError(f"cube {index} leaf CNF hash mismatch")
        if int(record.get("solver_exit", -1)) != 20:
            raise ValueError(f"cube {index} solver exit is not UNSAT")
        if int(record.get("extraction_exit", -1)) != 0:
            raise ValueError(f"cube {index} extraction exit is not zero")
        if int(record.get("verification_exit", -1)) != 0:
            raise ValueError(f"cube {index} verification exit is not zero")
        if record.get("proof_mode") not in (None, root_proof_mode):
            raise ValueError(f"cube {index} proof mode mismatch")
        if root_proof_mode == "rup" and (
            record.get("rup_only") is not True
            or record.get("rat_lemmas") not in (None, 0)
        ):
            raise ValueError(f"cube {index} is not a pure RUP proof")
        proof_name = record.get("compressed_core")
        if (
            not isinstance(proof_name, str)
            or Path(proof_name).name != proof_name
            or proof_name in expected_proofs
        ):
            raise ValueError(f"cube {index} has an invalid proof filename")
        if root_proof_mode == "rup" and not proof_name.endswith(
            ".core.rup.xz"
        ):
            raise ValueError(f"cube {index} has no RUP proof filename")
        proof = path.parent / proof_name
        require_file(proof)
        expected_bytes = int(record.get("compressed_core_bytes", -1))
        if expected_bytes <= 0 or proof.stat().st_size != expected_bytes:
            raise ValueError(f"cube {index} compressed proof size mismatch")
        require_sha256(
            proof,
            record.get("compressed_core_sha256"),
            f"cube {index} compressed proof",
        )
        if int(record.get("raw_proof_bytes", -1)) <= 0 or int(
            record.get("core_bytes", -1)
        ) <= 0:
            raise ValueError(f"cube {index} records an empty proof")
        expected_proofs.add(proof_name)

    actual_proofs = {item.name for item in path.parent.glob("*.xz")}
    if actual_proofs != expected_proofs:
        raise ValueError("certificate directory has missing or unbound proofs")
    return sorted(failed), len(records), len(failures)


def prune_uncommitted_rounds(tree: Path, committed_count: int) -> list[str]:
    removed = []
    for path in tree.glob("round_*"):
        match = ROUND_DIRECTORY.fullmatch(path.name)
        if match is None:
            continue
        if int(match.group(1)) <= committed_count:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(path.name)
    return sorted(removed)


def audit_tree(
    tree: Path,
    parent_cnf: Path,
    *,
    require_partial: bool = False,
    require_complete: bool = False,
    require_rup: bool = False,
    prune_uncommitted: bool = False,
) -> dict[str, Any]:
    if require_partial and require_complete:
        raise ValueError("cannot require both partial and complete state")
    manifest_path = tree / "adaptive_manifest.json"
    require_file(manifest_path)
    root = read_json(manifest_path)
    rounds = root.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        raise ValueError("adaptive manifest has no rounds")
    if int(root.get("round_count", -1)) != len(rounds):
        raise ValueError("adaptive round_count mismatch")

    removed = (
        prune_uncommitted_rounds(tree, len(rounds))
        if prune_uncommitted
        else []
    )
    actual_rounds: dict[int, str] = {}
    for path in tree.glob("round_*"):
        match = ROUND_DIRECTORY.fullmatch(path.name)
        if match is None:
            raise ValueError(f"invalid round path: {path}")
        round_number = int(match.group(1))
        if round_number in actual_rounds:
            raise ValueError(f"duplicate round number: {round_number}")
        actual_rounds[round_number] = path.name
    if set(actual_rounds) != set(range(1, len(rounds) + 1)):
        raise ValueError("round directories do not match committed manifest")

    verified = root.get("verified")
    if verified not in (True, False):
        raise ValueError("adaptive verified state is not boolean")
    if require_partial and verified is not False:
        raise ValueError("adaptive tree is not partial")
    if require_complete and verified is not True:
        raise ValueError("adaptive tree is not complete")
    if verified is False and root.get("reason") != "round limit reached":
        raise ValueError("partial adaptive tree has an invalid reason")
    if verified is True and "reason" in root:
        raise ValueError("complete adaptive tree unexpectedly has a reason")

    parent_cnf_sha256 = sha256(parent_cnf)
    if root.get("parent_cnf_sha256") != parent_cnf_sha256:
        raise ValueError("adaptive manifest does not bind parent CNF")
    parent_cnf_parsed = parse_parent_cnf(parent_cnf)
    solver_kind = root.get("solver_kind")
    declared_proof_mode = root.get("proof_mode")
    proof_mode = "rup" if declared_proof_mode is None else declared_proof_mode
    if solver_kind not in {None, "gimsatul", "cadical", "kissat"}:
        raise ValueError("invalid adaptive solver_kind")
    if proof_mode not in {"rup", "drat"}:
        raise ValueError("invalid adaptive proof_mode")
    if require_rup and proof_mode != "rup":
        raise ValueError("adaptive tree is not RUP-only")

    root_cubes_path = tree / "root.cubes"
    root_cubes = read_cubes(root_cubes_path)
    if root_cubes != [()]:
        raise ValueError("adaptive root.cubes must contain exactly a 0")
    expected_parents = root_cubes
    expected_parent_bytes = root_cubes_path.read_bytes()
    terminal_refutations = 0
    proof_count = 0
    last_failed_count = -1

    for expected_round, record in enumerate(rounds, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"round {expected_round} record is not an object")
        if int(record.get("round", -1)) != expected_round:
            raise ValueError("adaptive rounds are not sequential")
        declared_mode = record.get("mode")
        mode = "split" if declared_mode is None else declared_mode
        if mode not in {"split", "retry"}:
            raise ValueError(f"round {expected_round} has invalid mode")
        round_dir = tree / f"round_{expected_round:02d}"
        parents_path = round_dir / "parents.cubes"
        children_path = round_dir / "children.cubes"
        coverage_path = round_dir / "coverage.json"
        certificate_path = round_dir / "certificate" / "certificate_manifest.json"
        for path in (
            parents_path,
            children_path,
            coverage_path,
            certificate_path,
        ):
            require_file(path)
        if record.get("parents") != parents_path.name:
            raise ValueError(f"round {expected_round} parents filename mismatch")
        if record.get("children") != children_path.name:
            raise ValueError(f"round {expected_round} children filename mismatch")
        if record.get("coverage") != coverage_path.name:
            raise ValueError(f"round {expected_round} coverage filename mismatch")
        if record.get("certificate_manifest") != "certificate/certificate_manifest.json":
            raise ValueError(
                f"round {expected_round} certificate manifest filename mismatch"
            )
        require_sha256(
            parents_path, record.get("parents_sha256"), f"round {expected_round} parents"
        )
        require_sha256(
            children_path,
            record.get("children_sha256"),
            f"round {expected_round} children",
        )
        require_sha256(
            coverage_path,
            record.get("coverage_sha256"),
            f"round {expected_round} coverage",
        )
        require_sha256(
            certificate_path,
            record.get("certificate_manifest_sha256"),
            f"round {expected_round} certificate manifest",
        )
        if parents_path.read_bytes() != expected_parent_bytes:
            raise ValueError(f"round {expected_round} parent frontier mismatch")
        parents = read_cubes(parents_path)
        children = read_cubes(children_path)
        if parents != expected_parents:
            raise ValueError(f"round {expected_round} parsed parent mismatch")
        if int(record.get("parent_count", -1)) != len(parents):
            raise ValueError(f"round {expected_round} parent_count mismatch")
        if int(record.get("child_count", -1)) != len(children):
            raise ValueError(f"round {expected_round} child_count mismatch")
        if mode == "retry" and children_path.read_bytes() != parents_path.read_bytes():
            raise ValueError(f"round {expected_round} retry changed its frontier")
        if mode == "retry" and (
            int(record.get("split_depth", -1)) != 0
            or record.get("split_strategy") not in (None, "none")
        ):
            raise ValueError(f"round {expected_round} retry metadata mismatch")
        if (
            mode == "split"
            and declared_mode is not None
            and int(record.get("split_depth", 0)) < 1
        ):
            raise ValueError(f"round {expected_round} split depth is invalid")

        coverage = read_json(coverage_path)
        verify_coverage(coverage, parents, children, parents_path, children_path)
        certificate = read_json(certificate_path)
        round_solver_kind = record.get("solver_kind")
        if round_solver_kind not in {
            None,
            "gimsatul",
            "cadical",
            "kissat",
        }:
            raise ValueError(f"round {expected_round} has invalid solver_kind")
        failed_indices, verified_count, failed_count = verify_certificate_manifest(
            certificate_path,
            certificate,
            parent_cnf,
            parent_cnf_sha256,
            parent_cnf_parsed,
            children_path,
            children,
            coverage_path,
            round_solver_kind,
            proof_mode,
        )
        if record.get("failed_indices") != failed_indices:
            raise ValueError(f"round {expected_round} failed indices mismatch")
        if int(record.get("verified_count", -1)) != verified_count:
            raise ValueError(f"round {expected_round} verified_count mismatch")
        if int(record.get("failed_count", -1)) != failed_count:
            raise ValueError(f"round {expected_round} failed_count mismatch")
        if record.get("proof_mode") not in (None, proof_mode):
            raise ValueError(f"round {expected_round} proof_mode mismatch")

        terminal_refutations += verified_count
        proof_count += verified_count
        last_failed_count = failed_count
        if failed_count:
            failed_path = round_dir / "failed.cubes"
            failed_cubes = read_cubes(failed_path)
            expected_failed = [children[index] for index in failed_indices]
            if failed_cubes != expected_failed:
                raise ValueError(f"round {expected_round} failed frontier mismatch")
            expected_parents = failed_cubes
            expected_parent_bytes = failed_path.read_bytes()
        elif expected_round != len(rounds):
            raise ValueError("a non-final round has no unresolved frontier")

    if int(root.get("terminal_refutations", -1)) != terminal_refutations:
        raise ValueError("adaptive terminal_refutations mismatch")
    if verified is False and last_failed_count < 1:
        raise ValueError("partial tree has no unresolved frontier")
    if verified is True and last_failed_count != 0:
        raise ValueError("complete tree still has unresolved cubes")
    proof_modes = root.get("proof_modes")
    if proof_modes not in (None, [proof_mode]):
        raise ValueError("adaptive proof_modes summary mismatch")

    return {
        "verified": True,
        "tree_state": "complete" if verified else "partial",
        "adaptive_manifest_sha256": sha256(manifest_path),
        "parent_cnf_sha256": parent_cnf_sha256,
        "round_count": len(rounds),
        "terminal_refutations": terminal_refutations,
        "proof_count": proof_count,
        "proof_mode": proof_mode,
        "unresolved_cubes": last_failed_count,
        "schema": "legacy-rup" if declared_proof_mode is None else "current",
        "pruned_uncommitted_rounds": removed,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tree", type=Path)
    parser.add_argument("parent_cnf", type=Path)
    state = parser.add_mutually_exclusive_group()
    state.add_argument("--require-partial", action="store_true")
    state.add_argument("--require-complete", action="store_true")
    parser.add_argument("--require-rup", action="store_true")
    parser.add_argument("--prune-uncommitted", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    try:
        report = audit_tree(
            args.tree,
            args.parent_cnf,
            require_partial=args.require_partial,
            require_complete=args.require_complete,
            require_rup=args.require_rup,
            prune_uncommitted=args.prune_uncommitted,
        )
    except BaseException as error:
        report = {"verified": False, "error": str(error)}
        if args.report is not None:
            write_report(args.report, report)
        print(json.dumps(report, separators=(",", ":")))
        raise SystemExit(1) from error
    if args.report is not None:
        write_report(args.report, report)
    print(json.dumps(report, separators=(",", ":")))


if __name__ == "__main__":
    main()
