#!/usr/bin/env python3
"""Small deterministic command-line wrapper around installed PySAT solvers."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from pysat.formula import CNF
from pysat.solvers import Solver


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf", type=Path)
    parser.add_argument(
        "--solver",
        default="glucose4",
        help="a solver name accepted by pysat.solvers.Solver",
    )
    parser.add_argument("--model", type=Path)
    args = parser.parse_args()

    formula = CNF(from_file=str(args.cnf))
    started = time.perf_counter()
    with Solver(name=args.solver, bootstrap_with=formula.clauses) as solver:
        satisfiable = solver.solve()
        elapsed = time.perf_counter() - started
        model = solver.get_model() if satisfiable else None
        statistics = solver.accum_stats()

    print("s SATISFIABLE" if satisfiable else "s UNSATISFIABLE")
    if model is not None and args.model is not None:
        args.model.write_text(
            "v " + " ".join(map(str, model)) + " 0\n",
            encoding="ascii",
        )
    print(
        "c "
        + json.dumps(
            {
                "solver": args.solver,
                "seconds": elapsed,
                "variables": formula.nv,
                "clauses": len(formula.clauses),
                "statistics": statistics,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
