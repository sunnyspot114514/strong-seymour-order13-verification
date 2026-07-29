#!/usr/bin/env python3
"""Verify that child cubes exhaust every supplied parent cube."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
from pathlib import Path


def read_cubes(path: Path) -> list[tuple[int, ...]]:
    cubes = [
        tuple(map(int, line.split()[1:-1]))
        for line in path.read_text(encoding="ascii").splitlines()
        if line.startswith("a ")
    ]
    if not cubes:
        raise ValueError(f"{path} contains no cubes")
    for cube in cubes:
        variables: dict[int, bool] = {}
        for literal in cube:
            variable = abs(literal)
            value = literal > 0
            if variable in variables and variables[variable] != value:
                raise ValueError("cube contains complementary literals")
            variables[variable] = value
    return cubes


def canonical(cube: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(set(cube), key=lambda literal: abs(literal)))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@functools.lru_cache(maxsize=None)
def covers_boolean_space(cubes: tuple[tuple[int, ...], ...]) -> bool:
    """Return whether the disjunction of cubes is a tautology."""
    if any(not cube for cube in cubes):
        return True
    if not cubes:
        return False
    variable = abs(min(cubes, key=len)[0])
    branches = []
    for value in (False, True):
        literal = variable if value else -variable
        opposite = -literal
        restricted: set[tuple[int, ...]] = set()
        for cube in cubes:
            if opposite in cube:
                continue
            if literal in cube:
                restricted.add(
                    tuple(item for item in cube if item != literal)
                )
            else:
                restricted.add(cube)
        branches.append(
            covers_boolean_space(tuple(sorted(restricted)))
        )
    return all(branches)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("parents", type=Path)
    parser.add_argument("children", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    parents = read_cubes(args.parents)
    children = read_cubes(args.children)
    unused = set(range(len(children)))
    records = []
    for parent_index, parent in enumerate(parents):
        parent_set = set(parent)
        child_indices = [
            index
            for index, child in enumerate(children)
            if parent_set.issubset(child)
        ]
        if not child_indices:
            raise SystemExit(f"parent {parent_index} has no children")
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
        covered = covers_boolean_space(
            tuple(sorted(set(suffixes)))
        )
        records.append(
            {
                "parent": parent_index,
                "child_count": len(child_indices),
                "covered": covered,
            }
        )
        if not covered:
            raise SystemExit(
                f"children do not exhaust parent {parent_index}"
            )
    if unused:
        raise SystemExit(f"{len(unused)} children match no parent")
    result = {
        "verified": True,
        "parents_sha256": sha256(args.parents),
        "children_sha256": sha256(args.children),
        "parent_count": len(parents),
        "child_count": len(children),
        "records": records,
    }
    if args.output is not None:
        args.output.write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
