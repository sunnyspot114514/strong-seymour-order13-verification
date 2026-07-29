#!/usr/bin/env python3
"""Partition one root-cover branch by a complete cross-block row."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--axis",
        choices=("out-row", "in-row"),
        default="out-row",
        help=(
            "out-row fixes the first uncovered out-neighbour against every "
            "covered in-neighbour; in-row fixes the converse full row"
        ),
    )
    args = parser.parse_args()

    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    order = int(metadata["order"])
    degree = int(metadata["root_degree"])
    cover_left = int(metadata["root_cover_left"])
    cover_right = int(metadata["root_cover_right"])
    uncovered_out = list(range(cover_left + 1, degree + 1))
    covered_in = list(
        range(degree + 1, degree + 1 + cover_right)
    )
    if not uncovered_out:
        raise ValueError("the uncovered out-neighbour block is empty")
    if not covered_in:
        raise ValueError("the covered in-neighbour block is empty")

    # The canonical root-cover labelling used by generate_tournament_cnf.py:
    #
    #   block 0 = covered out-neighbours       1 .. cover_left
    #   block 1 = uncovered out-neighbours     cover_left+1 .. degree
    #   block 2 = covered in-neighbours        degree+1 .. degree+cover_right
    #   block 3 = uncovered in-neighbours      the remaining vertices
    #
    # Fixing every orientation in either selected cross-block row gives an
    # exact fixed-variable case partition.
    if args.axis == "out-row":
        source = uncovered_out[0]
        targets = covered_in
    else:
        source = covered_in[0]
        targets = uncovered_out
    orientation = metadata["orientation_variables"]
    variables = [
        int(orientation[f"{min(source, target)},{max(source, target)}"])
        for target in targets
    ]
    if not (0 < source < order):
        raise AssertionError("invalid source vertex")
    if len(set(variables)) != len(variables):
        raise AssertionError("duplicate split variable")

    with args.output.open("w", encoding="ascii", newline="\n") as handle:
        for signs in itertools.product((False, True), repeat=len(variables)):
            literals = [
                variable if positive else -variable
                for variable, positive in zip(variables, signs)
            ]
            handle.write("a " + " ".join(map(str, literals)) + " 0\n")

    print(
        json.dumps(
            {
                "source": source,
                "targets": targets,
                "variables": variables,
                "cubes": 1 << len(variables),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
