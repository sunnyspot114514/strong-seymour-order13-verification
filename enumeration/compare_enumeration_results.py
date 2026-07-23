#!/usr/bin/env python3
"""Compare the invariant summaries from catalogue and gentourng enumeration."""

import argparse
import hashlib
import json
from pathlib import Path

SUMMARY_FIELDS = (
    "catalog_records",
    "vertex_checks",
    "all_records_valid_6_regular_tournaments",
    "hall_and_augmenting_path_agree_everywhere",
    "minimum_strong_vertices",
    "maximum_non_strong_vertices",
    "minimum_isomorphism_class_count",
    "strong_count_distribution_unlabelled",
)


def load(path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog_results", type=Path)
    parser.add_argument("gentourng_results", type=Path)
    args = parser.parse_args()

    catalog, catalog_sha256 = load(args.catalog_results)
    generated, generated_sha256 = load(args.gentourng_results)

    differences = [
        field for field in SUMMARY_FIELDS
        if catalog.get(field) != generated.get(field)
    ]
    if differences:
        raise AssertionError(
            "enumeration summaries differ in: " + ", ".join(differences)
        )

    print(json.dumps({
        "status": "VERIFIED",
        "summary_fields_equal": True,
        "compared_fields": list(SUMMARY_FIELDS),
        "catalog_results_sha256": catalog_sha256,
        "gentourng_results_sha256": generated_sha256,
        "catalog_first_minimum_index": (
            catalog["first_minimum_witness"]["catalog_index_1_based"]
        ),
        "gentourng_first_minimum_index": (
            generated["first_minimum_witness"]["catalog_index_1_based"]
        ),
        "first_witness_encodings_differ": (
            catalog["first_minimum_witness"]["upper_triangle"]
            != generated["first_minimum_witness"]["upper_triangle"]
        ),
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
