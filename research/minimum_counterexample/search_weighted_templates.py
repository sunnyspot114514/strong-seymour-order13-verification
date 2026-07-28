#!/usr/bin/env python3
"""Search nearby tournament templates for smaller transitive blow-ups.

For the last vertex of a transitive cluster i, a nonempty set J of
out-neighbour clusters is a Hall witness exactly when

    sum(w[j] for j in J) > sum(w[z] for z in Gamma_i(J)).

The script enumerates template edge flips and uses an integer program to
choose positive cluster weights and one such witness for every root class.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


def order_from_code(code: str) -> int:
    length = len(code)
    order = (1 + math.isqrt(1 + 8 * length)) // 2
    if order * (order - 1) // 2 != length or set(code) - {"0", "1"}:
        raise ValueError("code length is not triangular or code is not binary")
    return order


def decode(code: str) -> list[list[bool]]:
    order = order_from_code(code)
    adjacency = [[False] * order for _ in range(order)]
    index = 0
    for u in range(order):
        for v in range(u + 1, order):
            adjacency[u][v] = code[index] == "1"
            adjacency[v][u] = not adjacency[u][v]
            index += 1
    return adjacency


def flip_code(code: str, flips: tuple[int, ...]) -> str:
    bits = list(code)
    for index in flips:
        bits[index] = "0" if bits[index] == "1" else "1"
    return "".join(bits)


def hall_options(adjacency: list[list[bool]], root: int) -> list[tuple[int, ...]]:
    order = len(adjacency)
    out = [vertex for vertex in range(order) if adjacency[root][vertex]]
    options: set[tuple[int, ...]] = set()
    for mask in range(1, 1 << len(out)):
        selected = {
            out[index] for index in range(len(out)) if mask & (1 << index)
        }
        gamma = {
            target
            for target in range(order)
            if adjacency[target][root]
            and any(adjacency[source][target] for source in selected)
        }
        coefficient = tuple(
            (1 if vertex in selected else 0)
            - (1 if vertex in gamma else 0)
            for vertex in range(order)
        )
        options.add(coefficient)

    # If b >= a componentwise, b is at least as easy to satisfy for every
    # positive weight vector, so a can be discarded from the disjunction.
    pareto = []
    for option in sorted(options):
        if any(
            other != option
            and all(b >= a for a, b in zip(option, other))
            for other in options
        ):
            continue
        pareto.append(option)
    return pareto


def matching_size(rows: list[int]) -> int:
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


def verify_blowup(
    template: list[list[bool]], weights: list[int]
) -> dict[str, object]:
    offsets = [0]
    for weight in weights:
        offsets.append(offsets[-1] + weight)
    classes = [
        cluster
        for cluster, weight in enumerate(weights)
        for _ in range(weight)
    ]
    order = len(classes)
    adjacency = [[False] * order for _ in range(order)]
    for u in range(order):
        for v in range(u + 1, order):
            if classes[u] == classes[v]:
                adjacency[u][v] = True
            elif template[classes[u]][classes[v]]:
                adjacency[u][v] = True
            else:
                adjacency[v][u] = True
    strong = []
    for root in range(order):
        left = [vertex for vertex in range(order) if adjacency[root][vertex]]
        right = [
            vertex
            for vertex in range(order)
            if vertex != root
            and adjacency[vertex][root]
            and any(adjacency[source][vertex] for source in left)
        ]
        rows = [
            sum(
                1 << index
                for index, target in enumerate(right)
                if adjacency[source][target]
            )
            for source in left
        ]
        if matching_size(rows) == len(left):
            strong.append(root)
    matrix = (
        "\n".join(
            "".join("1" if adjacency[u][v] else "0" for v in range(order))
            for u in range(order)
        )
        + "\n"
    )
    return {
        "verified_no_strong_vertices": not strong,
        "strong_vertices": strong,
        "matrix_sha256": hashlib.sha256(matrix.encode("ascii")).hexdigest(),
        "adjacency_matrix": matrix.splitlines(),
    }


def solve(adjacency: list[list[bool]], cap: int) -> dict | None:
    order = len(adjacency)
    options = [hall_options(adjacency, root) for root in range(order)]
    offsets = [order]
    for root_options in options:
        offsets.append(offsets[-1] + len(root_options))
    variable_count = offsets[-1]

    objective = np.zeros(variable_count)
    objective[:order] = 1
    lower = np.zeros(variable_count)
    upper = np.ones(variable_count)
    lower[:order] = 1
    upper[:order] = cap

    row_indices: list[int] = []
    column_indices: list[int] = []
    values: list[float] = []
    row_lower: list[float] = []
    row_upper: list[float] = []

    def add_row(entries: dict[int, float], lo: float, hi: float) -> None:
        row = len(row_lower)
        for column, value in entries.items():
            row_indices.append(row)
            column_indices.append(column)
            values.append(value)
        row_lower.append(lo)
        row_upper.append(hi)

    add_row({index: 1 for index in range(order)}, -np.inf, cap)
    big_m = cap + 1
    for root, root_options in enumerate(options):
        add_row(
            {
                offsets[root] + index: 1
                for index in range(len(root_options))
            },
            1,
            1,
        )
        for index, coefficient in enumerate(root_options):
            entries = {
                vertex: -value
                for vertex, value in enumerate(coefficient)
                if value
            }
            entries[offsets[root] + index] = big_m
            add_row(entries, -np.inf, big_m - 1)

    matrix = coo_matrix(
        (values, (row_indices, column_indices)),
        shape=(len(row_lower), variable_count),
    ).tocsr()
    result = milp(
        objective,
        integrality=np.ones(variable_count),
        bounds=Bounds(lower, upper),
        constraints=LinearConstraint(matrix, row_lower, row_upper),
        options={"presolve": True},
    )
    if not result.success or result.x is None:
        return None
    weights = [int(round(value)) for value in result.x[:order]]
    witnesses = []
    for root, root_options in enumerate(options):
        selected = max(
            range(len(root_options)),
            key=lambda index: result.x[offsets[root] + index],
        )
        coefficient = root_options[selected]
        defect = sum(a * w for a, w in zip(coefficient, weights))
        if defect < 1:
            raise RuntimeError("MILP returned an invalid Hall witness")
        witnesses.append(
            {"root": root, "coefficient": coefficient, "defect": defect}
        )
    verification = verify_blowup(adjacency, weights)
    if not verification["verified_no_strong_vertices"]:
        raise RuntimeError("weighted Hall solution failed direct matching check")
    return {
        "total": sum(weights),
        "weights": weights,
        "pareto_option_counts": [len(root_options) for root_options in options],
        "witnesses": witnesses,
        "direct_verification": verification,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--code")
    source.add_argument(
        "--verification-json",
        type=Path,
        help="JSON file containing a template_code field",
    )
    parser.add_argument("--cap", type=int, default=23)
    parser.add_argument("--flip-distance", type=int, default=0)
    parser.add_argument(
        "--random-template-count",
        type=int,
        help="search this many deterministic random templates instead",
    )
    parser.add_argument("--random-template-seed", type=int, default=1)
    parser.add_argument("--max-templates", type=int)
    parser.add_argument(
        "--skip-templates",
        type=int,
        default=0,
        help="skip this many templates assigned to the selected worker",
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--worker-index", type=int, default=0)
    parser.add_argument(
        "--shuffle-seed",
        type=int,
        help="deterministically shuffle the template order before splitting",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.verification_json:
        data = json.loads(args.verification_json.read_text(encoding="utf-8"))
        code = data["template_code"]
    else:
        code = args.code
    assert code is not None
    if not 1 <= args.workers or not 0 <= args.worker_index < args.workers:
        parser.error("require 0 <= --worker-index < --workers")
    edge_count = len(code)
    records = []
    tested = 0
    assigned = 0
    if args.random_template_count is not None:
        generator = random.Random(args.random_template_seed)
        random_codes: set[str] = set()
        while len(random_codes) < args.random_template_count:
            random_codes.add(
                "".join(generator.choice("01") for _ in range(edge_count))
            )
        candidates: list[tuple[tuple[int, ...] | None, str]] = [
            (None, candidate_code) for candidate_code in sorted(random_codes)
        ]
        search_mode = "random_templates"
    else:
        combinations = list(
            itertools.combinations(range(edge_count), args.flip_distance)
        )
        if args.shuffle_seed is not None:
            random.Random(args.shuffle_seed).shuffle(combinations)
        candidates = [
            (flips, flip_code(code, flips)) for flips in combinations
        ]
        search_mode = "edge_flip_distance"
    for candidate_index, (flips, candidate_code) in enumerate(candidates):
        if candidate_index % args.workers != args.worker_index:
            continue
        if assigned < args.skip_templates:
            assigned += 1
            continue
        assigned += 1
        if args.max_templates is not None and tested >= args.max_templates:
            break
        tested += 1
        solution = solve(decode(candidate_code), args.cap)
        if solution is None:
            continue
        record = {
            "template_code": candidate_code,
            **solution,
        }
        if flips is not None:
            record["flipped_code_indices"] = flips
        records.append(record)
        print(json.dumps(record), flush=True)

    result = {
        "base_template_code": code,
        "order": order_from_code(code),
        "cap": args.cap,
        "search_mode": search_mode,
        "flip_distance": args.flip_distance,
        "random_template_count": args.random_template_count,
        "random_template_seed": args.random_template_seed,
        "workers": args.workers,
        "worker_index": args.worker_index,
        "tested_templates": tested,
        "feasible_templates": len(records),
        "solutions": records,
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "order",
                    "cap",
                    "flip_distance",
                    "tested_templates",
                    "feasible_templates",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
