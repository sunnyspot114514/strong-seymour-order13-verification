#!/usr/bin/env python3
"""Rebind retained RUP cores to exact-sequential branch CNFs.

The exact encoder adds only definitional clauses and preserves every
variable number.  Hence a RUP proof checked against the original CNF is
also a RUP proof against the strengthened CNF.  This script regenerates
the strengthened bases and updates every manifest hash; the release
verifier still rechecks every retained core against its new leaf CNF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


BRANCH = re.compile(r"^n20_d([89])p([0-9]+)$")
EXPECTED = {
    "n20_d8p0",
    "n20_d8p1",
    "n20_d9p0",
    "n20_d9p1",
    "n20_d9p2",
    "n20_d9p3",
}
HEADER = re.compile(r"^p cnf ([1-9][0-9]*) ([0-9]+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def read_cubes(path: Path) -> list[list[int]]:
    cubes = [
        [int(token) for token in line.split()[1:-1]]
        for line in path.read_text(encoding="ascii").splitlines()
        if line.startswith("a ")
    ]
    if not cubes:
        raise ValueError(f"{path}: no cubes")
    return cubes


def parse_cnf(path: Path) -> tuple[list[str], int, int, int]:
    lines = path.read_text(encoding="ascii").splitlines()
    matches = [
        (index, HEADER.fullmatch(line))
        for index, line in enumerate(lines)
        if line.startswith("p ")
    ]
    if len(matches) != 1 or matches[0][1] is None:
        raise ValueError(f"{path}: invalid DIMACS header")
    header_index, match = matches[0]
    assert match is not None
    variables, clauses = map(int, match.groups())
    actual = sum(
        bool(line) and not line.startswith(("c", "p"))
        for line in lines
    )
    if actual != clauses:
        raise ValueError(f"{path}: clause-count mismatch")
    return lines, header_index, variables, clauses


def leaf_bytes(
    lines: list[str],
    header_index: int,
    variables: int,
    clauses: int,
    cube: list[int],
) -> bytes:
    if any(not literal or abs(literal) > variables for literal in cube):
        raise ValueError("cube literal outside DIMACS range")
    leaf = list(lines)
    leaf[header_index] = f"p cnf {variables} {clauses + len(cube)}"
    return (
        "\n".join(leaf)
        + "\n"
        + "".join(f"{literal} 0\n" for literal in cube)
    ).encode("ascii")


def leaf_sha256(
    parsed: tuple[list[str], int, int, int],
    cube: list[int],
) -> str:
    return hashlib.sha256(leaf_bytes(*parsed, cube)).hexdigest()


def materialize(
    parsed: tuple[list[str], int, int, int],
    cube: list[int],
    output: Path,
) -> str:
    data = leaf_bytes(*parsed, cube)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(output)
    return hashlib.sha256(data).hexdigest()


def rebind_manifest(
    path: Path,
    parsed: tuple[list[str], int, int, int],
    cubes: list[list[int]],
    new_base_sha256: str,
    old_base_sha256: str,
) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["base_cnf_sha256"] != old_base_sha256:
        raise ValueError(f"{path}: unexpected source base hash")
    manifest["source_base_cnf_sha256"] = old_base_sha256
    manifest["base_cnf_sha256"] = new_base_sha256
    for record in manifest["records"]:
        index = int(record["cube_index"])
        if not 0 <= index < len(cubes):
            raise ValueError(f"{path}: invalid cube index {index}")
        record["source_leaf_cnf_sha256"] = record["leaf_cnf_sha256"]
        record["leaf_cnf_sha256"] = leaf_sha256(parsed, cubes[index])
    write_json(path, manifest)


def migrate_branch(
    directory: Path,
    generator: Path,
) -> dict[str, object]:
    match = BRANCH.fullmatch(directory.name)
    if match is None:
        raise ValueError(f"invalid branch directory {directory}")
    degree, cover_left = map(int, match.groups())
    base = directory / f"{directory.name}.cnf"
    metadata_path = base.with_suffix(".json")
    row_path = directory / f"{directory.name}.row.cubes"
    old_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if old_metadata["cardinality_encoder"] != "triangular_sinz_sequential":
        raise ValueError(f"{metadata_path}: source encoder is not legacy Sinz")
    old_base_sha256 = sha256(base)
    row_cubes = read_cubes(row_path)

    temporary_base = directory / f".{directory.name}.exact.cnf"
    subprocess.run(
        [
            sys.executable,
            str(generator),
            "20",
            str(degree),
            str(temporary_base),
            "--encoding",
            "conditional-cover",
            "--root-cover-left",
            str(cover_left),
            "--symmetry",
            "hierarchical-profile-ties",
            "--exact-sequential",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    temporary_metadata = temporary_base.with_suffix(".json")
    new_metadata = json.loads(
        temporary_metadata.read_text(encoding="utf-8")
    )
    if (
        new_metadata["variables"] != old_metadata["variables"]
        or new_metadata["orientation_variables"]
        != old_metadata["orientation_variables"]
        or new_metadata["cardinality_encoder"]
        != "exact_triangular_sequential"
    ):
        raise ValueError(f"{directory}: exact regeneration mismatch")
    temporary_base.replace(base)
    write_json(metadata_path, new_metadata)
    temporary_metadata.unlink()
    new_base_sha256 = sha256(base)
    base_parsed = parse_cnf(base)

    for manifest_path in sorted(
        directory.glob("shards/*/certificate_manifest.json")
    ):
        rebind_manifest(
            manifest_path,
            base_parsed,
            row_cubes,
            new_base_sha256,
            old_base_sha256,
        )

    fixed_count = 0
    for refinement_path in sorted(
        directory.glob("refinements/*/*.refinement.json")
    ):
        refinement = json.loads(
            refinement_path.read_text(encoding="utf-8")
        )
        if refinement["base_cnf_sha256"] != old_base_sha256:
            raise ValueError(f"{refinement_path}: source-base mismatch")
        parent_index = int(refinement["parent_cube_index"])
        parent_path = refinement_path.parent / refinement["parent_cnf"]
        old_parent_sha256 = refinement["parent_cnf_sha256"]
        if sha256(parent_path) != old_parent_sha256:
            raise ValueError(f"{parent_path}: source-parent mismatch")
        new_parent_sha256 = materialize(
            base_parsed,
            row_cubes[parent_index],
            parent_path,
        )
        refinement["source_base_cnf_sha256"] = old_base_sha256
        refinement["source_parent_cnf_sha256"] = old_parent_sha256
        refinement["base_cnf_sha256"] = new_base_sha256
        refinement["parent_cnf_sha256"] = new_parent_sha256
        write_json(refinement_path, refinement)

        children_path = (
            refinement_path.parent / refinement["child_cubes"]
        )
        child_cubes = read_cubes(children_path)
        rebind_manifest(
            refinement_path.parent / "certificate_manifest.json",
            parse_cnf(parent_path),
            child_cubes,
            new_parent_sha256,
            old_parent_sha256,
        )
        fixed_count += 1

    adaptive_count = 0
    for adaptive_path in sorted(
        directory.glob("refinements/*/adaptive/adaptive_manifest.json")
    ):
        refinement_directory = adaptive_path.parent.parent
        parent_paths = list(refinement_directory.glob("*.parent.json"))
        if len(parent_paths) != 1:
            raise ValueError(
                f"{refinement_directory}: expected one parent manifest"
            )
        parent_metadata_path = parent_paths[0]
        parent_metadata = json.loads(
            parent_metadata_path.read_text(encoding="utf-8")
        )
        if parent_metadata["base_cnf_sha256"] != old_base_sha256:
            raise ValueError(
                f"{parent_metadata_path}: source-base mismatch"
            )
        parent_index = int(parent_metadata["parent_cube_index"])
        parent_path = (
            refinement_directory / parent_metadata["parent_cnf"]
        )
        old_parent_sha256 = parent_metadata["parent_cnf_sha256"]
        if sha256(parent_path) != old_parent_sha256:
            raise ValueError(f"{parent_path}: source-parent mismatch")
        new_parent_sha256 = materialize(
            base_parsed,
            row_cubes[parent_index],
            parent_path,
        )
        parent_metadata["source_base_cnf_sha256"] = old_base_sha256
        parent_metadata["source_parent_cnf_sha256"] = old_parent_sha256
        parent_metadata["base_cnf_sha256"] = new_base_sha256
        parent_metadata["parent_cnf_sha256"] = new_parent_sha256
        write_json(parent_metadata_path, parent_metadata)
        parent_parsed = parse_cnf(parent_path)

        adaptive = json.loads(
            adaptive_path.read_text(encoding="utf-8")
        )
        if adaptive["parent_cnf_sha256"] != old_parent_sha256:
            raise ValueError(f"{adaptive_path}: source-parent mismatch")
        adaptive["source_parent_cnf_sha256"] = old_parent_sha256
        adaptive["parent_cnf_sha256"] = new_parent_sha256
        for round_record in adaptive["rounds"]:
            round_directory = (
                adaptive_path.parent
                / f"round_{int(round_record['round']):02d}"
            )
            children_path = (
                round_directory / round_record["children"]
            )
            child_cubes = read_cubes(children_path)
            child_manifest_path = (
                round_directory
                / round_record["certificate_manifest"]
            )
            rebind_manifest(
                child_manifest_path,
                parent_parsed,
                child_cubes,
                new_parent_sha256,
                old_parent_sha256,
            )
            round_record["source_certificate_manifest_sha256"] = (
                round_record["certificate_manifest_sha256"]
            )
            round_record["certificate_manifest_sha256"] = sha256(
                child_manifest_path
            )
        write_json(adaptive_path, adaptive)
        adaptive_count += 1

    return {
        "branch": directory.name,
        "source_base_cnf_sha256": old_base_sha256,
        "exact_base_cnf_sha256": new_base_sha256,
        "row_cubes": len(row_cubes),
        "fixed_refinements": fixed_count,
        "adaptive_refinements": adaptive_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "cube_root",
        type=Path,
        help="directory containing the six hard branch directories",
    )
    parser.add_argument("generator", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    marker = args.cube_root / "EXACT_SEQUENTIAL_MIGRATION.json"
    if marker.exists():
        raise ValueError(f"refusing already migrated tree: {marker}")
    directories = {
        path.name: path
        for path in args.cube_root.iterdir()
        if path.is_dir() and BRANCH.fullmatch(path.name)
    }
    if set(directories) != EXPECTED:
        raise ValueError(
            f"hard-branch set mismatch: {sorted(directories)}"
        )
    records = [
        migrate_branch(directories[name], args.generator)
        for name in sorted(EXPECTED)
    ]
    result = {
        "verified": True,
        "migration": "legacy Sinz to exact sequential definitions",
        "generator": args.generator.name,
        "generator_sha256": sha256(args.generator),
        "branches": records,
    }
    write_json(marker, result)
    if args.output is not None:
        write_json(args.output, result)
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
