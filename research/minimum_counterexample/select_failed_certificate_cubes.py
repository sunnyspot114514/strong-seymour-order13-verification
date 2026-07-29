#!/usr/bin/env python3
"""Select exactly the failed cube indices from a certificate manifest."""

from __future__ import annotations

import argparse
import json
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cubes", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    cubes = read_cubes(args.cubes)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if int(manifest["total_cube_count"]) != len(cubes):
        raise ValueError("manifest cube count does not match cube file")

    verified = {
        int(record["cube_index"]) for record in manifest["records"]
    }
    failed = {
        int(record["cube_index"]) for record in manifest["failed_cubes"]
    }
    all_indices = set(range(len(cubes)))
    if verified & failed:
        raise ValueError("an index is both verified and failed")
    if verified | failed != all_indices:
        missing = sorted(all_indices - verified - failed)
        raise ValueError(f"manifest leaves {len(missing)} indices unresolved")

    ordered = sorted(failed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(
            "a " + " ".join(map(str, cubes[index])) + " 0\n"
            for index in ordered
        ),
        encoding="ascii",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "selected": len(ordered),
                "indices": ordered,
            },
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
