#!/usr/bin/env python3
"""Independently verify the first extremal witness emitted by the enumerator."""

import argparse
import gzip
import itertools
import json
from pathlib import Path

N = 13
SIDE = 6


def decode_upper_triangle(bits):
    if len(bits) != N * (N - 1) // 2 or set(bits) - {"0", "1"}:
        raise ValueError("invalid upper-triangle encoding")
    matrix = [[0] * N for _ in range(N)]
    pos = 0
    for i in range(N):
        for j in range(i + 1, N):
            if bits[pos] == "1":
                matrix[i][j] = 1
            else:
                matrix[j][i] = 1
            pos += 1
    return matrix


def maximum_matching_by_exhaustive_injections(rows):
    """Try every partial injection, without augmenting paths or Hall's theorem."""
    for size in range(SIDE, -1, -1):
        for left_vertices in itertools.combinations(range(SIDE), size):
            for right_vertices in itertools.permutations(range(SIDE), size):
                if all(rows[u] & (1 << v)
                       for u, v in zip(left_vertices, right_vertices)):
                    return size
    raise AssertionError("empty matching was not found")


def first_hall_defect(rows):
    for subset in range(1, 1 << SIDE):
        neighbors = 0
        for u in range(SIDE):
            if subset & (1 << u):
                neighbors |= rows[u]
        if neighbors.bit_count() < subset.bit_count():
            return subset, neighbors
    return None


def check_vertex(matrix, root):
    left = [v for v in range(N) if matrix[root][v]]
    right = [v for v in range(N) if v != root and not matrix[root][v]]
    if len(left) != SIDE or len(right) != SIDE:
        raise AssertionError("the witness is not regular")
    rows = []
    for u in left:
        mask = 0
        for j, v in enumerate(right):
            if matrix[u][v]:
                mask |= 1 << j
        rows.append(mask)
    matching_size = maximum_matching_by_exhaustive_injections(rows)
    defect = first_hall_defect(rows)
    return left, right, matching_size, defect


def read_catalog_record(path, one_based_index):
    with gzip.open(path, "rt", encoding="ascii", newline="") as stream:
        for index, line in enumerate(stream, 1):
            if index == one_based_index:
                return line.strip()
    raise AssertionError("catalog ended before the requested witness")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results_json", type=Path)
    parser.add_argument("--catalog-gz", type=Path)
    args = parser.parse_args()

    results = json.loads(args.results_json.read_text(encoding="utf-8"))
    witness = results["first_minimum_witness"]
    bits = witness["upper_triangle"]
    matrix = decode_upper_triangle(bits)

    published_matrix = [[int(bit) for bit in row]
                        for row in witness["adjacency_matrix"]]
    if matrix != published_matrix:
        raise AssertionError("upper triangle and adjacency matrix disagree")

    for i in range(N):
        if matrix[i][i] != 0 or sum(matrix[i]) != SIDE:
            raise AssertionError("invalid diagonal or out-degree")
        for j in range(i + 1, N):
            if matrix[i][j] + matrix[j][i] != 1:
                raise AssertionError("not a tournament")

    matching_sizes = []
    defects = {}
    for root in range(N):
        left, right, matching_size, defect = check_vertex(matrix, root)
        matching_sizes.append(matching_size)
        if defect is not None:
            subset, neighbors = defect
            defects[root] = {
                "S": [left[i] for i in range(SIDE) if subset & (1 << i)],
                "GammaS": [
                    right[i] for i in range(SIDE) if neighbors & (1 << i)
                ],
            }

    if matching_sizes != witness["matching_sizes"]:
        raise AssertionError("matching-size vector mismatch")
    non_strong = [v for v, size in enumerate(matching_sizes) if size < SIDE]
    if non_strong != witness["non_strong_vertices"]:
        raise AssertionError("non-strong vertex set mismatch")

    for published in witness["hall_defects"]:
        root = published["vertex"]
        if defects.get(root) != {
            "S": published["S"],
            "GammaS": published["GammaS"],
        }:
            raise AssertionError("Hall-defect mismatch")

    if args.catalog_gz is not None:
        catalog_bits = read_catalog_record(
            args.catalog_gz, witness["catalog_index_1_based"])
        if catalog_bits != bits:
            raise AssertionError("catalog witness does not match results")

    print(json.dumps({
        "status": "VERIFIED",
        "method": "exhaustive partial injections plus exhaustive Hall subsets",
        "catalog_record_checked": args.catalog_gz is not None,
        "matching_sizes": matching_sizes,
        "non_strong_vertices": non_strong,
        "hall_defects": defects,
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
