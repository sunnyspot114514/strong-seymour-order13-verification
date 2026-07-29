#!/usr/bin/env python3
"""Directly analyze strong Seymour vertices of a tournament matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_matrix(path: Path) -> list[str]:
    rows = [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]
    order = len(rows)
    if order == 0 or any(
        len(row) != order or set(row) - {"0", "1"} for row in rows
    ):
        raise ValueError("input is not a square zero-one matrix")
    for u in range(order):
        if rows[u][u] != "0":
            raise ValueError(f"loop at vertex {u}")
        for v in range(u + 1, order):
            if (rows[u][v] == "1") == (rows[v][u] == "1"):
                raise ValueError(f"pair {u},{v} is not oriented exactly once")
    return rows


def maximum_matching(rows: list[int]) -> int:
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


def minimum_cover(rows: list[int], right_count: int) -> tuple[int, int, int]:
    left_count = len(rows)
    best = left_count + right_count + 1
    best_left = 0
    best_right = 0
    for left_cover in range(1 << left_count):
        right_cover = 0
        for index, row in enumerate(rows):
            if not left_cover & (1 << index):
                right_cover |= row
        size = left_cover.bit_count() + right_cover.bit_count()
        if size < best:
            best = size
            best_left = left_cover
            best_right = right_cover
    return best, best_left, best_right


def best_near_cover(
    rows: list[int], right_count: int
) -> tuple[int, int, int, int]:
    """Choose |L_cover|+|R_cover|=|L|-1 minimizing uncovered edges."""
    left_count = len(rows)
    budget = left_count - 1
    best_uncovered = sum(row.bit_count() for row in rows) + 1
    best_left = 0
    best_right = 0
    for left_cover in range(1 << left_count):
        left_size = left_cover.bit_count()
        right_budget = budget - left_size
        if not 0 <= right_budget <= right_count:
            continue
        column_degrees = []
        for target in range(right_count):
            degree = sum(
                1
                for source, row in enumerate(rows)
                if not left_cover & (1 << source)
                and row & (1 << target)
            )
            column_degrees.append((degree, target))
        column_degrees.sort(reverse=True)
        right_cover = sum(
            1 << target for _, target in column_degrees[:right_budget]
        )
        uncovered = sum(
            1
            for source, row in enumerate(rows)
            if not left_cover & (1 << source)
            for target in range(right_count)
            if row & (1 << target) and not right_cover & (1 << target)
        )
        if uncovered < best_uncovered:
            best_uncovered = uncovered
            best_left = left_cover
            best_right = right_cover
    return best_uncovered, best_left, best_right, budget


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--flip",
        action="append",
        default=[],
        metavar="U,V",
        help="flip one tournament edge before analysis; may be repeated",
    )
    parser.add_argument(
        "--delete",
        action="append",
        default=[],
        type=int,
        metavar="VERTEX",
        help="delete a vertex before analysis; may be repeated",
    )
    parser.add_argument("--write-matrix", type=Path)
    args = parser.parse_args()
    matrix = read_matrix(args.matrix)
    deleted = set(args.delete)
    if len(deleted) != len(args.delete):
        raise ValueError("a deleted vertex is repeated")
    if any(not 0 <= vertex < len(matrix) for vertex in deleted):
        raise ValueError("a deleted vertex is outside the matrix")
    retained = [
        vertex for vertex in range(len(matrix)) if vertex not in deleted
    ]
    matrix = [
        "".join(matrix[u][v] for v in retained) for u in retained
    ]
    mutable = [list(row) for row in matrix]
    for specification in args.flip:
        u, v = map(int, specification.split(","))
        if u == v or not 0 <= u < len(matrix) or not 0 <= v < len(matrix):
            raise ValueError(f"invalid edge: {specification}")
        mutable[u][v], mutable[v][u] = mutable[v][u], mutable[u][v]
    matrix = ["".join(row) for row in mutable]
    if args.write_matrix:
        args.write_matrix.write_text(
            "\n".join(matrix) + "\n", encoding="ascii"
        )
    order = len(matrix)
    records = []
    for root in range(order):
        left = [v for v in range(order) if matrix[root][v] == "1"]
        right = [
            v
            for v in range(order)
            if v != root
            and matrix[v][root] == "1"
            and any(matrix[u][v] == "1" for u in left)
        ]
        rows = [
            sum(
                1 << index
                for index, target in enumerate(right)
                if matrix[source][target] == "1"
            )
            for source in left
        ]
        matching = maximum_matching(rows)
        cover_size, left_cover, right_cover = minimum_cover(rows, len(right))
        uncovered, near_left, near_right, near_budget = best_near_cover(
            rows, len(right)
        )
        records.append(
            {
                "vertex": root,
                "outdegree": len(left),
                "strict_second": len(right),
                "matching": matching,
                "strong": matching == len(left),
                "minimum_cover": {
                    "size": cover_size,
                    "left": [
                        left[index]
                        for index in range(len(left))
                        if left_cover & (1 << index)
                    ],
                    "right": [
                        right[index]
                        for index in range(len(right))
                        if right_cover & (1 << index)
                    ],
                },
                "best_size_d_minus_1_cover": {
                    "size": near_budget,
                    "uncovered_edges": uncovered,
                    "left": [
                        left[index]
                        for index in range(len(left))
                        if near_left & (1 << index)
                    ],
                    "right": [
                        right[index]
                        for index in range(len(right))
                        if near_right & (1 << index)
                    ],
                    "uncovered_edge_list": [
                        [left[source], right[target]]
                        for source, row in enumerate(rows)
                        if not near_left & (1 << source)
                        for target in range(len(right))
                        if row & (1 << target)
                        and not near_right & (1 << target)
                    ],
                },
            }
        )
    result = {
        "order": order,
        "minimum_outdegree": min(r["outdegree"] for r in records),
        "strong_vertices": [r["vertex"] for r in records if r["strong"]],
        "vertices": records,
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
