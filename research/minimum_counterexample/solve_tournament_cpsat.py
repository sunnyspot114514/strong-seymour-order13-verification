#!/usr/bin/env python3
"""Direct OR-Tools CP-SAT search for a tournament with no strong vertex."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ortools.sat.python import cp_model


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
    parser.add_argument("--time-limit", type=float, default=180)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--random-seed", type=int, default=20260729)
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

    model = cp_model.CpModel()
    orientation = {
        (u, v): model.NewBoolVar(f"a_{u}_{v}")
        for u in range(order)
        for v in range(u + 1, order)
    }
    cover = {
        (root, vertex): model.NewBoolVar(f"c_{root}_{vertex}")
        for root in range(order)
        for vertex in range(order)
        if root != vertex
    }

    def arc(tail: int, head: int):
        return (
            orientation[tail, head]
            if tail < head
            else orientation[head, tail].Not()
        )

    for vertex in range(1, order):
        model.Add(arc(0, vertex) == (vertex <= root_degree))

    if args.fix_matrix is not None:
        fixed = read_and_relabel_matrix(
            args.fix_matrix, order, root_degree
        )
        for u in range(order):
            for v in range(u + 1, order):
                model.Add(orientation[u, v] == (fixed[u][v] == "1"))
    else:
        chosen = set(range(1, 1 + p))
        chosen.update(range(root_degree + 1, root_degree + 1 + q))
        for vertex in range(1, order):
            model.Add(cover[0, vertex] == (vertex in chosen))
        blocks = [
            list(range(1, 1 + p)),
            list(range(1 + p, 1 + root_degree)),
            list(range(root_degree + 1, root_degree + 1 + q)),
            list(range(root_degree + 1 + q, order)),
        ]
        for block in blocks:
            for tail, head in zip(block, block[1:]):
                model.Add(arc(tail, head) == 1)

    for root in range(order):
        model.Add(
            sum(arc(root, other) for other in range(order) if other != root)
            >= root_degree
        )
        for left in range(order):
            if left == root:
                continue
            for right in range(order):
                if right == root or right == left:
                    continue
                model.AddBoolOr(
                    [
                        arc(root, left).Not(),
                        arc(left, right).Not(),
                        arc(right, root).Not(),
                        cover[root, left],
                        cover[root, right],
                    ]
                )
        model.Add(
            sum(
                cover[root, vertex]
                for vertex in range(order)
                if vertex != root
            )
            + sum(
                arc(other, root)
                for other in range(order)
                if other != root
            )
            == order - 2
        )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = args.random_seed
    status = solver.Solve(model)
    status_name = solver.StatusName(status)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result_name = "SAT"
    elif status == cp_model.INFEASIBLE:
        result_name = "UNSAT"
    else:
        result_name = "UNKNOWN"

    record: dict[str, object] = {
        "order": order,
        "root_degree": root_degree,
        "root_cover_left": p,
        "result": result_name,
        "status": status_name,
        "seconds": solver.WallTime(),
        "conflicts": solver.NumConflicts(),
        "branches": solver.NumBranches(),
        "workers": args.workers,
        "random_seed": args.random_seed,
    }
    if result_name == "SAT":
        adjacency = [[False] * order for _ in range(order)]
        for (u, v), variable in orientation.items():
            if solver.BooleanValue(variable):
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
        record["matrix_sha256"] = hashlib.sha256(
            text.encode("ascii")
        ).hexdigest()
        record["adjacency_matrix"] = text.splitlines()
        if args.matrix_output is not None:
            args.matrix_output.write_text(text, encoding="ascii")

    args.output.write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, separators=(",", ":")))


if __name__ == "__main__":
    main()
