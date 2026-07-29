# A 24-vertex tournament counterexample to the strong Seymour conjecture

[US English](README.md) | [CN 中文说明](README_zh.md)

This directory gives an explicit structured tournament on 24 vertices with no strong Seymour vertex. Thus the proposed strengthening fails even for tournaments.

The construction substitutes transitive tournaments of orders

```text
(5,1,2,2,3,1,2,5,1,2)
```

into a 10-vertex tournament encoded by

```text
110000101011101000010111101010010100010010010
```

and orients all cross-class arcs according to the template.

A simple transitive-completion lemma proves the construction by lifting ten
class-level weighted Hall defects. The Python and C++ checkers verify that
every vertex fails Hall's condition and has matching number strictly below
its out-degree. A third checker uses finite-state dynamic programming and
optionally cross-checks every matching number with NetworkX.

The adjacency-matrix SHA-256 is

```text
d3b70f40dd3cc33f66ba23dcbb99138580d6cd6d6684e3658028606d680d23ed
```

Run:

```bash
bash run_all.sh
```

See [`docs/PROOF_zh.md`](docs/PROOF_zh.md) for the hand-checkable argument
and [`audit/AUDIT_REPORT.md`](audit/AUDIT_REPORT.md) for the independent
audit.

This construction originally gave

```text
14 <= n_oriented <= n_tournament <= 24.
```

The newer [`../tournament23/`](../tournament23/) package improves the
repository-wide upper bound to 23. This construction remains useful for its
compact weighted-blow-up proof. It does not prove minimality and has not yet
been peer reviewed.
