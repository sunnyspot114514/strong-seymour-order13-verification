#!/usr/bin/env python3
"""Refine cubes by all signs of unused low-numbered primary variables."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path


def read_cubes(path: Path) -> list[list[int]]:
    cubes = [
        [int(token) for token in line.split()[1:-1]]
        for line in path.read_text(encoding="ascii").splitlines()
        if line.startswith("a ")
    ]
    if not cubes:
        raise ValueError(f"{path} contains no cubes")
    return cubes


def read_unit_variables(path: Path) -> set[int]:
    units = set()
    for line in path.read_text(encoding="ascii").splitlines():
        if not line or line.startswith(("c", "p")):
            continue
        literals = list(map(int, line.split()))
        if len(literals) == 2 and literals[-1] == 0:
            units.add(abs(literals[0]))
    return units


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("parents", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--variable-upper-bound", type=int, required=True)
    parser.add_argument("--additional-depth", type=int, default=4)
    args = parser.parse_args()
    if args.variable_upper_bound < 1 or args.additional_depth < 1:
        raise ValueError("bounds must be positive")

    parents = read_cubes(args.parents)
    unavailable = read_unit_variables(args.cnf)
    unavailable.update(
        abs(literal) for parent in parents for literal in parent
    )
    split_variables = [
        variable
        for variable in range(1, args.variable_upper_bound + 1)
        if variable not in unavailable
    ][: args.additional_depth]
    if len(split_variables) != args.additional_depth:
        raise ValueError("not enough unused primary variables")

    with args.output.open("w", encoding="ascii", newline="\n") as output:
        for parent in parents:
            for signs in itertools.product(
                (False, True), repeat=len(split_variables)
            ):
                suffix = [
                    variable if positive else -variable
                    for variable, positive in zip(split_variables, signs)
                ]
                output.write(
                    "a "
                    + " ".join(map(str, parent + suffix))
                    + " 0\n"
                )
    print(
        f"parents={len(parents)} "
        f"children={len(parents) * (1 << len(split_variables))} "
        f"variables={','.join(map(str, split_variables))}"
    )


if __name__ == "__main__":
    main()
