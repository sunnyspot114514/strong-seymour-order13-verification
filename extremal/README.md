# Exact extremal verification

## Result

> Every regular tournament on 13 vertices contains at least eleven strong
> Seymour vertices, and this bound is sharp.

Equivalently, at most two vertices can be non-strong, and the package
contains a tournament with exactly two.

## Reduction

For a vertex `x` in a regular tournament of order 13, both `N+(x)` and
`N-(x)` have size 6 and `N++(x) = N-(x)`. The strong Seymour condition is
therefore equivalent to the existence of a perfect matching in the
`6 x 6` bipartite graph of arcs from `N+(x)` to `N-(x)`.

By Kőnig's theorem, `x` is non-strong exactly when this bipartite graph has a
vertex cover of size at most 5. The SAT encoding attaches such a cover
certificate to every vertex declared non-strong.

To rule out three non-strong vertices, choose one of them as root 0, label
its out-neighbors 1 through 6 and its in-neighbors 7 through 12, and pad its
cover to size 5. If the cover contains `p` left-side vertices, then
`p = 0,...,5`. Relabeling within both sides makes these six branches
exhaustive. Every branch is UNSAT.

## Certificates

| Root branch `p` | Status | RUP steps |
|---:|---|---:|
| 0 | UNSAT | 1 |
| 1 | UNSAT | 1 |
| 2 | UNSAT | 19,031 |
| 3 | UNSAT | 19,236 |
| 4 | UNSAT | 1 |
| 5 | UNSAT | 1 |

The published proofs are checked by two included implementations:

1. a watched-literal C++ RUP checker;
2. an independent full-scan/occurrence C++ RUP checker.

When `drat-trim` is on `PATH`, the reproduction script also invokes it in
RUP-only mode.

## Sharp witness

`tight/m2_p2.model` encodes a regular tournament whose matching sizes are:

```text
[5, 6, 6, 6, 6, 5, 6, 6, 6, 6, 6, 6, 6]
```

Only vertices 0 and 5 are non-strong. Their Hall defects are:

```text
vertex 0: S = {3,4,5,6}, Gamma(S) = {7,8,9}
vertex 5: S = {3,4,6},   Gamma(S) = {7,9}
```

The full adjacency matrix, perfect matchings for the other eleven vertices,
and Hall certificates are in `tight/tight_instance_analysis.json`.

## Reproduce

On Ubuntu 22.04 or another Debian-like environment:

```bash
sudo apt install g++ python3 drat-trim
bash run_all.sh
```

`drat-trim` is optional. The script always rebuilds and runs both bundled
RUP checkers, regenerates the tight witness analysis, and compares all
outputs with the published artifacts.

## Files

- `src/generate_extremal_cnf.py`: deterministic CNF generator;
- `src/cdcl.cpp`: proof-producing SAT solver;
- `src/rupcheck.cpp`: watched-literal RUP checker;
- `src/scan_rupcheck.cpp`: independent full-scan/occurrence checker;
- `src/analyze_tight_instance.py`: regularity, matching, and Hall analysis;
- `certificates/`: six UNSAT CNFs, RUP proofs, metadata, and logs;
- `tight/`: satisfiable sharp witness and its analysis;
- `RESULTS.json`: machine-readable summary;
- `AUDIT_REPORT.md`: independent reproduction and third-party-checker audit;
- `INDEPENDENT_REPRODUCTION.log`: raw successful WSL run including all
  `drat-trim` checks.

This is a finite computer-assisted result and has not been peer reviewed.
