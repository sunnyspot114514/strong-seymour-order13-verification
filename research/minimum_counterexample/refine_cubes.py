#!/usr/bin/env python3
"""Refine selected cubes with CaDiCaL lookahead under assumptions."""

from __future__ import annotations

import argparse
import concurrent.futures
import subprocess
import tempfile
from pathlib import Path


def read_cubes(path: Path) -> list[list[int]]:
    return [
        [int(token) for token in line.split()[1:-1]]
        for line in path.read_text(encoding="ascii").splitlines()
        if line.startswith("a ")
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("parents", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("generator", type=Path)
    parser.add_argument("--additional-depth", type=int, default=2)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    parents = read_cubes(args.parents)
    if not parents:
        raise ValueError("parent cube file is empty")

    def refine(item: tuple[int, list[int]]) -> list[list[int]]:
        index, parent = item
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / f"parent_{index}.cubes"
            completed = subprocess.run(
                [
                    str(args.generator),
                    str(args.cnf),
                    str(args.additional_depth),
                    str(output),
                    *map(str, parent),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr[-1000:])
            children = read_cubes(output)
        if len(children) != 1 << args.additional_depth:
            raise RuntimeError(
                f"parent {index} produced {len(children)} children"
            )
        if any(child[: len(parent)] != parent for child in children):
            raise RuntimeError(f"parent {index} prefix was not preserved")
        return children

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.jobs
    ) as executor:
        groups = list(executor.map(refine, enumerate(parents)))
    children = [child for group in groups for child in group]
    args.output.write_text(
        "".join(
            "a " + " ".join(map(str, cube)) + " 0\n" for cube in children
        ),
        encoding="ascii",
        newline="\n",
    )
    print(f"parents={len(parents)} children={len(children)}")


if __name__ == "__main__":
    main()
