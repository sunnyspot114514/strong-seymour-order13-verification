#!/usr/bin/env python3
"""Independently verify every certificate in EXCEPTIONAL_CLASSES.jsonl."""

import argparse
import collections
import gzip
import hashlib
import itertools
import json
from pathlib import Path

N = 13
SIDE = 6


def decode_upper_triangle(bits):
    if len(bits) != N * (N - 1) // 2 or set(bits) - {"0", "1"}:
        raise ValueError("invalid upper-triangle encoding")
    matrix = [[0] * N for _ in range(N)]
    position = 0
    for i in range(N):
        for j in range(i + 1, N):
            matrix[i][j] = int(bits[position])
            matrix[j][i] = 1 - matrix[i][j]
            position += 1
    return matrix


def bipartite_rows(matrix, root):
    left = [vertex for vertex in range(N) if matrix[root][vertex]]
    right = [
        vertex for vertex in range(N)
        if vertex != root and not matrix[root][vertex]
    ]
    if len(left) != SIDE or len(right) != SIDE:
        raise AssertionError("record is not a regular tournament")
    rows = []
    for source in left:
        mask = 0
        for position, target in enumerate(right):
            if matrix[source][target]:
                mask |= 1 << position
        rows.append(mask)
    return left, right, rows


def maximum_matching_by_exhaustive_injections(rows):
    for size in range(SIDE, -1, -1):
        for left_vertices in itertools.combinations(range(SIDE), size):
            for right_vertices in itertools.permutations(range(SIDE), size):
                if all(
                    rows[source] & (1 << target)
                    for source, target in zip(left_vertices, right_vertices)
                ):
                    return size
    raise AssertionError("empty matching was not found")


def first_hall_defect(left, right, rows):
    for subset in range(1, 1 << SIDE):
        neighbors = 0
        for source in range(SIDE):
            if subset & (1 << source):
                neighbors |= rows[source]
        if neighbors.bit_count() < subset.bit_count():
            return {
                "S": [
                    left[position] for position in range(SIDE)
                    if subset & (1 << position)
                ],
                "GammaS": [
                    right[position] for position in range(SIDE)
                    if neighbors & (1 << position)
                ],
            }
    return None


def verify_perfect_matching(matrix, root, certificate):
    edges = certificate["edges"]
    if len(edges) != SIDE:
        raise AssertionError("perfect matching does not contain six edges")
    left = {vertex for vertex in range(N) if matrix[root][vertex]}
    right = {
        vertex for vertex in range(N)
        if vertex != root and not matrix[root][vertex]
    }
    sources = [edge[0] for edge in edges]
    targets = [edge[1] for edge in edges]
    if set(sources) != left or len(set(sources)) != SIDE:
        raise AssertionError("perfect matching does not cover N+(x)")
    if set(targets) != right or len(set(targets)) != SIDE:
        raise AssertionError("perfect matching does not cover N-(x)")
    if any(not matrix[source][target] for source, target in edges):
        raise AssertionError("perfect matching contains a missing arc")


def read_catalog_records(path, wanted_indices):
    found = {}
    with gzip.open(path, "rt", encoding="ascii", newline="") as stream:
        for index, line in enumerate(stream, 1):
            if index in wanted_indices:
                found[index] = line.strip()
    if set(found) != wanted_indices:
        raise AssertionError("catalogue ended before all exceptional records")
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("exceptions_jsonl", type=Path)
    parser.add_argument("--catalog-gz", type=Path)
    args = parser.parse_args()

    raw = args.exceptions_jsonl.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    records = [json.loads(line) for line in lines if line]
    if len(records) != 61:
        raise AssertionError(f"expected 61 exceptional records, got {len(records)}")

    indices = [record["catalog_index_1_based"] for record in records]
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise AssertionError("catalogue indices are not unique and increasing")

    encodings = [record["upper_triangle"] for record in records]
    if len(set(encodings)) != len(encodings):
        raise AssertionError("duplicate exceptional encodings")

    catalog_records = None
    if args.catalog_gz is not None:
        catalog_records = read_catalog_records(args.catalog_gz, set(indices))

    distribution = collections.Counter()
    perfect_matching_certificates = 0
    hall_defect_certificates = 0
    for record in records:
        index = record["catalog_index_1_based"]
        bits = record["upper_triangle"]
        if catalog_records is not None and catalog_records[index] != bits:
            raise AssertionError(f"catalogue encoding mismatch at record {index}")
        matrix = decode_upper_triangle(bits)
        for vertex in range(N):
            if matrix[vertex][vertex] or sum(matrix[vertex]) != SIDE:
                raise AssertionError("invalid diagonal or out-degree")

        matching_sizes = []
        defects = {}
        for root in range(N):
            left, right, rows = bipartite_rows(matrix, root)
            matching_sizes.append(maximum_matching_by_exhaustive_injections(rows))
            defect = first_hall_defect(left, right, rows)
            if defect is not None:
                defects[root] = defect

        if matching_sizes != record["matching_sizes"]:
            raise AssertionError(f"matching-size mismatch at record {index}")
        non_strong = [
            vertex for vertex, size in enumerate(matching_sizes)
            if size < SIDE
        ]
        if non_strong != record["non_strong_vertices"]:
            raise AssertionError(f"non-strong set mismatch at record {index}")
        strong_count = N - len(non_strong)
        if strong_count != record["strong_count"] or strong_count not in (11, 12):
            raise AssertionError(f"strong-count mismatch at record {index}")

        published_defects = {
            item["vertex"]: {"S": item["S"], "GammaS": item["GammaS"]}
            for item in record["hall_defects"]
        }
        if published_defects != defects:
            raise AssertionError(f"Hall-defect mismatch at record {index}")

        published_matchings = {
            item["vertex"]: item for item in record["perfect_matchings"]
        }
        expected_strong = set(range(N)) - set(non_strong)
        if set(published_matchings) != expected_strong:
            raise AssertionError(
                f"perfect-matching certificate set mismatch at record {index}"
            )
        for root, certificate in published_matchings.items():
            verify_perfect_matching(matrix, root, certificate)

        distribution[strong_count] += 1
        perfect_matching_certificates += len(published_matchings)
        hall_defect_certificates += len(published_defects)

    expected_distribution = {11: 13, 12: 48}
    if dict(sorted(distribution.items())) != expected_distribution:
        raise AssertionError("exceptional-class distribution mismatch")

    print(json.dumps({
        "status": "VERIFIED",
        "method": (
            "exhaustive partial injections, exhaustive Hall subsets, "
            "and direct perfect-matching certificate checks"
        ),
        "exceptional_jsonl_sha256": hashlib.sha256(raw).hexdigest(),
        "exceptional_class_count": len(records),
        "strong_count_distribution": {
            str(key): value for key, value in sorted(distribution.items())
        },
        "vertex_checks": len(records) * N,
        "perfect_matching_certificates": perfect_matching_certificates,
        "hall_defect_certificates": hall_defect_certificates,
        "catalog_records_checked": len(records) if catalog_records else 0,
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
