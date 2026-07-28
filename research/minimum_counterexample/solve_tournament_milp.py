#!/usr/bin/env python3
"""Direct 0-1 MILP search for a tournament with no strong vertex."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


def read_and_relabel_matrix(
    path: Path, order: int, root_degree: int
) -> list[str]:
    rows = [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]
    if len(rows) != order or any(
        len(row) != order or set(row) - {"0", "1"} for row in rows
    ):
        raise ValueError("fixed matrix has the wrong size or alphabet")
    for u in range(order):
        if rows[u][u] != "0":
            raise ValueError("fixed matrix has a loop")
        for v in range(u + 1, order):
            if (rows[u][v] == "1") == (rows[v][u] == "1"):
                raise ValueError("fixed matrix is not a tournament")
    roots = [
        vertex
        for vertex, row in enumerate(rows)
        if row.count("1") == root_degree
    ]
    if not roots:
        raise ValueError("fixed matrix has no root of the requested degree")
    root = roots[0]
    permutation = [root]
    permutation.extend(v for v in range(order) if rows[root][v] == "1")
    permutation.extend(
        v for v in range(order) if v != root and rows[v][root] == "1"
    )
    return [
        "".join(rows[permutation[u]][permutation[v]] for v in range(order))
        for u in range(order)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("order", type=int)
    parser.add_argument("root_degree", type=int)
    parser.add_argument("root_cover_left", type=int)
    parser.add_argument("output", type=Path)
    parser.add_argument("--time-limit", type=float)
    parser.add_argument("--fix-matrix", type=Path)
    parser.add_argument("--matrix-output", type=Path)
    args = parser.parse_args()

    order = args.order
    root_degree = args.root_degree
    p = args.root_cover_left
    q = root_degree - 1 - p
    indegree = order - 1 - root_degree
    if not 0 <= p <= root_degree or not 0 <= q <= indegree:
        raise ValueError("invalid root-cover split")

    orientation: dict[tuple[int, int], int] = {}
    variable_count = 0
    for u in range(order):
        for v in range(u + 1, order):
            orientation[u, v] = variable_count
            variable_count += 1
    cover: dict[tuple[int, int], int] = {}
    for root in range(order):
        for vertex in range(order):
            if vertex != root:
                cover[root, vertex] = variable_count
                variable_count += 1

    # Return coefficient, variable index, and constant for a 0-1 arc value.
    def arc(tail: int, head: int) -> tuple[int, int, int]:
        if tail < head:
            return 1, orientation[tail, head], 0
        return -1, orientation[head, tail], 1

    row_indices: list[int] = []
    column_indices: list[int] = []
    values: list[float] = []
    row_lower: list[float] = []
    row_upper: list[float] = []

    def add_row(entries: dict[int, float], lo: float, hi: float) -> None:
        row = len(row_lower)
        for column, value in entries.items():
            if value:
                row_indices.append(row)
                column_indices.append(column)
                values.append(value)
        row_lower.append(lo)
        row_upper.append(hi)

    lower_bounds = np.zeros(variable_count)
    upper_bounds = np.ones(variable_count)

    # Canonically label a minimum-degree root and its out-/in-neighbours.
    for vertex in range(1, order):
        coefficient, variable, constant = arc(0, vertex)
        required = 1 if vertex <= root_degree else 0
        fixed = (required - constant) / coefficient
        lower_bounds[variable] = fixed
        upper_bounds[variable] = fixed
    if args.fix_matrix is not None:
        fixed_matrix = read_and_relabel_matrix(
            args.fix_matrix, order, root_degree
        )
        for (u, v), variable in orientation.items():
            value = 1 if fixed_matrix[u][v] == "1" else 0
            lower_bounds[variable] = value
            upper_bounds[variable] = value

    if args.fix_matrix is None:
        # Fix a padded size-(d-1) cover at root 0.
        chosen = set(range(1, 1 + p))
        chosen.update(range(root_degree + 1, root_degree + 1 + q))
        for vertex in range(1, order):
            value = 1 if vertex in chosen else 0
            variable = cover[0, vertex]
            lower_bounds[variable] = value
            upper_bounds[variable] = value

        # Directed Hamiltonian paths inside the four interchangeable blocks.
        blocks = [
            list(range(1, 1 + p)),
            list(range(1 + p, 1 + root_degree)),
            list(range(root_degree + 1, root_degree + 1 + q)),
            list(range(root_degree + 1 + q, order)),
        ]
        for block in blocks:
            for tail, head in zip(block, block[1:]):
                coefficient, variable, constant = arc(tail, head)
                fixed = (1 - constant) / coefficient
                lower_bounds[variable] = fixed
                upper_bounds[variable] = fixed

    # Vertex 0 is selected to have minimum outdegree.
    for root in range(order):
        entries: dict[int, float] = {}
        constant = 0
        for other in range(order):
            if other == root:
                continue
            coefficient, variable, offset = arc(root, other)
            entries[variable] = entries.get(variable, 0) + coefficient
            constant += offset
        add_row(entries, root_degree - constant, np.inf)

    for root in range(order):
        # Cover every directed-triangle matching edge.
        for left in range(order):
            if left == root:
                continue
            for right in range(order):
                if right == root or right == left:
                    continue
                entries = {
                    cover[root, left]: 1,
                    cover[root, right]: 1,
                }
                triangle_constant = 0
                for tail, head in (
                    (root, left),
                    (left, right),
                    (right, root),
                ):
                    coefficient, variable, offset = arc(tail, head)
                    entries[variable] = entries.get(variable, 0) - coefficient
                    triangle_constant -= offset
                # c(left)+c(right)-a-b-c >= -2.
                add_row(entries, -2 - triangle_constant, np.inf)

        # Pad every cover to size d+(root)-1:
        # |C_root| + d-(root) = n-2.
        entries = {
            cover[root, vertex]: 1
            for vertex in range(order)
            if vertex != root
        }
        constant = 0
        for other in range(order):
            if other == root:
                continue
            coefficient, variable, offset = arc(other, root)
            entries[variable] = entries.get(variable, 0) + coefficient
            constant += offset
        target = order - 2 - constant
        add_row(entries, target, target)

    matrix = coo_matrix(
        (values, (row_indices, column_indices)),
        shape=(len(row_lower), variable_count),
    ).tocsr()
    options: dict[str, float | bool] = {"presolve": True, "mip_rel_gap": 0}
    if args.time_limit is not None:
        options["time_limit"] = args.time_limit
    started = time.perf_counter()
    result = milp(
        np.zeros(variable_count),
        integrality=np.ones(variable_count),
        bounds=Bounds(lower_bounds, upper_bounds),
        constraints=LinearConstraint(matrix, row_lower, row_upper),
        options=options,
    )
    elapsed = time.perf_counter() - started

    record: dict[str, object] = {
        "order": order,
        "root_degree": root_degree,
        "root_cover_left": p,
        "variables": variable_count,
        "constraints": len(row_lower),
        "seconds": elapsed,
        "status": int(result.status),
        "message": result.message,
        "success": bool(result.success),
    }
    if result.success and result.x is not None:
        adjacency = [[False] * order for _ in range(order)]
        for (u, v), variable in orientation.items():
            if result.x[variable] > 0.5:
                adjacency[u][v] = True
            else:
                adjacency[v][u] = True
        text = (
            "\n".join(
                "".join("1" if adjacency[u][v] else "0" for v in range(order))
                for u in range(order)
            )
            + "\n"
        )
        record["result"] = "SAT"
        record["matrix_sha256"] = hashlib.sha256(
            text.encode("ascii")
        ).hexdigest()
        record["adjacency_matrix"] = text.splitlines()
        if args.matrix_output is not None:
            args.matrix_output.write_text(text, encoding="ascii")
    elif result.status == 2:
        record["result"] = "UNSAT"
    else:
        record["result"] = "UNKNOWN"

    args.output.write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: record[key]
                for key in (
                    "order",
                    "root_degree",
                    "root_cover_left",
                    "result",
                    "seconds",
                    "variables",
                    "constraints",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
