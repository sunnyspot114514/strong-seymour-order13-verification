# Strong Seymour conjecture: exact order-13 feasibility check

## Claim checked

For every oriented graph `D` on at most 13 vertices, there is a vertex `x` for which a complete matching exists from `N+(x)` to `N++(x)`.

The paper arXiv:2607.18047 proves the claim whenever the minimum out-degree is at most 5. Therefore:

- every oriented graph on at most 12 vertices is already covered;
- a possible 13-vertex counterexample must have minimum out-degree at least 6;
- since an oriented graph on 13 vertices has at most 78 arcs, it must then have exactly 78 arcs and every vertex must have out-degree 6;
- hence the only remaining case is a 13-vertex regular tournament.

## Exact finite model

For a regular tournament on 13 vertices and a fixed root `x`:

- `|N+(x)| = |N-(x)| = 6`;
- `N++(x) = N-(x)`, because an in-neighbor of `x` cannot dominate `x` and all six out-neighbors without having out-degree at least 7.

Thus `x` is strong exactly when the bipartite graph of arcs from `N+(x)` to `N-(x)` has a perfect matching.

Two independent binary integer models were solved:

1. **Vertex-cover encoding.** A non-strong vertex has a bipartite vertex cover of size at most 5 by König's theorem.
2. **Hall-witness encoding.** A non-strong vertex has a set `S subset N+(x)` satisfying `|N(S)| < |S|`.

The orientation variables cover all labeled 13-vertex regular tournaments. Label symmetry is broken by fixing vertex 0 to dominate vertices 1–6 and lose to 7–12. The possible root-0 certificate shapes are split into six exhaustive cases.

## Result

All six cases were reported **infeasible** by HiGHS 1.8.0 under both independent encodings. The vertex-cover encoding was also rerun with presolve disabled, with the same result.

As a negative-control test, both encodings were weakened to require only vertex 0 to be non-strong. They then produced valid regular tournaments in which vertex 0 has maximum matching size 5, while the other twelve vertices are strong. `verify_matrices.py` checks these matrices independently using direct matching and exhaustive Hall-subset enumeration.

## Interpretation

This is strong exact computational evidence that the strengthened Seymour conjecture holds for all oriented graphs of order at most 13.

For a fully formal computer-assisted theorem, the next step should be one of:

- enumerate McKay's 1,495,297 non-isomorphic regular tournaments and run the independent checker; or
- translate the model to SAT and publish a DRAT/LRAT unsatisfiability certificate.

The current HiGHS result is reproducible but does not include a formally checkable UNSAT proof certificate.

## Run

```bash
python solve_vertex_cover_cases.py 0
python solve_vertex_cover_cases.py 1
# ... through case 5

python solve_hall_cases.py 1
# ... through Hall-set size 6

python verify_matrices.py
```

Dependencies: Python 3, NumPy, SciPy with `scipy.optimize.milp`.
