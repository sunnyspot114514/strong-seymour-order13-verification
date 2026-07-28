#!/usr/bin/env python3
"""Independent direct audit of the six-cluster order-36 counterexample."""

from __future__ import annotations

import hashlib
import itertools
import json

try:
    import networkx as nx
except ImportError:
    nx = None


WEIGHTS = (11, 7, 3, 3, 3, 9)
TEMPLATE_OUT = (
    frozenset((1, 2, 4)),
    frozenset((3, 4, 5)),
    frozenset((1, 5)),
    frozenset((0, 2)),
    frozenset((2, 3, 5)),
    frozenset((0, 3)),
)
CLASS_DEFECTS = (
    frozenset((1, 2, 4)),
    frozenset((3, 4, 5)),
    frozenset((1,)),
    frozenset((0,)),
    frozenset((3, 5)),
    frozenset((0, 3)),
)
EXPECTED_GAMMA = (
    frozenset((3, 5)),
    frozenset((0, 2)),
    frozenset((3, 4)),
    frozenset((1, 4)),
    frozenset((0,)),
    frozenset((1, 2, 4)),
)
EXPECTED_MATRIX_SHA256 = (
    "ce1ce6f2e86b7e4546477e1f821e2ccb155836c58ee27418252930fe4c585985"
)


def construct() -> tuple[list[list[bool]], list[int], list[list[int]]]:
    classes: list[list[int]] = []
    vertex_class: list[int] = []
    for class_index, weight in enumerate(WEIGHTS):
        classes.append(list(range(len(vertex_class), len(vertex_class) + weight)))
        vertex_class.extend([class_index] * weight)
    n = len(vertex_class)
    adjacency = [[False] * n for _ in range(n)]
    for u in range(n):
        for v in range(n):
            adjacency[u][v] = vertex_class[v] in TEMPLATE_OUT[vertex_class[u]]
    return adjacency, vertex_class, classes


def neighborhoods(
    adjacency: list[list[bool]], root: int
) -> tuple[list[int], list[int]]:
    first = [v for v, arc in enumerate(adjacency[root]) if arc]
    first_set = set(first)
    second = [
        z
        for z in range(len(adjacency))
        if z != root
        and z not in first_set
        and any(adjacency[y][z] for y in first)
    ]
    return first, second


def rows_for(
    adjacency: list[list[bool]], left: list[int], right: list[int]
) -> list[int]:
    return [
        sum(1 << j for j, v in enumerate(right) if adjacency[u][v])
        for u in left
    ]


def dp_matching(rows: list[int]) -> int:
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


def nx_matching(
    adjacency: list[list[bool]], left: list[int], right: list[int]
) -> int:
    assert nx is not None
    graph = nx.Graph()
    left_nodes = [("L", u) for u in left]
    right_nodes = [("R", v) for v in right]
    graph.add_nodes_from(left_nodes, bipartite=0)
    graph.add_nodes_from(right_nodes, bipartite=1)
    graph.add_edges_from(
        (("L", u), ("R", v))
        for u in left
        for v in right
        if adjacency[u][v]
    )
    matching = nx.algorithms.bipartite.maximum_matching(
        graph, top_nodes=set(left_nodes)
    )
    return sum(node in matching for node in left_nodes)


def hall_defect(
    left: list[int], right: list[int], rows: list[int]
) -> tuple[list[int], list[int]]:
    for size in range(1, len(left) + 1):
        for indices in itertools.combinations(range(len(left)), size):
            gamma = 0
            for index in indices:
                gamma |= rows[index]
            if gamma.bit_count() < size:
                return (
                    [left[index] for index in indices],
                    [
                        right[index]
                        for index in range(len(right))
                        if gamma & (1 << index)
                    ],
                )
    raise AssertionError("No Hall defect")


def main() -> None:
    for u in range(6):
        assert u not in TEMPLATE_OUT[u]
        for v in range(u + 1, 6):
            assert (v in TEMPLATE_OUT[u]) ^ (u in TEMPLATE_OUT[v])

    adjacency, vertex_class, classes = construct()
    n = len(adjacency)
    assert n == 36
    assert all(not adjacency[u][u] for u in range(n))
    for u in range(n):
        for v in range(u + 1, n):
            if vertex_class[u] == vertex_class[v]:
                assert not adjacency[u][v] and not adjacency[v][u]
            else:
                assert adjacency[u][v] ^ adjacency[v][u]

    matrix = (
        "\n".join(
            "".join("1" if adjacency[u][v] else "0" for v in range(n))
            for u in range(n)
        )
        + "\n"
    ).encode("ascii")
    digest = hashlib.sha256(matrix).hexdigest()
    assert digest == EXPECTED_MATRIX_SHA256

    vertices = []
    for root in range(n):
        left, right = neighborhoods(adjacency, root)
        rows = rows_for(adjacency, left, right)
        dp_size = dp_matching(rows)
        nx_size = dp_size if nx is None else nx_matching(adjacency, left, right)
        defect_s, defect_gamma = hall_defect(left, right, rows)
        assert dp_size == nx_size < len(left)
        assert len(defect_gamma) < len(defect_s)
        vertices.append(
            {
                "vertex": root,
                "class": vertex_class[root],
                "outdegree": len(left),
                "strict_second": len(right),
                "matching": dp_size,
            }
        )

    class_certificates = []
    for root_class, selected_classes in enumerate(CLASS_DEFECTS):
        root = classes[root_class][0]
        left, right = neighborhoods(adjacency, root)
        selected = [
            vertex
            for class_index in selected_classes
            for vertex in classes[class_index]
        ]
        gamma = [
            z for z in right if any(adjacency[u][z] for u in selected)
        ]
        gamma_classes = frozenset(vertex_class[z] for z in gamma)
        assert set(selected) <= set(left)
        assert gamma_classes == EXPECTED_GAMMA[root_class]
        assert len(gamma) < len(selected)
        class_certificates.append(
            {
                "root_class": root_class,
                "S_classes": sorted(selected_classes),
                "S_weight": len(selected),
                "Gamma_classes": sorted(gamma_classes),
                "Gamma_weight": len(gamma),
            }
        )

    result = {
        "verified": True,
        "order": n,
        "arc_count": sum(sum(row) for row in adjacency),
        "minimum_outdegree": min(entry["outdegree"] for entry in vertices),
        "strong_vertices": [],
        "matrix_sha256": digest,
        "networkx_version": None if nx is None else nx.__version__,
        "dp_networkx_agreement": None if nx is None else True,
        "vertices": vertices,
        "class_certificates": class_certificates,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
