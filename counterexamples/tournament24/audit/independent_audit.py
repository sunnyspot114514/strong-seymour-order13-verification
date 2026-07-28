#!/usr/bin/env python3
"""Independent audit of the 24-vertex tournament counterexample package.

This parser/reconstructor intentionally does not import either bundled verifier.
Maximum matchings are computed by a finite-state dynamic program, not by an
augmenting-path implementation.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

try:
    import networkx as nx
except ImportError:
    nx = None


PACKAGE = Path(__file__).resolve().parents[1]
MATRIX_PATH = PACKAGE / "data" / "adjacency_matrix.txt"
FULL_RESULTS_PATH = PACKAGE / "data" / "full_verification.json"

TEMPLATE_OUT = (
    frozenset((1, 2, 7, 9)),
    frozenset((3, 4, 5, 7)),
    frozenset((1, 5, 7, 8, 9)),
    frozenset((0, 2, 4, 6, 8)),
    frozenset((0, 2, 6, 8)),
    frozenset((0, 3, 4, 8)),
    frozenset((0, 1, 2, 5, 8)),
    frozenset((3, 4, 5, 6, 9)),
    frozenset((0, 1, 7)),
    frozenset((1, 3, 4, 5, 6, 8)),
)
WEIGHTS = (5, 1, 2, 2, 3, 1, 2, 5, 1, 2)
CLASS_DEFECTS = (
    frozenset((1, 2, 7, 9)),
    frozenset((7,)),
    frozenset((1, 7, 9)),
    frozenset((4,)),
    frozenset((0, 2, 6, 8)),
    frozenset((3, 4)),
    frozenset((0, 2, 8)),
    frozenset((3, 4, 5, 6, 9)),
    frozenset((0,)),
    frozenset((3, 4, 5, 6)),
)
EXPECTED_MATRIX_SHA256 = (
    "d3b70f40dd3cc33f66ba23dcbb99138580d6cd6d6684e3658028606d680d23ed"
)


def validate_template() -> None:
    assert len(TEMPLATE_OUT) == len(WEIGHTS) == 10
    for u in range(10):
        assert u not in TEMPLATE_OUT[u]
        for v in range(u + 1, 10):
            assert (v in TEMPLATE_OUT[u]) ^ (u in TEMPLATE_OUT[v])


def construct_expanded_tournament() -> tuple[list[list[bool]], list[int], list[int]]:
    offsets = [0]
    for weight in WEIGHTS:
        offsets.append(offsets[-1] + weight)
    classes = [
        class_index
        for class_index, weight in enumerate(WEIGHTS)
        for _ in range(weight)
    ]
    n = offsets[-1]
    adjacency = [[False] * n for _ in range(n)]
    for u in range(n):
        for v in range(n):
            if classes[u] == classes[v]:
                adjacency[u][v] = u < v
            else:
                adjacency[u][v] = classes[v] in TEMPLATE_OUT[classes[u]]
    return adjacency, offsets, classes


def validate_tournament(adjacency: list[list[bool]]) -> None:
    n = len(adjacency)
    assert all(len(row) == n for row in adjacency)
    assert all(not adjacency[u][u] for u in range(n))
    for u in range(n):
        for v in range(u + 1, n):
            assert adjacency[u][v] ^ adjacency[v][u]


def matrix_bytes(adjacency: list[list[bool]]) -> bytes:
    return (
        "\n".join(
            "".join("1" if adjacency[u][v] else "0" for v in range(len(adjacency)))
            for u in range(len(adjacency))
        )
        + "\n"
    ).encode("ascii")


def strict_second_neighborhood(
    adjacency: list[list[bool]], root: int
) -> tuple[list[int], list[int]]:
    n = len(adjacency)
    first = [v for v in range(n) if adjacency[root][v]]
    first_set = set(first)
    second = [
        z
        for z in range(n)
        if z != root
        and z not in first_set
        and any(adjacency[y][z] for y in first)
    ]
    return first, second


def bipartite_rows(
    adjacency: list[list[bool]], left: list[int], right: list[int]
) -> list[int]:
    return [
        sum(1 << j for j, v in enumerate(right) if adjacency[u][v])
        for u in left
    ]


def matching_size_by_state_dp(rows: list[int]) -> int:
    """Return the exact matching number using reachable right-vertex masks."""
    reachable = {0}
    for row in rows:
        next_reachable = set(reachable)
        for used in reachable:
            available = row & ~used
            while available:
                bit = available & -available
                available -= bit
                next_reachable.add(used | bit)
        reachable = next_reachable
    return max(mask.bit_count() for mask in reachable)


def matching_size_by_networkx(
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


def smallest_hall_defect(
    left: list[int], right: list[int], rows: list[int]
) -> tuple[list[int], list[int]]:
    for size in range(1, len(left) + 1):
        for indices in itertools.combinations(range(len(left)), size):
            gamma_mask = 0
            for index in indices:
                gamma_mask |= rows[index]
            if gamma_mask.bit_count() < size:
                return (
                    [left[index] for index in indices],
                    [
                        right[index]
                        for index in range(len(right))
                        if gamma_mask & (1 << index)
                    ],
                )
    raise AssertionError("No Hall defect exists")


def normalized_published_vertex(entry: dict, labels: list[str]) -> dict:
    if isinstance(entry["vertex"], str):
        vertex = labels.index(entry["vertex"])
        hall_s = [labels.index(label) for label in entry["hall_S"]]
        hall_gamma = [labels.index(label) for label in entry["hall_Gamma"]]
    else:
        vertex = entry["vertex"]
        hall_s = entry["hall_S"]
        hall_gamma = entry["hall_Gamma"]
    return {
        "vertex": vertex,
        "outdegree": entry["outdegree"],
        "strict_second": entry["strict_second"],
        "matching": entry["matching"],
        "hall_S": hall_s,
        "hall_Gamma": hall_gamma,
    }


def validate_published_certificate(
    entry: dict,
    adjacency: list[list[bool]],
    left: list[int],
    right: list[int],
    matching: int,
) -> None:
    assert entry["outdegree"] == len(left)
    assert entry["strict_second"] == len(right)
    assert entry["matching"] == matching
    hall_s = entry["hall_S"]
    hall_gamma = entry["hall_Gamma"]
    assert hall_s and set(hall_s) <= set(left)
    actual_gamma = sorted(
        v for v in right if any(adjacency[u][v] for u in hall_s)
    )
    assert actual_gamma == sorted(hall_gamma)
    assert len(actual_gamma) < len(hall_s)


def validate_structural_certificates(
    adjacency: list[list[bool]], offsets: list[int]
) -> list[dict]:
    summary = []
    for root_class, defect_classes in enumerate(CLASS_DEFECTS):
        assert defect_classes <= TEMPLATE_OUT[root_class]
        strict_second_classes = {
            z
            for z in range(10)
            if z != root_class
            and z not in TEMPLATE_OUT[root_class]
            and any(z in TEMPLATE_OUT[y] for y in TEMPLATE_OUT[root_class])
        }
        gamma_classes = {
            z
            for z in strict_second_classes
            if any(z in TEMPLATE_OUT[y] for y in defect_classes)
        }
        left_weight = sum(WEIGHTS[y] for y in defect_classes)
        gamma_weight = sum(WEIGHTS[z] for z in gamma_classes)
        assert left_weight > gamma_weight

        last_vertex = offsets[root_class + 1] - 1
        expanded_s = [
            u
            for class_index in defect_classes
            for u in range(offsets[class_index], offsets[class_index + 1])
        ]
        first, second = strict_second_neighborhood(adjacency, last_vertex)
        actual_gamma = [
            z for z in second if any(adjacency[u][z] for u in expanded_s)
        ]
        assert set(expanded_s) <= set(first)
        assert len(actual_gamma) == gamma_weight < len(expanded_s) == left_weight

        for x in range(offsets[root_class], last_vertex):
            successor = x + 1
            first, second = strict_second_neighborhood(adjacency, x)
            assert successor in first
            assert not any(adjacency[successor][z] for z in second)

        summary.append(
            {
                "root_class": root_class,
                "J": sorted(defect_classes),
                "weight_J": left_weight,
                "Gamma": sorted(gamma_classes),
                "weight_Gamma": gamma_weight,
            }
        )
    return summary


def main() -> None:
    validate_template()
    adjacency, offsets, classes = construct_expanded_tournament()
    validate_tournament(adjacency)
    assert len(adjacency) == sum(WEIGHTS) == 24

    generated_matrix = matrix_bytes(adjacency)
    published_matrix = MATRIX_PATH.read_bytes()
    matrix_sha256 = hashlib.sha256(generated_matrix).hexdigest()
    assert generated_matrix == published_matrix
    assert matrix_sha256 == EXPECTED_MATRIX_SHA256

    labels = [
        f"V{class_index}_{position}"
        for class_index, weight in enumerate(WEIGHTS)
        for position in range(weight)
    ]
    published = json.loads(FULL_RESULTS_PATH.read_text(encoding="utf-8"))
    assert published.get("n", published.get("order")) == 24
    assert tuple(published["weights"]) == WEIGHTS
    assert published["matrix_sha256"] == EXPECTED_MATRIX_SHA256
    if "rows" in published:
        assert published["rows"] == generated_matrix.decode("ascii").splitlines()
    published_entries = {
        normalized["vertex"]: normalized
        for raw in published["vertices"]
        for normalized in (normalized_published_vertex(raw, labels),)
    }
    assert set(published_entries) == set(range(24))

    vertices = []
    for root in range(24):
        left, right = strict_second_neighborhood(adjacency, root)
        rows = bipartite_rows(adjacency, left, right)
        matching = matching_size_by_state_dp(rows)
        if nx is not None:
            networkx_matching = matching_size_by_networkx(adjacency, left, right)
            assert networkx_matching == matching
        hall_s, hall_gamma = smallest_hall_defect(left, right, rows)
        assert matching < len(left)
        assert len(hall_gamma) < len(hall_s)
        validate_published_certificate(
            published_entries[root], adjacency, left, right, matching
        )
        vertices.append(
            {
                "vertex": root,
                "class": classes[root],
                "outdegree": len(left),
                "strict_second": len(right),
                "matching": matching,
                "matching_deficit": len(left) - matching,
                "smallest_hall_S": hall_s,
                "smallest_hall_Gamma": hall_gamma,
            }
        )

    structural = validate_structural_certificates(adjacency, offsets)
    output = {
        "verified": True,
        "order": 24,
        "is_tournament": True,
        "matrix_matches_published_bytes": True,
        "matrix_sha256": matrix_sha256,
        "strong_vertices": [],
        "published_vertex_certificates_checked": 24,
        "matching_method": "reachable-right-mask dynamic programming",
        "networkx_version": None if nx is None else nx.__version__,
        "networkx_matching_agreement": None if nx is None else True,
        "vertices": vertices,
        "structural_class_certificates": structural,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
