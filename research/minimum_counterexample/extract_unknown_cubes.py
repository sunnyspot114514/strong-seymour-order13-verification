#!/usr/bin/env python3
"""Extract unresolved cubes from a solve_cubes summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    if "pending_cube_indices" in summary:
        source = Path(summary["cubes"])
        if not source.is_absolute():
            source = Path.cwd() / source
        source_cubes = [
            [int(token) for token in line.split()[1:-1]]
            for line in source.read_text(
                encoding="ascii"
            ).splitlines()
            if line.startswith("a ")
        ]
        cubes = [
            source_cubes[index]
            for index in summary["pending_cube_indices"]
        ]
    else:
        cubes = [
            record["literals"]
            for record in summary["records"]
            if record["result"] == "UNKNOWN"
        ]
    args.output.write_text(
        "".join(
            "a " + " ".join(map(str, cube)) + " 0\n" for cube in cubes
        ),
        encoding="ascii",
        newline="\n",
    )
    print(f"unknown_cubes={len(cubes)}")


if __name__ == "__main__":
    main()
