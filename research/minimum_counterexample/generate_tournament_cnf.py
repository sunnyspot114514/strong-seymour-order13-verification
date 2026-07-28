#!/usr/bin/env python3
"""Encode a tournament with no strong Seymour vertex.

For a root r, the matching graph has an edge y--z exactly when
r -> y -> z -> r is a directed triangle. By Konig's theorem, r is
non-strong iff this bipartite graph has a vertex cover C_r with
|C_r| <= d+(r)-1. Since d+(r) = n-1-d-(r), this is equivalent to

    |C_r| + d-(r) <= n-2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class CNF:
    def __init__(self) -> None:
        self.variable_count = 0
        self.clauses: list[list[int]] = []
        self.names: dict[tuple, int] = {}

    def variable(self, name: tuple) -> int:
        if name not in self.names:
            self.variable_count += 1
            self.names[name] = self.variable_count
        return self.names[name]

    def add(self, *literals: int) -> None:
        clause: list[int] = []
        seen: set[int] = set()
        for literal in literals:
            if -literal in seen:
                return
            if literal not in seen:
                seen.add(literal)
                clause.append(literal)
        self.clauses.append(clause)

    def at_most(self, literals: list[int], bound: int, prefix: tuple) -> None:
        count = len(literals)
        if bound >= count:
            return
        if bound < 0:
            self.add()
            return
        if bound == 0:
            for literal in literals:
                self.add(-literal)
            return
        sequential = {
            (index, total): self.variable(prefix + (index, total))
            for index in range(1, count)
            for total in range(1, bound + 1)
        }
        for index in range(1, count):
            self.add(-literals[index - 1], sequential[index, 1])
        for index in range(2, count):
            self.add(-sequential[index - 1, 1], sequential[index, 1])
        for index in range(2, count):
            for total in range(2, bound + 1):
                self.add(
                    -literals[index - 1],
                    -sequential[index - 1, total - 1],
                    sequential[index, total],
                )
                self.add(
                    -sequential[index - 1, total],
                    sequential[index, total],
                )
        for index in range(2, count + 1):
            self.add(-literals[index - 1], -sequential[index - 1, bound])


def read_and_relabel_matrix(
    path: Path, order: int, root_degree: int
) -> tuple[list[str], str]:
    rows = [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]
    if len(rows) != order or any(
        len(row) != order or set(row) - {"0", "1"} for row in rows
    ):
        raise ValueError(f"{path} is not an {order} by {order} zero-one matrix")
    for u in range(order):
        if rows[u][u] != "0":
            raise ValueError("matrix diagonal must be zero")
        for v in range(u + 1, order):
            if (rows[u][v] == "1") == (rows[v][u] == "1"):
                raise ValueError(f"matrix is not a tournament at pair {u},{v}")

    roots = [
        vertex
        for vertex, row in enumerate(rows)
        if row.count("1") == root_degree
    ]
    if not roots:
        raise ValueError(
            f"matrix has no vertex of requested root degree {root_degree}"
        )
    root = roots[0]
    out_neighbours = [
        vertex for vertex in range(order) if rows[root][vertex] == "1"
    ]
    in_neighbours = [
        vertex
        for vertex in range(order)
        if vertex != root and rows[vertex][root] == "1"
    ]
    permutation = [root] + out_neighbours + in_neighbours
    relabelled = [
        "".join(rows[permutation[u]][permutation[v]] for v in range(order))
        for u in range(order)
    ]
    digest = hashlib.sha256(
        ("\n".join(rows) + "\n").encode("ascii")
    ).hexdigest()
    return relabelled, digest


def build(
    order: int,
    root_degree: int,
    fixed_matrix: list[str] | None = None,
    encoding: str = "hall",
    root_cover_left: int | None = None,
) -> tuple[CNF, dict]:
    if not 0 <= root_degree < order:
        raise ValueError("invalid root degree")
    cnf = CNF()
    orientation = {
        (u, v): cnf.variable(("orientation", u, v))
        for u in range(order)
        for v in range(u + 1, order)
    }
    def arc(tail: int, head: int) -> int:
        return (
            orientation[tail, head]
            if tail < head
            else -orientation[head, tail]
        )

    # Relabel a minimum-outdegree vertex as 0, then independently relabel
    # its out- and in-neighbours.
    for vertex in range(1, order):
        cnf.add(
            arc(0, vertex)
            if vertex <= root_degree
            else -arc(0, vertex)
        )

    # Vertex 0 is chosen to have minimum outdegree. This is both a valid
    # canonical choice for every tournament and an important symmetry break.
    maximum_indegree = order - 1 - root_degree
    for vertex in range(order):
        cnf.at_most(
            [
                arc(other, vertex)
                for other in range(order)
                if other != vertex
            ],
            maximum_indegree,
            ("minimum_outdegree", vertex),
        )
        if 2 * root_degree == order - 1:
            # At the average degree, the lower bounds force regularity.
            # Adding the implied upper bounds substantially strengthens unit
            # propagation without changing the represented tournaments.
            cnf.at_most(
                [
                    arc(vertex, other)
                    for other in range(order)
                    if other != vertex
                ],
                root_degree,
                ("regular_outdegree", vertex),
            )

    if fixed_matrix is not None:
        for u in range(order):
            for v in range(u + 1, order):
                cnf.add(arc(u, v) if fixed_matrix[u][v] == "1" else -arc(u, v))

    if encoding in {"cover", "hybrid"}:
        cover_roots = list(range(order)) if encoding == "cover" else [0]
        cover = {
            (root, vertex): cnf.variable(("cover", root, vertex))
            for root in cover_roots
            for vertex in range(order)
            if root != vertex
        }
        if root_cover_left is not None:
            root_cover_right = root_degree - 1 - root_cover_left
            indegree = order - 1 - root_degree
            if not 0 <= root_cover_left <= root_degree:
                raise ValueError("invalid number of root-cover left vertices")
            if not 0 <= root_cover_right <= indegree:
                raise ValueError("root-cover right part exceeds the indegree")
            chosen = set(range(1, 1 + root_cover_left))
            chosen.update(
                range(
                    root_degree + 1,
                    root_degree + 1 + root_cover_right,
                )
            )
            for vertex in range(1, order):
                cnf.add(
                    cover[0, vertex]
                    if vertex in chosen
                    else -cover[0, vertex]
                )
            # The four membership blocks can each be relabelled freely.
            # Every tournament has a directed Hamiltonian path, so requiring
            # consecutive labels in each block to point forward is a complete
            # (not heuristic) symmetry break.
            blocks = [
                list(range(1, 1 + root_cover_left)),
                list(range(1 + root_cover_left, 1 + root_degree)),
                list(
                    range(
                        root_degree + 1,
                        root_degree + 1 + root_cover_right,
                    )
                ),
                list(
                    range(
                        root_degree + 1 + root_cover_right,
                        order,
                    )
                ),
            ]
            for block in blocks:
                for tail, head in zip(block, block[1:]):
                    cnf.add(arc(tail, head))
        for root in cover_roots:
            # Cover every edge of the matching graph. The antecedent is
            # exactly the directed triangle root -> left -> right -> root.
            for left in range(order):
                if left == root:
                    continue
                for right in range(order):
                    if right == root or right == left:
                        continue
                    cnf.add(
                        -arc(root, left),
                        -arc(left, right),
                        -arc(right, root),
                        cover[root, left],
                        cover[root, right],
                    )

            # |C_r| + d-(r) <= n-2.
            cardinality_literals = [
                cover[root, vertex]
                for vertex in range(order)
                if vertex != root
            ] + [
                arc(vertex, root)
                for vertex in range(order)
                if vertex != root
            ]
            cnf.at_most(
                cardinality_literals,
                order - 2,
                ("cover_plus_indegree", root),
            )
            # Any smaller cover can be padded to size d+(r)-1. Requiring the
            # padded equality removes many equivalent witness assignments:
            # |C_r| + d-(r) = n-2.
            cnf.at_most(
                [-literal for literal in cardinality_literals],
                len(cardinality_literals) - (order - 2),
                ("padded_cover_equality", root),
            )
        if encoding == "hybrid":
            selected = {
                (root, vertex): cnf.variable(("selected", root, vertex))
                for root in range(1, order)
                for vertex in range(order)
                if root != vertex
            }
            gamma = {
                (root, vertex): cnf.variable(("gamma", root, vertex))
                for root in range(1, order)
                for vertex in range(order)
                if root != vertex
            }
            for root in range(1, order):
                for vertex in range(order):
                    if vertex == root:
                        continue
                    cnf.add(-selected[root, vertex], arc(root, vertex))
                    cnf.add(-gamma[root, vertex], arc(vertex, root))
                for left in range(order):
                    if left == root:
                        continue
                    for right in range(order):
                        if right == root or right == left:
                            continue
                        cnf.add(
                            -selected[root, left],
                            -arc(left, right),
                            -arc(right, root),
                            gamma[root, right],
                        )
                cardinality_literals = [
                    gamma[root, vertex]
                    for vertex in range(order)
                    if vertex != root
                ] + [
                    -selected[root, vertex]
                    for vertex in range(order)
                    if vertex != root
                ]
                cnf.at_most(
                    cardinality_literals,
                    order - 2,
                    ("hall_defect", root),
                )
    elif encoding == "hall":
        selected = {
            (root, vertex): cnf.variable(("selected", root, vertex))
            for root in range(order)
            for vertex in range(order)
            if root != vertex
        }
        gamma = {
            (root, vertex): cnf.variable(("gamma", root, vertex))
            for root in range(order)
            for vertex in range(order)
            if root != vertex
        }
        for root in range(order):
            for vertex in range(order):
                if vertex == root:
                    continue
                # S is a subset of the out-neighbourhood, while Gamma is a
                # subset of the in-neighbourhood.
                cnf.add(-selected[root, vertex], arc(root, vertex))
                cnf.add(-gamma[root, vertex], arc(vertex, root))

            # Every strict second neighbour reached from S belongs to Gamma.
            for left in range(order):
                if left == root:
                    continue
                for right in range(order):
                    if right == root or right == left:
                        continue
                    cnf.add(
                        -selected[root, left],
                        -arc(left, right),
                        -arc(right, root),
                        gamma[root, right],
                    )

            # |Gamma(S)| < |S|, written as
            # |Gamma(S)| + |V \ ({root} union S)| <= n-2.
            cardinality_literals = [
                gamma[root, vertex]
                for vertex in range(order)
                if vertex != root
            ] + [
                -selected[root, vertex]
                for vertex in range(order)
                if vertex != root
            ]
            cnf.at_most(
                cardinality_literals,
                order - 2,
                ("hall_defect", root),
            )
    else:
        raise ValueError(f"unknown encoding: {encoding}")

    metadata = {
        "order": order,
        "root_degree": root_degree,
        "variables": cnf.variable_count,
        "clauses": len(cnf.clauses),
        "orientation_variables": {
            f"{u},{v}": variable
            for (u, v), variable in orientation.items()
        },
        "encoding": encoding,
    }
    if root_cover_left is not None:
        metadata["root_cover_left"] = root_cover_left
        metadata["root_cover_right"] = (
            root_degree - 1 - root_cover_left
        )
    return cnf, metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("order", type=int)
    parser.add_argument("root_degree", type=int)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--fix-matrix",
        type=Path,
        help=(
            "fix all orientations to this adjacency matrix after relabelling "
            "a vertex of the requested root degree as vertex 0"
        ),
    )
    parser.add_argument(
        "--encoding",
        choices=("hall", "cover", "hybrid"),
        default="hall",
        help="encode non-strong roots by Hall defects or vertex covers",
    )
    parser.add_argument(
        "--root-cover-left",
        type=int,
        help=(
            "with --encoding cover, canonically fix a padded size d-1 "
            "cover for root 0 with this many out-neighbour vertices"
        ),
    )
    args = parser.parse_args()
    fixed_matrix = None
    fixed_matrix_sha256 = None
    if args.fix_matrix is not None:
        fixed_matrix, fixed_matrix_sha256 = read_and_relabel_matrix(
            args.fix_matrix, args.order, args.root_degree
        )
    if args.root_cover_left is not None and args.encoding not in {
        "cover",
        "hybrid",
    }:
        parser.error("--root-cover-left requires --encoding cover or hybrid")
    cnf, metadata = build(
        args.order,
        args.root_degree,
        fixed_matrix,
        args.encoding,
        args.root_cover_left,
    )
    if fixed_matrix_sha256 is not None:
        metadata["fixed_matrix_sha256"] = fixed_matrix_sha256
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="ascii", newline="\n") as output:
        output.write(
            f"c order {args.order} tournament counterexample, "
            f"root degree {args.root_degree}\n"
        )
        output.write(f"p cnf {cnf.variable_count} {len(cnf.clauses)}\n")
        for clause in cnf.clauses:
            output.write(" ".join(map(str, clause)) + " 0\n")
    args.output.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "order": args.order,
                "root_degree": args.root_degree,
                "variables": cnf.variable_count,
                "clauses": len(cnf.clauses),
            }
        )
    )


if __name__ == "__main__":
    main()
