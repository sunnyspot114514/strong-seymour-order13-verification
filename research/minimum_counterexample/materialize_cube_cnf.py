#!/usr/bin/env python3
"""Materialize one cube as unit clauses appended to a DIMACS formula."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_cube(path: Path, index: int) -> list[int]:
    cubes = [
        [int(token) for token in line.split()[1:-1]]
        for line in path.read_text(encoding="ascii").splitlines()
        if line.startswith("a ")
    ]
    if not 0 <= index < len(cubes):
        raise IndexError(
            f"cube index {index} is outside 0..{len(cubes) - 1}"
        )
    cube = cubes[index]
    values: dict[int, bool] = {}
    for literal in cube:
        if not literal:
            raise ValueError("a cube contains literal zero")
        variable = abs(literal)
        value = literal > 0
        if variable in values:
            if values[variable] != value:
                raise ValueError("a cube contains complementary literals")
            raise ValueError("a cube repeats a literal")
        values[variable] = value
    return cube


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_cnf", type=Path)
    parser.add_argument("cubes", type=Path)
    parser.add_argument("cube_index", type=int)
    parser.add_argument("output_cnf", type=Path)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()

    cube = read_cube(args.cubes, args.cube_index)
    lines = args.base_cnf.read_text(encoding="ascii").splitlines()
    header_indices = [
        index
        for index, line in enumerate(lines)
        if line.startswith("p cnf ")
    ]
    if len(header_indices) != 1:
        raise ValueError("the base CNF must have exactly one DIMACS header")
    header_index = header_indices[0]
    fields = lines[header_index].split()
    if len(fields) != 4:
        raise ValueError("invalid DIMACS header")
    variables = int(fields[2])
    clauses = int(fields[3])
    if any(abs(literal) > variables for literal in cube):
        raise ValueError("a cube literal exceeds the DIMACS variable bound")

    actual_clauses = sum(
        bool(line) and not line.startswith(("c", "p"))
        for line in lines
    )
    if actual_clauses != clauses:
        raise ValueError(
            f"header declares {clauses} clauses, found {actual_clauses}"
        )
    lines[header_index] = f"p cnf {variables} {clauses + len(cube)}"
    args.output_cnf.parent.mkdir(parents=True, exist_ok=True)
    args.output_cnf.write_text(
        "\n".join(lines)
        + "\n"
        + "".join(f"{literal} 0\n" for literal in cube),
        encoding="ascii",
        newline="\n",
    )

    result = {
        "base_cnf": str(args.base_cnf),
        "base_cnf_sha256": sha256(args.base_cnf),
        "cubes": str(args.cubes),
        "cubes_sha256": sha256(args.cubes),
        "cube_index": args.cube_index,
        "cube_literals": cube,
        "output_cnf": str(args.output_cnf),
        "output_cnf_sha256": sha256(args.output_cnf),
        "variables": variables,
        "base_clauses": clauses,
        "unit_clauses_added": len(cube),
    }
    if args.metadata is not None:
        args.metadata.write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
