#!/usr/bin/env python3
"""Solve every cube of an exhaustive CNF partition in parallel."""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import re
import shutil
import subprocess
import time
from pathlib import Path


HEADER = re.compile(r"^p cnf ([1-9][0-9]*) ([0-9]+)$", re.MULTILINE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument("cubes", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("solver", type=Path)
    parser.add_argument("--seconds", type=int, default=10)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument(
        "--solver-kind",
        choices=(
            "kissat",
            "kissat-competition",
            "cadical",
            "gimsatul",
        ),
        default="kissat",
    )
    parser.add_argument(
        "--solver-threads",
        type=int,
        default=4,
        help="worker threads for a gimsatul process",
    )
    parser.add_argument("--keep-cnf", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="reuse terminal SAT/UNSAT outputs already present in work",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="permit a non-exhaustive subset for follow-up solving",
    )
    parser.add_argument(
        "--parents",
        type=Path,
        help="verify that adaptive child cubes exhaust these parent cubes",
    )
    args = parser.parse_args()

    header_match = None
    with args.cnf.open("r", encoding="ascii") as source:
        for line in source:
            candidate = HEADER.fullmatch(line.strip())
            if candidate is not None:
                if header_match is not None:
                    raise ValueError("CNF has multiple headers")
                header_match = candidate
    if header_match is None:
        raise ValueError("CNF has no valid header")
    variables, clauses = map(int, header_match.groups())
    cube_list = [
        [int(token) for token in line.split()[1:-1]]
        for line in args.cubes.read_text(encoding="ascii").splitlines()
        if line.startswith("a ")
    ]
    if not cube_list:
        raise ValueError("cube file has no a-lines")
    if any(
        not cube or any(abs(literal) > variables for literal in cube)
        for cube in cube_list
    ):
        raise ValueError("invalid cube literal")
    depth = len(cube_list[0])
    if any(len(cube) != depth for cube in cube_list):
        raise ValueError("all cubes must have one common depth")
    split_variables: list[int] | None = None
    exhaustive_fixed = False
    exhaustive_parent_refinement = False
    if args.parents is None:
        split_variables = [abs(literal) for literal in cube_list[0]]
        repeated = len(set(split_variables)) != depth
        consistent = all(
            [abs(literal) for literal in cube] == split_variables
            for cube in cube_list
        )
        if repeated and not args.allow_partial:
            raise ValueError("a cube repeats a split variable")
        if not consistent and not args.allow_partial:
            raise ValueError("cube list is not a fixed-variable partition")
        if (
            not repeated
            and consistent
            and len(cube_list) == 1 << depth
        ):
            observed_signs = {
                tuple(literal > 0 for literal in cube) for cube in cube_list
            }
            expected_signs = set(
                itertools.product((False, True), repeat=depth)
            )
            exhaustive_fixed = observed_signs == expected_signs
    else:
        parent_list = [
            [int(token) for token in line.split()[1:-1]]
            for line in args.parents.read_text(
                encoding="ascii"
            ).splitlines()
            if line.startswith("a ")
        ]
        if not parent_list:
            raise ValueError("parent cube file has no a-lines")
        parent_depth = len(parent_list[0])
        if any(len(parent) != parent_depth for parent in parent_list):
            raise ValueError("parent cube depths differ")
        remaining = list(cube_list)
        for parent in parent_list:
            children = [
                cube for cube in remaining if cube[:parent_depth] == parent
            ]
            if not children:
                raise ValueError("a parent has no children")
            suffix_depth = len(children[0]) - parent_depth
            if suffix_depth < 1 or any(
                len(child) != parent_depth + suffix_depth
                for child in children
            ):
                raise ValueError("invalid child depth")
            suffix_variables = [
                abs(literal) for literal in children[0][parent_depth:]
            ]
            if len(set(map(abs, parent)) | set(suffix_variables)) != (
                parent_depth + suffix_depth
            ):
                raise ValueError("child repeats a parent/suffix variable")
            if any(
                [
                    abs(literal)
                    for literal in child[parent_depth:]
                ]
                != suffix_variables
                for child in children
            ):
                raise ValueError("one parent has inconsistent split variables")
            observed = {
                tuple(literal > 0 for literal in child[parent_depth:])
                for child in children
            }
            expected = set(
                itertools.product((False, True), repeat=suffix_depth)
            )
            if observed != expected:
                raise ValueError("children do not exhaust a parent")
            child_set = {tuple(child) for child in children}
            remaining = [
                cube for cube in remaining if tuple(cube) not in child_set
            ]
        if remaining:
            raise ValueError("a child has no matching parent")
        exhaustive_parent_refinement = True
    exhaustive = exhaustive_fixed or exhaustive_parent_refinement
    if not exhaustive and not args.allow_partial:
        raise ValueError("cubes do not form a verified exhaustive partition")

    args.work.mkdir(parents=True, exist_ok=True)
    template = args.work / "cube_template.cnf"
    with args.cnf.open("r", encoding="ascii") as source, template.open(
        "w", encoding="ascii", newline="\n"
    ) as target:
        replaced = False
        for line in source:
            if HEADER.fullmatch(line.strip()) is not None:
                target.write(
                    f"p cnf {variables} "
                    f"{clauses + len(cube_list[0])}\n"
                )
                replaced = True
            else:
                target.write(line)
        if not replaced:
            raise AssertionError("CNF header disappeared")

    def solve(item: tuple[int, list[int]]) -> dict[str, object]:
        index, cube = item
        cube_cnf = args.work / f"cube_{index:05d}.cnf"
        output = args.work / f"cube_{index:05d}.solver.out"
        if args.resume and output.exists():
            previous = output.read_text(
                encoding="ascii", errors="replace"
            )
            if "s SATISFIABLE" in previous:
                return {
                    "cube": index,
                    "literals": cube,
                    "result": "SAT",
                    "seconds": 0.0,
                    "exit_code": 10,
                    "stderr": "",
                    "resumed": True,
                }
            if "s UNSATISFIABLE" in previous:
                return {
                    "cube": index,
                    "literals": cube,
                    "result": "UNSAT",
                    "seconds": 0.0,
                    "exit_code": 20,
                    "stderr": "",
                    "resumed": True,
                }
        shutil.copyfile(template, cube_cnf)
        with cube_cnf.open("a", encoding="ascii", newline="\n") as target:
            for literal in cube:
                target.write(f"{literal} 0\n")
        started = time.perf_counter()
        solver_command = [
            "timeout",
            "-k",
            "5s",
            f"{args.seconds}s",
            str(args.solver),
        ]
        if args.solver_kind == "gimsatul":
            if args.solver_threads <= 0:
                raise ValueError("solver thread count must be positive")
            solver_command.extend(
                [
                    str(cube_cnf),
                    f"--threads={args.solver_threads}",
                ]
            )
        else:
            if args.solver_kind == "kissat":
                solver_command.extend(["--unsat", "--quiet"])
            elif args.solver_kind == "cadical":
                solver_command.append("--quiet")
            solver_command.append(str(cube_cnf))
        completed = subprocess.run(
            solver_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        elapsed = time.perf_counter() - started
        output.write_text(completed.stdout, encoding="ascii")
        if not args.keep_cnf:
            cube_cnf.unlink()
        if completed.returncode == 10:
            result = "SAT"
        elif completed.returncode == 20:
            result = "UNSAT"
        elif completed.returncode in {124, 137}:
            result = "UNKNOWN"
        else:
            result = "ERROR"
        return {
            "cube": index,
            "literals": cube,
            "result": result,
            "seconds": elapsed,
            "exit_code": completed.returncode,
            "stderr": completed.stderr[-1000:],
        }

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.jobs
    ) as executor:
        records = list(executor.map(solve, enumerate(cube_list)))
    records.sort(key=lambda record: record["cube"])
    summary = {
        "cnf": str(args.cnf),
        "cubes": str(args.cubes),
        "cube_count": len(cube_list),
        "cube_depth": depth,
        "split_variables": split_variables,
        "exhaustive_fixed_variable_partition": exhaustive_fixed,
        "exhaustive_parent_refinement": exhaustive_parent_refinement,
        "parents": str(args.parents) if args.parents is not None else None,
        "time_limit_seconds": args.seconds,
        "jobs": args.jobs,
        "counts": {
            status: sum(record["result"] == status for record in records)
            for status in ("SAT", "UNSAT", "UNKNOWN", "ERROR")
        },
        "records": records,
    }
    summary_path = args.work / "cube_sweep.json"
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    if not args.keep_cnf:
        template.unlink()
    print(json.dumps(summary["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
