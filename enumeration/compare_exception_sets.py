#!/usr/bin/env python3
"""Compare two exceptional-tournament sets after canonical nauty labelling."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

N = 13


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


def encode_digraph6(matrix):
    if len(matrix) != N or any(len(row) != N for row in matrix):
        raise ValueError("unexpected adjacency-matrix dimensions")
    bits = "".join(str(bit) for row in matrix for bit in row)
    bits += "0" * ((-len(bits)) % 6)
    payload = "".join(
        chr(int(bits[position:position + 6], 2) + 63)
        for position in range(0, len(bits), 6)
    )
    return "&" + chr(N + 63) + payload


def load_records(path):
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(records) != 61:
        raise AssertionError(f"{path} has {len(records)} records, expected 61")
    return records


def canonical_labels(labelg, records):
    encoded = [
        encode_digraph6(decode_upper_triangle(record["upper_triangle"]))
        for record in records
    ]
    process = subprocess.run(
        [str(labelg), "-q", "-z"],
        input=("\n".join(encoded) + "\n").encode("ascii"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    labels = process.stdout.decode("ascii").splitlines()
    if len(labels) != len(records):
        raise AssertionError("labelg output record count mismatch")
    if len(set(labels)) != len(labels):
        raise AssertionError("an input exceptional set contains isomorphic duplicates")
    return labels


def labelled_strong_counts(labels, records):
    return {
        label: record["strong_count"]
        for label, record in zip(labels, records)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog_exceptions", type=Path)
    parser.add_argument("generated_exceptions", type=Path)
    parser.add_argument("--labelg", type=Path, required=True)
    args = parser.parse_args()

    catalog_records = load_records(args.catalog_exceptions)
    generated_records = load_records(args.generated_exceptions)
    catalog_labels = canonical_labels(args.labelg, catalog_records)
    generated_labels = canonical_labels(args.labelg, generated_records)

    catalog_map = labelled_strong_counts(catalog_labels, catalog_records)
    generated_map = labelled_strong_counts(generated_labels, generated_records)
    if catalog_map != generated_map:
        missing = sorted(set(catalog_map) - set(generated_map))
        extra = sorted(set(generated_map) - set(catalog_map))
        changed = sorted(
            label for label in set(catalog_map) & set(generated_map)
            if catalog_map[label] != generated_map[label]
        )
        raise AssertionError(
            "canonical exceptional sets differ: "
            f"missing={len(missing)} extra={len(extra)} "
            f"changed_counts={len(changed)}"
        )

    canonical_bytes = (
        "\n".join(
            f"{label} {catalog_map[label]}"
            for label in sorted(catalog_map)
        ) + "\n"
    ).encode("ascii")
    distribution = {}
    for strong_count in catalog_map.values():
        distribution[str(strong_count)] = (
            distribution.get(str(strong_count), 0) + 1
        )

    print(json.dumps({
        "status": "VERIFIED",
        "method": "nauty labelg canonical digraph6 comparison",
        "catalog_exceptional_class_count": len(catalog_map),
        "gentourng_exceptional_class_count": len(generated_map),
        "canonical_exception_sets_equal": True,
        "strong_counts_equal_class_by_class": True,
        "strong_count_distribution": dict(sorted(distribution.items())),
        "canonical_set_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
