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
    def __init__(self, exact_sequential: bool = False) -> None:
        self.variable_count = 0
        self.clauses: list[list[int]] = []
        self.names: dict[tuple, int] = {}
        self.exact_sequential = exact_sequential

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

    def at_most(
        self,
        literals: list[int],
        bound: int,
        prefix: tuple,
        gate: int | None = None,
    ) -> None:
        first_clause = len(self.clauses)
        count = len(literals)
        if bound >= count:
            return
        if bound < 0:
            self.add(*([gate] if gate is not None else []))
            return
        if bound == 0:
            for literal in literals:
                self.add(
                    *([gate] if gate is not None else []),
                    -literal,
                )
            return
        sequential = {
            (index, total): self.variable(prefix + (index, total))
            for index in range(1, count)
            for total in range(1, min(index, bound) + 1)
        }
        if self.exact_sequential:
            # Give every sequential-counter variable its exact threshold
            # meaning, even when the at-most constraint is gated off.  This
            # removes extension-variable freedom without changing the
            # projected solutions on the input literals.
            for index in range(1, count):
                self.add(-literals[index - 1], sequential[index, 1])
                if index == 1:
                    self.add(-sequential[index, 1], literals[index - 1])
                else:
                    self.add(
                        -sequential[index - 1, 1],
                        sequential[index, 1],
                    )
                    self.add(
                        -sequential[index, 1],
                        literals[index - 1],
                        sequential[index - 1, 1],
                    )
            for index in range(2, count):
                for total in range(2, min(index, bound) + 1):
                    self.add(
                        -literals[index - 1],
                        -sequential[index - 1, total - 1],
                        sequential[index, total],
                    )
                    previous_same = sequential.get((index - 1, total))
                    if previous_same is not None:
                        self.add(
                            -previous_same,
                            sequential[index, total],
                        )
                        self.add(
                            -sequential[index, total],
                            previous_same,
                            literals[index - 1],
                        )
                        self.add(
                            -sequential[index, total],
                            previous_same,
                            sequential[index - 1, total - 1],
                        )
                    else:
                        self.add(
                            -sequential[index, total],
                            literals[index - 1],
                        )
                        self.add(
                            -sequential[index, total],
                            sequential[index - 1, total - 1],
                        )
            for index in range(bound + 1, count + 1):
                self.add(
                    *([gate] if gate is not None else []),
                    -literals[index - 1],
                    -sequential[index - 1, bound],
                )
            return
        for index in range(1, count):
            self.add(-literals[index - 1], sequential[index, 1])
        for index in range(2, count):
            self.add(-sequential[index - 1, 1], sequential[index, 1])
        for index in range(2, count):
            for total in range(2, min(index, bound) + 1):
                self.add(
                    -literals[index - 1],
                    -sequential[index - 1, total - 1],
                    sequential[index, total],
                )
                if total <= index - 1:
                    self.add(
                        -sequential[index - 1, total],
                        sequential[index, total],
                    )
        for index in range(bound + 1, count + 1):
            self.add(-literals[index - 1], -sequential[index - 1, bound])
        if gate is not None:
            generated = self.clauses[first_clause:]
            del self.clauses[first_clause:]
            for clause in generated:
                self.add(gate, *clause)


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
    maximum_edge_flips: int | None = None,
    encoding: str = "hall",
    root_cover_left: int | None = None,
    symmetry: str = "hamilton",
    exact_sequential: bool = False,
) -> tuple[CNF, dict]:
    if not 0 <= root_degree < order:
        raise ValueError("invalid root degree")
    cnf = CNF(exact_sequential=exact_sequential)
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
        differences = [
            -arc(u, v) if fixed_matrix[u][v] == "1" else arc(u, v)
            for u in range(order)
            for v in range(u + 1, order)
        ]
        if maximum_edge_flips is None:
            for difference in differences:
                cnf.add(-difference)
        else:
            cnf.at_most(
                differences,
                maximum_edge_flips,
                ("maximum_edge_flips",),
            )

    if encoding in {"cover", "hybrid", "conditional-cover"}:
        cover_roots = list(range(order)) if encoding == "cover" else [0]
        if encoding == "conditional-cover":
            cover_roots = list(range(order))
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
            if symmetry == "hamilton":
                # Every tournament has a directed Hamiltonian path, so this
                # is a complete (not heuristic) symmetry break.
                for block in blocks:
                    for tail, head in zip(block, block[1:]):
                        cnf.add(arc(tail, head))
            elif symmetry == "degree":
                # The labels in each block may instead be sorted by total
                # outdegree.  The inequality d+(u) <= d+(v) is equivalent to
                # sum(out(u)) + sum(not out(v)) <= n-1.
                for block_index, block in enumerate(blocks):
                    for position, (lower, upper) in enumerate(
                        zip(block, block[1:])
                    ):
                        degree_comparison = [
                            arc(lower, other)
                            for other in range(order)
                            if other != lower
                        ] + [
                            -arc(upper, other)
                            for other in range(order)
                            if other != upper
                        ]
                        cnf.at_most(
                            degree_comparison,
                            order - 1,
                            (
                                "degree_symmetry",
                                block_index,
                                position,
                            ),
                        )
            elif symmetry == "block-degree":
                # Within each freely permutable membership block, sort by
                # the number of wins into the largest other block.  This is
                # another complete symmetry break and is often stronger for
                # highly unbalanced root-cover branches.
                for block_index, block in enumerate(blocks):
                    targets = [
                        candidate
                        for candidate_index, candidate in enumerate(blocks)
                        if (
                            candidate_index != block_index
                            and candidate
                            and {candidate_index, block_index} != {1, 3}
                        )
                    ]
                    if len(block) < 2 or not targets:
                        continue
                    target = max(targets, key=len)
                    for position, (lower, upper) in enumerate(
                        zip(block, block[1:])
                    ):
                        comparison = [
                            arc(lower, vertex) for vertex in target
                        ] + [
                            -arc(upper, vertex) for vertex in target
                        ]
                        cnf.at_most(
                            comparison,
                            len(target),
                            (
                                "block_degree_symmetry",
                                block_index,
                                position,
                            ),
                        )
            elif symmetry == "internal-degree":
                # Sort each block by outdegree inside its own induced
                # subtournament.  Internal scores are invariant under every
                # relabelling of that block, so this is also complete.
                for block_index, block in enumerate(blocks):
                    for position, (lower, upper) in enumerate(
                        zip(block, block[1:])
                    ):
                        comparison = [
                            arc(lower, vertex)
                            for vertex in block
                            if vertex != lower
                        ] + [
                            -arc(upper, vertex)
                            for vertex in block
                            if vertex != upper
                        ]
                        cnf.at_most(
                            comparison,
                            len(block) - 1,
                            (
                                "internal_degree_symmetry",
                                block_index,
                                position,
                            ),
                        )
            elif symmetry == "internal-degree-ties":
                # Sort by induced-subtournament score and, inside every
                # equal-score class, choose a directed Hamiltonian path.
                # Both operations only relabel vertices inside one block.
                for block_index, block in enumerate(blocks):
                    if len(block) < 2:
                        continue
                    score = {
                        (vertex, value): cnf.variable(
                            (
                                "internal_score",
                                block_index,
                                vertex,
                                value,
                            )
                        )
                        for vertex in block
                        for value in range(len(block))
                    }
                    for vertex in block:
                        cnf.add(
                            *[
                                score[vertex, value]
                                for value in range(len(block))
                            ]
                        )
                        outgoing = [
                            arc(vertex, other)
                            for other in block
                            if other != vertex
                        ]
                        for value in range(len(block)):
                            cnf.at_most(
                                outgoing,
                                value,
                                (
                                    "internal_score_upper",
                                    block_index,
                                    vertex,
                                    value,
                                ),
                                gate=-score[vertex, value],
                            )
                            cnf.at_most(
                                [-literal for literal in outgoing],
                                len(block) - 1 - value,
                                (
                                    "internal_score_lower",
                                    block_index,
                                    vertex,
                                    value,
                                ),
                                gate=-score[vertex, value],
                            )
                    for lower, upper in zip(block, block[1:]):
                        for lower_score in range(len(block)):
                            for upper_score in range(len(block)):
                                if lower_score > upper_score:
                                    cnf.add(
                                        -score[lower, lower_score],
                                        -score[upper, upper_score],
                                    )
                                elif lower_score == upper_score:
                                    cnf.add(
                                        -score[lower, lower_score],
                                        -score[upper, upper_score],
                                        arc(lower, upper),
                                    )
            elif symmetry in {
                "profile-ties",
                "full-profile-ties",
                "hierarchical-profile-ties",
                "out-first-profile-ties",
            }:
                # Refine the internal score by the number of wins into the
                # nonconstant external membership blocks (only the largest
                # one in the lighter "profile-ties" variant).  These scores
                # are invariant under every allowed block relabelling.  Sort
                # lexicographically by the profile and use a directed
                # Hamiltonian path only inside an exact-profile tie class.
                for block_index, block in enumerate(blocks):
                    if len(block) < 2:
                        continue
                    external_targets = [
                        candidate
                        for candidate_index, candidate in enumerate(blocks)
                        if (
                            candidate_index != block_index
                            and candidate
                            and {candidate_index, block_index} != {1, 3}
                        )
                    ]
                    components = [block]
                    if external_targets:
                        external_targets.sort(key=len, reverse=True)
                        components.extend(
                            external_targets
                            if symmetry
                            in {
                                "full-profile-ties",
                                "hierarchical-profile-ties",
                                "out-first-profile-ties",
                            }
                            else external_targets[:1]
                        )
                    if symmetry in {
                        "hierarchical-profile-ties",
                        "out-first-profile-ties",
                    }:
                        # Break the remaining equal-count symmetries
                        # acyclically.  The default hierarchy starts with
                        # block 2; the out-first variant starts with block 1.
                        # A later block may use its individual adjacencies
                        # into already canonicalized blocks as further
                        # lexicographic components.
                        #
                        # Relabelling the later block changes only aggregate
                        # win counts seen by every earlier block, so all
                        # earlier profile constraints remain invariant.
                        hierarchy = (
                            [1, 2, 3, 0]
                            if symmetry == "out-first-profile-ties"
                            else [2, 1, 3, 0]
                        )
                        current_rank = hierarchy.index(block_index)
                        for earlier_index in hierarchy[:current_rank]:
                            earlier = blocks[earlier_index]
                            if (
                                not earlier
                                or {earlier_index, block_index} == {1, 3}
                            ):
                                continue
                            components.extend(
                                [[vertex] for vertex in earlier]
                            )

                    component_scores: list[
                        dict[tuple[int, int], int]
                    ] = []
                    for component_index, target in enumerate(components):
                        maximum_score = len(target) - (
                            1 if target is block else 0
                        )
                        score = {
                            (vertex, value): cnf.variable(
                                (
                                    "profile_score",
                                    block_index,
                                    component_index,
                                    vertex,
                                    value,
                                )
                            )
                            for vertex in block
                            for value in range(maximum_score + 1)
                        }
                        component_scores.append(score)
                        for vertex in block:
                            cnf.add(
                                *[
                                    score[vertex, value]
                                    for value in range(maximum_score + 1)
                                ]
                            )
                            outgoing = [
                                arc(vertex, other)
                                for other in target
                                if other != vertex
                            ]
                            for value in range(maximum_score + 1):
                                cnf.at_most(
                                    outgoing,
                                    value,
                                    (
                                        "profile_score_upper",
                                        block_index,
                                        component_index,
                                        vertex,
                                        value,
                                    ),
                                    gate=-score[vertex, value],
                                )
                                cnf.at_most(
                                    [-literal for literal in outgoing],
                                    maximum_score - value,
                                    (
                                        "profile_score_lower",
                                        block_index,
                                        component_index,
                                        vertex,
                                        value,
                                    ),
                                    gate=-score[vertex, value],
                                )

                    for pair_index, (lower, upper) in enumerate(
                        zip(block, block[1:])
                    ):
                        equal_prefix: int | None = None
                        for component_index, score in enumerate(
                            component_scores
                        ):
                            values = list(
                                range(
                                    max(
                                        value
                                        for vertex, value in score
                                        if vertex == lower
                                    )
                                    + 1
                                )
                            )
                            prefix_gate = (
                                [] if equal_prefix is None
                                else [-equal_prefix]
                            )
                            for lower_score in values:
                                for upper_score in values:
                                    if lower_score > upper_score:
                                        cnf.add(
                                            *prefix_gate,
                                            -score[lower, lower_score],
                                            -score[upper, upper_score],
                                        )
                            next_equal_prefix = cnf.variable(
                                (
                                    "profile_equal_prefix",
                                    block_index,
                                    pair_index,
                                    component_index,
                                )
                            )
                            # next_equal_prefix is equivalent to:
                            #
                            #   equal_prefix AND
                            #   score(lower) == score(upper).
                            #
                            # The reverse implications are essential.
                            # Without them a solver may set an equality
                            # prefix false and bypass all later lexicographic
                            # profile components.
                            if equal_prefix is not None:
                                cnf.add(
                                    -next_equal_prefix,
                                    equal_prefix,
                                )
                            for value in values:
                                cnf.add(
                                    *prefix_gate,
                                    -score[lower, value],
                                    -score[upper, value],
                                    next_equal_prefix,
                                )
                                cnf.add(
                                    -next_equal_prefix,
                                    -score[lower, value],
                                    score[upper, value],
                                )
                                cnf.add(
                                    -next_equal_prefix,
                                    -score[upper, value],
                                    score[lower, value],
                                )
                            equal_prefix = next_equal_prefix
                        if equal_prefix is None:
                            raise AssertionError(
                                "profile has no score components"
                            )
                        cnf.add(
                            -equal_prefix,
                            arc(lower, upper),
                        )
            elif symmetry != "none":
                raise ValueError(f"unknown symmetry break: {symmetry}")
        high_degree: dict[int, int] = {}
        if encoding == "conditional-cover":
            low_degree_maximum = (order - 1) // 2
            high_degree = {
                root: cnf.variable(("high_degree", root))
                for root in range(order)
            }
            for root in range(order):
                outgoing = [
                    arc(root, other)
                    for other in range(order)
                    if other != root
                ]
                incoming = [-literal for literal in outgoing]
                # high_degree iff d+(root) >= low_degree_maximum + 1.
                cnf.at_most(
                    incoming,
                    order - 2 - low_degree_maximum,
                    ("high_implies_degree", root),
                    gate=-high_degree[root],
                )
                cnf.at_most(
                    outgoing,
                    low_degree_maximum,
                    ("low_implies_degree", root),
                    gate=high_degree[root],
                )
            cnf.add(-high_degree[0])

            # The total outdegree of a tournament is n(n-1)/2.  Since every
            # vertex has outdegree at least root_degree, every high-degree
            # vertex consumes at least
            #
            #     low_degree_maximum + 1 - root_degree
            #
            # units of the total excess above that minimum.  Bounding the
            # number of high-degree flags is therefore implied, but exposes
            # useful global propagation to the SAT solver.
            excess = order * (order - 1) // 2 - order * root_degree
            high_degree_excess = (
                low_degree_maximum + 1 - root_degree
            )
            maximum_high_degree_vertices = (
                excess // high_degree_excess
            )
            cnf.at_most(
                list(high_degree.values()),
                maximum_high_degree_vertices,
                ("maximum_high_degree_vertices",),
            )

        for root in cover_roots:
            # Cover every edge of the matching graph. The antecedent is
            # exactly the directed triangle root -> left -> right -> root.
            for left in range(order):
                if left == root:
                    continue
                for right in range(order):
                    if right == root or right == left:
                        continue
                    edge_cover_clause = [
                        -arc(root, left),
                        -arc(left, right),
                        -arc(right, root),
                        cover[root, left],
                        cover[root, right],
                    ]
                    if encoding == "conditional-cover":
                        edge_cover_clause.insert(0, high_degree[root])
                    cnf.add(*edge_cover_clause)

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
                gate=(
                    high_degree[root]
                    if encoding == "conditional-cover"
                    else None
                ),
            )
            # Any smaller cover can be padded to size d+(r)-1. Requiring the
            # padded equality removes many equivalent witness assignments:
            # |C_r| + d-(r) = n-2.
            cnf.at_most(
                [-literal for literal in cardinality_literals],
                len(cardinality_literals) - (order - 2),
                ("padded_cover_equality", root),
                gate=(
                    high_degree[root]
                    if encoding == "conditional-cover"
                    else None
                ),
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
        "symmetry": symmetry,
        "cardinality_encoder": (
            "exact_triangular_sequential"
            if exact_sequential
            else "triangular_sinz_sequential"
        ),
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
        "--near-matrix",
        type=Path,
        help=(
            "restrict the result to a Hamming ball around this matrix after "
            "the same root relabelling as --fix-matrix"
        ),
    )
    parser.add_argument(
        "--max-edge-flips",
        type=int,
        help="radius of --near-matrix in reversed tournament edges",
    )
    parser.add_argument(
        "--encoding",
        choices=("hall", "cover", "hybrid", "conditional-cover"),
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
    parser.add_argument(
        "--symmetry",
        choices=(
            "hamilton",
            "degree",
            "block-degree",
            "internal-degree",
            "internal-degree-ties",
            "profile-ties",
            "full-profile-ties",
            "hierarchical-profile-ties",
            "out-first-profile-ties",
            "none",
        ),
        default="hamilton",
        help=(
            "complete symmetry break inside the four root-membership blocks"
        ),
    )
    parser.add_argument(
        "--exact-sequential",
        action="store_true",
        help=(
            "define every sequential-counter threshold variable in both "
            "directions, including inside gated constraints"
        ),
    )
    args = parser.parse_args()
    if args.fix_matrix is not None and args.near_matrix is not None:
        parser.error("--fix-matrix and --near-matrix are mutually exclusive")
    if (args.near_matrix is None) != (args.max_edge_flips is None):
        parser.error("--near-matrix and --max-edge-flips must be used together")
    if args.max_edge_flips is not None and args.max_edge_flips < 0:
        parser.error("--max-edge-flips must be nonnegative")
    fixed_matrix = None
    fixed_matrix_sha256 = None
    matrix_path = (
        args.fix_matrix
        if args.fix_matrix is not None
        else args.near_matrix
    )
    if matrix_path is not None:
        fixed_matrix, fixed_matrix_sha256 = read_and_relabel_matrix(
            matrix_path, args.order, args.root_degree
        )
    if args.root_cover_left is not None and args.encoding not in {
        "cover",
        "hybrid",
        "conditional-cover",
    }:
        parser.error("--root-cover-left requires --encoding cover or hybrid")
    cnf, metadata = build(
        args.order,
        args.root_degree,
        fixed_matrix,
        args.max_edge_flips,
        args.encoding,
        args.root_cover_left,
        args.symmetry,
        args.exact_sequential,
    )
    if fixed_matrix_sha256 is not None:
        if args.fix_matrix is not None:
            metadata["fixed_matrix_sha256"] = fixed_matrix_sha256
        else:
            metadata["near_matrix_sha256"] = fixed_matrix_sha256
            metadata["maximum_edge_flips"] = args.max_edge_flips
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
