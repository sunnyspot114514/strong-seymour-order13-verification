# Minimum tournament-counterexample research

[US English](README.md) | [CN 中文说明](README_zh.md)

This directory contains exploratory, reproducible code for deciding whether
the published order-24 tournament counterexample can be reduced. Search
failures and solver timeouts are not nonexistence proofs.

## Exact formulation

For a tournament root `r`, the matching graph has an edge `y--z` exactly
when `r -> y -> z -> r` is a directed triangle. Thus `r` is non-strong if
and only if this bipartite graph has a vertex cover of size at most
`d+(r)-1`.

`generate_tournament_cnf.py` encodes this condition for every root. It:

- relabels a minimum-outdegree vertex as vertex 0;
- fixes its out-neighbours before its in-neighbours;
- enforces the same minimum-outdegree lower bound at every vertex;
- canonically branches on `p`, the number of root-cover vertices in the
  out-neighbourhood;
- uses directed Hamiltonian paths inside the four interchangeable root
  membership blocks as a complete symmetry break.

For order 23, the minimum outdegree is at most 11. The published theorem for
minimum outdegree at most 5 means that the complete exact search consists of
the branches

```text
d = 6,...,11
p = max(0, 2d-23),...,d-1.
```

Example:

```bash
python generate_tournament_cnf.py 23 7 work/n23_d7_p3.cnf \
  --encoding cover --root-cover-left 3
kissat work/n23_d7_p3.cnf > work/n23_d7_p3.model
```

If a branch is satisfiable, independently verify the emitted model:

```bash
python verify_tournament_model.py \
  work/n23_d7_p3.json work/n23_d7_p3.model work/verified.json
```

The verifier reconstructs the tournament and recomputes every strict second
neighbourhood, maximum matching, and Hall defect without trusting the cover
variables in the SAT model.

`solve_tournament_milp.py` and `solve_tournament_cpsat.py` encode the same
mathematical specification without a CNF cardinality counter. They provide
compact HiGHS MILP and OR-Tools CP-SAT cross-checks. Optional exploratory
dependencies are:

```bash
python -m pip install scipy python-sat ortools
```

The known order-24 counterexample is a positive control. Passing
`--fix-matrix` fixes its orientations after canonical relabelling:

```bash
python generate_tournament_cnf.py 24 10 work/order24-fixed.cnf \
  --encoding cover \
  --fix-matrix ../../counterexamples/tournament24/data/adjacency_matrix.txt
```

## Direct local search

`search_tournament.cpp` starts from vertex-deleted subgraphs of the published
order-24 tournament. It uses single-edge flips and degree-preserving directed
triangle reversals. Every candidate is evaluated by exact bipartite maximum
matching for all roots.

```bash
g++ -O3 -std=c++17 -Wall -Wextra -Wpedantic -Werror \
  search_tournament.cpp -o search_tournament
./search_tournament \
  ../../counterexamples/tournament24/data/adjacency_matrix.txt \
  30 250000 779 4 0 7
```

The final argument is the required minimum outdegree. A zero-strong
candidate is printed to standard output. Progress is printed to standard
error.

`analyze_tournament.py` independently reports the strong vertices, exact
matchings, minimum covers, and the closest size-`d-1` cover for any matrix.

## Structured template search

`search_weighted_templates.py` searches transitive blow-ups of tournament
templates. For each template root it enumerates the Pareto-maximal weighted
Hall witnesses, then uses an integer program to choose positive cluster
weights.

The following checks all templates at edge-flip distance two from the
published 10-point template, split over four independent workers:

```bash
for worker in 0 1 2 3; do
  python search_weighted_templates.py \
    --verification-json \
    ../../counterexamples/tournament24/data/full_verification.json \
    --cap 23 --flip-distance 2 --workers 4 --worker-index "$worker" \
    --output "work/template-distance2-worker${worker}.json" &
done
wait
```

As controls, the unmodified template is infeasible at total weight 23 and
feasible at total weight 24.

## Current exploratory status

As of 2026-07-29:

- the fixed order-24 positive control is SAT and independently verified;
- the six order-13 regular-tournament branches are UNSAT;
- all order-23 branches with minimum outdegree 6 are UNSAT;
- the completed higher-degree branches and all unresolved branches are listed
  precisely in `EXACT_SEARCH_STATUS.json`;
- reproducible local searches at minimum outdegrees 6 and 7 reach one
  remaining strong vertex, but have not found an order-23 counterexample.
- the base 10-point blow-up template and every template at edge-flip distance
  at most two are infeasible at total weight 23; see
  `STRUCTURED_RESULTS.json`.

These are working results. A branch is promoted to a certified lower bound
only after every branch is complete and its UNSAT proof is checked by a
standard proof verifier.
