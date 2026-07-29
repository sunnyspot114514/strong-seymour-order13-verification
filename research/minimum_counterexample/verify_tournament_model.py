#!/usr/bin/env python3
"""Verify a SAT model as a tournament with no strong Seymour vertex."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path


def read_model(path: Path) -> set[int]:
    values: set[int] = set()
    saw_model_line = False
    for line in path.read_text(encoding="ascii").splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "v":
            saw_model_line = True
            fields = fields[1:]
        elif fields[0] == "s" or fields[0].startswith("c"):
            continue
        elif saw_model_line:
            continue
        else:
            try:
                int(fields[0])
            except ValueError:
                continue
        for token in fields:
            literal = int(token)
            if literal > 0:
                values.add(literal)
    if not saw_model_line and not values:
        raise ValueError("solver output contains no model literals")
    return values


def matching_size(rows: list[int]) -> int:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--matrix-output", type=Path)
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    true_variables = read_model(args.model)
    order = metadata["order"]
    orientation = {
        tuple(map(int, pair.split(","))): variable
        for pair, variable in metadata["orientation_variables"].items()
    }
    adjacency = [[False] * order for _ in range(order)]
    for (u, v), variable in orientation.items():
        if variable in true_variables:
            adjacency[u][v] = True
        else:
            adjacency[v][u] = True

    records = []
    strong_vertices = []
    for root in range(order):
        left = [vertex for vertex in range(order) if adjacency[root][vertex]]
        left_set = set(left)
        right = [
            vertex
            for vertex in range(order)
            if vertex != root
            and vertex not in left_set
            and any(adjacency[u][vertex] for u in left)
        ]
        rows = [
            sum(
                1 << index
                for index, vertex in enumerate(right)
                if adjacency[u][vertex]
            )
            for u in left
        ]
        maximum_matching = matching_size(rows)
        hall = None
        for size in range(1, len(left) + 1):
            for indices in itertools.combinations(range(len(left)), size):
                gamma = 0
                for index in indices:
                    gamma |= rows[index]
                if gamma.bit_count() < size:
                    hall = {
                        "S": [left[index] for index in indices],
                        "Gamma": [
                            right[index]
                            for index in range(len(right))
                            if gamma & (1 << index)
                        ],
                    }
                    break
            if hall is not None:
                break
        if maximum_matching == len(left):
            strong_vertices.append(root)
        records.append(
            {
                "vertex": root,
                "outdegree": len(left),
                "strict_second": len(right),
                "matching": maximum_matching,
                "hall_defect": hall,
            }
        )

    matrix = (
        "\n".join(
            "".join("1" if adjacency[u][v] else "0" for v in range(order))
            for u in range(order)
        )
        + "\n"
    )
    result = {
        "verified": not strong_vertices,
        "order": order,
        "strong_vertices": strong_vertices,
        "minimum_outdegree": min(record["outdegree"] for record in records),
        "matrix_sha256": hashlib.sha256(matrix.encode("ascii")).hexdigest(),
        "adjacency_matrix": matrix.splitlines(),
        "vertices": records,
    }
    if strong_vertices:
        raise SystemExit(
            f"model is not a counterexample; strong vertices={strong_vertices}"
        )
    if args.matrix_output is not None:
        args.matrix_output.write_text(
            matrix, encoding="ascii", newline="\n"
        )
    args.output.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "verified": result["verified"],
                "order": order,
                "minimum_outdegree": result["minimum_outdegree"],
                "matrix_sha256": result["matrix_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()
