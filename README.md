# Strong Seymour verification at order 13

This repository contains a reproducible computer-assisted verification of the
following finite claim:

> Every regular tournament on 13 vertices contains a strong Seymour vertex.

Together with Theorem 1.5 of Bai, Li, and Park,
[*Towards a strengthening of the second neighborhood conjecture*](https://arxiv.org/abs/2607.18047),
this implies that every oriented graph on at most 13 vertices contains a
strong Seymour vertex.

Chinese documentation is available in [README_zh.md](README_zh.md).

## What is verified

For a vertex `x` in a regular tournament of order 13:

- `N+(x)` and `N-(x)` both have size 6;
- `N++(x) = N-(x)`;
- `x` is strong exactly when the bipartite graph of arcs from `N+(x)` to
  `N-(x)` has a perfect matching.

A counterexample would therefore require all 13 associated bipartite graphs
to have matching number at most 5. The SAT encoding represents this with a
size-at-most-5 vertex cover for every root. After symmetry breaking, the
root certificate has six exhaustive shapes, indexed by `p = 0,...,5`.
All six CNFs are unsatisfiable.

## Repository contents

- `generate_cnf.py`: deterministic generator for the six SAT instances.
- `cdcl.cpp`: small proof-producing CDCL solver.
- `rupcheck.cpp`: watched-literal RUP checker.
- `naive_rupcheck.py`: independent full-scan RUP checker.
- `cases/`: published CNFs, RUP refutations, metadata, and checker logs.
- `generate_control.py`, `verify_control.py`: satisfiable negative control.
- `milp_crosscheck/`: independent vertex-cover and Hall-witness MILP models.
- `AUDIT_REPORT.md`: independent Ubuntu 22.04 and third-party checker audit.
- `RESULTS.json`: machine-readable result summary.

No precompiled executable, virtual environment, local absolute path, user
name, or host-specific working directory is included.

## Reproduce the SAT verification

Requirements:

- Python 3;
- a C++17 compiler exposed as `g++`;
- Bash.

From the repository root:

```bash
./run_all.sh
```

The script compiles the solver and checker from source, regenerates all six
CNFs, solves them, verifies every RUP refutation with two independent
checkers, and checks a satisfiable negative control. If `drat-trim` is on
`PATH`, it is also used as a third-party DRAT/RUP checker.

Generated files are written only to the repository-relative `build/` and
`regenerated/` directories, both ignored by Git.

## Reproduce the MILP cross-check

Install NumPy and SciPy in an isolated environment, then run:

```bash
./run_milp_all.sh
```

This executes:

- six vertex-cover branches `p = 0,...,5`;
- six Hall-witness branches `|S| = 1,...,6`;
- direct verification of the satisfiable negative-control matrices.

All twelve feasibility branches must report `status 2` / `infeasible`.

## Scope and trust boundary

This is a finite computer-assisted verification, not a proof of the
conjecture for arbitrary order. The published RUP refutations prove the
generated CNFs unsatisfiable. The graph-theoretic conclusion also relies on
the correctness of the documented reduction and CNF generator.

For a more formally minimized trust base, the next step would be to emit
LRAT and validate it with a formally verified LRAT checker.
