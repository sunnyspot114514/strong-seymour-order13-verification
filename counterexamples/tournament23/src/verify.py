#!/usr/bin/env python3
"""Verify the published 23-vertex tournament by state DP and Hall search."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path


def read_matrix(path: Path) -> list[str]:
    rows = [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]
    order = len(rows)
    if not rows or any(len(row) != order for row in rows):
        raise ValueError("matrix is not square")
    if any(set(row) - {"0", "1"} for row in rows):
        raise ValueError("matrix is not binary")
    for u in range(order):
        if rows[u][u] != "0":
            raise ValueError("matrix has a loop")
        for v in range(u + 1, order):
            if (rows[u][v] == "1") == (rows[v][u] == "1"):
                raise ValueError("matrix is not a tournament")
    return rows


def matching_size_by_state_dp(rows: list[int]) -> int:
    reachable = {0}
    for row in rows:
        updated = set(reachable)
        for used in reachable:
            available = row & ~used
            while available:
                bit = available & -available
                available -= bit
                updated.add(used | bit)
        reachable = updated
    return max(mask.bit_count() for mask in reachable)


def verify(matrix: list[str]) -> dict[str, object]:
    order = len(matrix)
    vertices = []
    strong_vertices = []
    for root in range(order):
        first = [v for v in range(order) if matrix[root][v] == "1"]
        first_set = set(first)
        second = [
            z
            for z in range(order)
            if z != root
            and z not in first_set
            and any(matrix[y][z] == "1" for y in first)
        ]
        rows = [
            sum(
                1 << index
                for index, z in enumerate(second)
                if matrix[y][z] == "1"
            )
            for y in first
        ]
        matching = matching_size_by_state_dp(rows)
        hall_s: list[int] | None = None
        hall_gamma: list[int] | None = None
        for size in range(1, len(first) + 1):
            for indices in itertools.combinations(range(len(first)), size):
                gamma = 0
                for index in indices:
                    gamma |= rows[index]
                if gamma.bit_count() < size:
                    hall_s = [first[index] for index in indices]
                    hall_gamma = [
                        second[index]
                        for index in range(len(second))
                        if gamma & (1 << index)
                    ]
                    break
            if hall_s is not None:
                break
        if matching == len(first):
            strong_vertices.append(root)
        if hall_s is None or hall_gamma is None:
            raise AssertionError(f"vertex {root} has no Hall defect")
        vertices.append(
            {
                "vertex": root,
                "outdegree": len(first),
                "strict_second": len(second),
                "matching": matching,
                "hall_S": hall_s,
                "hall_Gamma": hall_gamma,
            }
        )

    text = "\n".join(matrix) + "\n"
    return {
        "verified": not strong_vertices,
        "order": order,
        "minimum_outdegree": min(
            entry["outdegree"] for entry in vertices
        ),
        "strong_vertices": strong_vertices,
        "matrix_sha256": hashlib.sha256(
            text.encode("ascii")
        ).hexdigest(),
        "vertices": vertices,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(read_matrix(args.matrix))
    if not result["verified"]:
        raise SystemExit(
            f"strong vertices found: {result['strong_vertices']}"
        )
    if args.output is not None:
        args.output.write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
