# Explicit Counterexamples

[US English](README.md) | [CN 中文说明](README_zh.md)

This directory contains two directly checkable constructions.

| Construction | Graph class | Order | Strong Seymour vertices |
|---|---|---:|---:|
| [`tournament24/`](tournament24/) | tournament | 24 | 0 |
| [`oriented36/`](oriented36/) | oriented graph with independent clusters | 36 | 0 |

The order-24 tournament is the stronger upper bound. The order-36
construction is retained because its six-cluster weighted blow-up and
scalable infinite family are especially simple.

Together with the separately verified order-at-most-13 result, the current
bounds should be written using two different parameters:

```text
14 <= n_oriented <= n_tournament <= 24.
```

Neither directory proves minimality at order 24. Heuristic searches at
orders 14 through 23 are not part of the certified claims.
