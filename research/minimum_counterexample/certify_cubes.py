#!/usr/bin/env python3
"""Generate and check pure-RUP certificates for a shard of CNF cubes."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import itertools
import json
import re
import subprocess
import time
from pathlib import Path


HEADER = re.compile(r"^p cnf ([1-9][0-9]*) ([0-9]+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_complete_cubes(path: Path, variables: int) -> list[list[int]]:
    cubes = [
        [int(token) for token in line.split()[1:-1]]
        for line in path.read_text(encoding="ascii").splitlines()
        if line.startswith("a ")
    ]
    if not cubes:
        raise ValueError("cube file has no a-lines")
    depth = len(cubes[0])
    split_variables = [abs(literal) for literal in cubes[0]]
    if (
        not depth
        or len(set(split_variables)) != depth
        or any(variable > variables for variable in split_variables)
    ):
        raise ValueError("invalid split-variable list")
    if any(
        len(cube) != depth
        or [abs(literal) for literal in cube] != split_variables
        for cube in cubes
    ):
        raise ValueError("cubes are not one fixed-variable partition")
    observed = {
        tuple(literal > 0 for literal in cube)
        for cube in cubes
    }
    expected = set(itertools.product((False, True), repeat=depth))
    if observed != expected or len(cubes) != len(expected):
        raise ValueError("cubes do not exhaust the split-variable space")
    return cubes


def read_covered_cubes(path: Path, variables: int) -> list[list[int]]:
    cubes = [
        [int(token) for token in line.split()[1:-1]]
        for line in path.read_text(encoding="ascii").splitlines()
        if line.startswith("a ")
    ]
    if not cubes:
        raise ValueError("cube file has no a-lines")
    depth = len(cubes[0])
    if not depth or any(len(cube) != depth for cube in cubes):
        raise ValueError("covered cubes must have one positive depth")
    canonical = set()
    for cube in cubes:
        cube_variables = [abs(literal) for literal in cube]
        if (
            0 in cube
            or len(set(cube_variables)) != len(cube_variables)
            or any(variable > variables for variable in cube_variables)
        ):
            raise ValueError("covered cube has invalid literals")
        key = tuple(sorted(cube, key=abs))
        if key in canonical:
            raise ValueError("covered cube file contains a duplicate")
        canonical.add(key)
    return cubes


def parse_cnf(path: Path) -> tuple[list[str], int, int, int]:
    lines = path.read_text(encoding="ascii").splitlines()
    headers = [
        (index, HEADER.fullmatch(line))
        for index, line in enumerate(lines)
        if line.startswith("p ")
    ]
    if len(headers) != 1 or headers[0][1] is None:
        raise ValueError("CNF must have exactly one valid header")
    header_index, match = headers[0]
    assert match is not None
    variables, clauses = map(int, match.groups())
    actual = sum(
        bool(line) and not line.startswith(("c", "p"))
        for line in lines
    )
    if actual != clauses:
        raise ValueError(
            f"header declares {clauses} clauses, found {actual}"
        )
    return lines, header_index, variables, clauses


def run_checked(
    command: list[str],
    log: Path,
    timeout: int,
) -> tuple[int, float, str]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        output = completed.stdout.decode("utf-8", errors="replace")
        status = completed.returncode
    except subprocess.TimeoutExpired as error:
        partial = error.stdout or b""
        if isinstance(partial, str):
            output = partial
        else:
            output = partial.decode("utf-8", errors="replace")
        output += f"\ncertificate command timed out after {timeout}s\n"
        status = 124
    elapsed = time.perf_counter() - started
    log.write_text(output, encoding="utf-8", newline="\n")
    return status, elapsed, output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("cubes", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("gimsatul", type=Path)
    parser.add_argument("drat_trim", type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--solver-threads", type=int, default=1)
    parser.add_argument("--seconds", type=int, default=3600)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--xz-level", type=int, default=9)
    parser.add_argument("--coverage", type=Path)
    parser.add_argument(
        "--discard-logs",
        action="store_true",
        help=(
            "remove per-cube solver/checker logs after their status and "
            "timings have been recorded in the manifest"
        ),
    )
    args = parser.parse_args()

    if args.jobs < 1 or args.solver_threads < 1 or args.seconds < 1:
        raise ValueError("jobs, solver threads, and seconds must be positive")
    if args.shards < 1 or not 0 <= args.shard_index < args.shards:
        raise ValueError("invalid shard specification")
    if not 0 <= args.xz_level <= 9:
        raise ValueError("xz level must be between 0 and 9")

    lines, header_index, variables, clauses = parse_cnf(args.cnf)
    if args.coverage is None:
        cubes = read_complete_cubes(args.cubes, variables)
        coverage_sha256 = None
    else:
        cubes = read_covered_cubes(args.cubes, variables)
        coverage = json.loads(
            args.coverage.read_text(encoding="utf-8")
        )
        if (
            coverage.get("verified") is not True
            or int(coverage["child_count"]) != len(cubes)
            or coverage.get("children_sha256") != sha256(args.cubes)
        ):
            raise ValueError("coverage file does not bind this cube file")
        coverage_sha256 = sha256(args.coverage)
    selected = [
        (index, cube)
        for index, cube in enumerate(cubes)
        if index % args.shards == args.shard_index
    ]
    if not selected:
        raise ValueError("selected shard has no cubes")

    args.output.mkdir(parents=True, exist_ok=True)

    def certify(item: tuple[int, list[int]]) -> dict[str, object]:
        index, cube = item
        stem = f"cube_{index:05d}"
        leaf_cnf = args.output / f"{stem}.cnf"
        raw_proof = args.output / f"{stem}.drat"
        core = args.output / f"{stem}.core.rup"
        compressed_core = args.output / f"{stem}.core.rup.xz"
        solver_log = args.output / f"{stem}.solver.log"
        extraction_log = args.output / f"{stem}.core-extraction.log"
        verification_log = args.output / f"{stem}.core-verification.log"

        leaf_lines = list(lines)
        leaf_lines[header_index] = (
            f"p cnf {variables} {clauses + len(cube)}"
        )
        leaf_cnf.write_text(
            "\n".join(leaf_lines)
            + "\n"
            + "".join(f"{literal} 0\n" for literal in cube),
            encoding="ascii",
            newline="\n",
        )
        leaf_sha256 = sha256(leaf_cnf)

        solver_status, solver_seconds, solver_output = run_checked(
            [
                str(args.gimsatul),
                f"--threads={args.solver_threads}",
                str(leaf_cnf),
                str(raw_proof),
            ],
            solver_log,
            args.seconds,
        )
        if solver_status != 20 or "s UNSATISFIABLE" not in solver_output:
            raise RuntimeError(
                f"cube {index}: solver status {solver_status}"
            )
        raw_proof_bytes = raw_proof.stat().st_size

        extraction_status, extraction_seconds, extraction_output = (
            run_checked(
                [
                    str(args.drat_trim),
                    str(leaf_cnf),
                    str(raw_proof),
                    "-U",
                    "-l",
                    str(core),
                ],
                extraction_log,
                args.seconds,
            )
        )
        if "s VERIFIED" not in extraction_output:
            raise RuntimeError(
                f"cube {index}: core extraction status "
                f"{extraction_status}"
            )
        core_bytes = core.stat().st_size

        verification_status, verification_seconds, verification_output = (
            run_checked(
                [
                    str(args.drat_trim),
                    str(leaf_cnf),
                    str(core),
                    "-U",
                ],
                verification_log,
                args.seconds,
            )
        )
        if "s VERIFIED" not in verification_output:
            raise RuntimeError(
                f"cube {index}: core verification status "
                f"{verification_status}"
            )

        subprocess.run(
            ["xz", "-T1", f"-{args.xz_level}", "-f", str(core)],
            check=True,
        )
        compressed_core_sha256 = sha256(compressed_core)
        compressed_core_bytes = compressed_core.stat().st_size
        raw_proof.unlink()
        leaf_cnf.unlink()
        if args.discard_logs:
            solver_log.unlink()
            extraction_log.unlink()
            verification_log.unlink()
        return {
            "cube_index": index,
            "literals": cube,
            "leaf_cnf_sha256": leaf_sha256,
            "solver_exit": solver_status,
            "solver_seconds": solver_seconds,
            "raw_proof_bytes": raw_proof_bytes,
            "extraction_exit": extraction_status,
            "extraction_seconds": extraction_seconds,
            "core_bytes": core_bytes,
            "verification_exit": verification_status,
            "verification_seconds": verification_seconds,
            "compressed_core": compressed_core.name,
            "compressed_core_sha256": compressed_core_sha256,
            "compressed_core_bytes": compressed_core_bytes,
            "rup_only": True,
        }

    records: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    manifest_path = args.output / "certificate_manifest.json"

    def write_manifest() -> None:
        ordered_records = sorted(
            records,
            key=lambda record: int(record["cube_index"]),
        )
        result = {
            "base_cnf": str(args.cnf),
            "base_cnf_sha256": sha256(args.cnf),
            "cubes": str(args.cubes),
            "cubes_sha256": sha256(args.cubes),
            "complete_partition": True,
            "total_cube_count": len(cubes),
            "cube_depth": len(cubes[0]),
            "shards": args.shards,
            "shard_index": args.shard_index,
            "xz_level": args.xz_level,
            "logs_retained": not args.discard_logs,
            "coverage": (
                str(args.coverage) if args.coverage is not None else None
            ),
            "coverage_sha256": coverage_sha256,
            "selected_cube_indices": [index for index, _ in selected],
            "verified_cube_count": len(ordered_records),
            "failed_cubes": sorted(
                failures,
                key=lambda failure: int(failure["cube_index"]),
            ),
            "records": ordered_records,
        }
        temporary = manifest_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(manifest_path)

    write_manifest()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.jobs
    ) as executor:
        futures = {
            executor.submit(certify, item): item[0]
            for item in selected
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                record = future.result()
                records.append(record)
                print(
                    json.dumps(
                        {
                            "cube": record["cube_index"],
                            "verified": True,
                        },
                        separators=(",", ":"),
                    ),
                    flush=True,
                )
            except BaseException as error:
                failures.append(
                    {
                        "cube_index": futures[future],
                        "error": str(error),
                    }
                )
                print(
                    json.dumps(
                        {
                            "cube": futures[future],
                            "verified": False,
                            "error": str(error),
                        },
                        separators=(",", ":"),
                    ),
                    flush=True,
                )
            write_manifest()

    if failures:
        raise SystemExit(
            f"{len(failures)} cube certificate command(s) failed"
        )
    if len(records) != len(selected):
        raise AssertionError("not every selected cube was certified")


if __name__ == "__main__":
    main()
