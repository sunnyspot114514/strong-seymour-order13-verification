#!/usr/bin/env python3
"""Refine one row cube by a complete assignment to the next cross row."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_cubes(path: Path) -> list[list[int]]:
    return [
        [int(token) for token in line.split()[1:-1]]
        for line in path.read_text(encoding="ascii").splitlines()
        if line.startswith("a ")
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_cnf", type=Path)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("row_cubes", type=Path)
    parser.add_argument("parent_index", type=int)
    parser.add_argument("parent_cnf", type=Path)
    parser.add_argument("child_cubes", type=Path)
    parser.add_argument("output_metadata", type=Path)
    parser.add_argument("--depth", type=int, default=1)
    args = parser.parse_args()
    if args.depth < 1:
        raise ValueError("depth must be positive")

    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    row_cubes = read_cubes(args.row_cubes)
    if not 0 <= args.parent_index < len(row_cubes):
        raise IndexError("parent cube index is out of range")
    parent = row_cubes[args.parent_index]
    fixed = {abs(literal) for literal in parent}

    degree = int(metadata["root_degree"])
    cover_left = int(metadata["root_cover_left"])
    cover_right = int(metadata["root_cover_right"])
    uncovered_out = list(range(cover_left + 1, degree + 1))
    covered_in = list(range(degree + 1, degree + 1 + cover_right))
    if len(uncovered_out) < 2 or not covered_in:
        raise ValueError("branch has no second uncovered-out cross row")

    orientation = metadata["orientation_variables"]
    candidates = []
    for source in uncovered_out[1:]:
        for target in covered_in:
            variable = int(
                orientation[f"{min(source, target)},{max(source, target)}"]
            )
            if variable not in fixed and variable not in candidates:
                candidates.append(variable)
    if len(candidates) < args.depth:
        raise ValueError("not enough unfixed cross-row variables")
    split_variables = candidates[: args.depth]

    lines = args.base_cnf.read_text(encoding="ascii").splitlines()
    headers = [
        index for index, line in enumerate(lines) if line.startswith("p cnf ")
    ]
    if len(headers) != 1:
        raise ValueError("base CNF must have exactly one DIMACS header")
    header_index = headers[0]
    fields = lines[header_index].split()
    if len(fields) != 4:
        raise ValueError("invalid DIMACS header")
    variables = int(fields[2])
    clauses = int(fields[3])
    actual = sum(
        bool(line) and not line.startswith(("c", "p")) for line in lines
    )
    if actual != clauses:
        raise ValueError("DIMACS clause-count mismatch")
    if any(abs(literal) > variables for literal in parent + split_variables):
        raise ValueError("literal exceeds DIMACS variable count")

    lines[header_index] = f"p cnf {variables} {clauses + len(parent)}"
    args.parent_cnf.parent.mkdir(parents=True, exist_ok=True)
    args.parent_cnf.write_text(
        "\n".join(lines)
        + "\n"
        + "".join(f"{literal} 0\n" for literal in parent),
        encoding="ascii",
        newline="\n",
    )
    args.child_cubes.write_text(
        "".join(
            "a "
            + " ".join(
                str(variable if positive else -variable)
                for variable, positive in zip(split_variables, signs)
            )
            + " 0\n"
            for signs in itertools.product(
                (False, True), repeat=len(split_variables)
            )
        ),
        encoding="ascii",
        newline="\n",
    )

    result = {
        "base_cnf_sha256": sha256(args.base_cnf),
        "row_cubes_sha256": sha256(args.row_cubes),
        "parent_cube_index": args.parent_index,
        "parent_literals": parent,
        "parent_cnf": args.parent_cnf.name,
        "parent_cnf_sha256": sha256(args.parent_cnf),
        "child_cubes": args.child_cubes.name,
        "child_cubes_sha256": sha256(args.child_cubes),
        "split_variables": split_variables,
        "child_count": 1 << len(split_variables),
        "complete_partition": True,
    }
    args.output_metadata.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
