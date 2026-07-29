# Explicit Counterexamples

[US English](README.md) | [CN 中文说明](README_zh.md)

This directory contains three directly checkable constructions.

| Construction | Graph class | Order | Strong Seymour vertices |
|---|---|---:|---:|
| [`tournament23/`](tournament23/) | tournament | 23 | 0 |
| [`tournament24/`](tournament24/) | tournament | 24 | 0 |
| [`oriented36/`](oriented36/) | oriented graph with independent clusters | 36 | 0 |

The order-23 tournament is the strongest upper bound. The order-24 and
order-36 constructions are retained because their weighted blow-up
descriptions are especially simple.

Together with the separately verified order-at-most-13 result, the current
bounds should be written using two different parameters:

```text
14 <= n_oriented <= n_tournament <= 23.
```

No directory proves minimality at order 23. Exact searches at orders 14
through 22 are recorded separately until they produce checked SAT witnesses
or certified UNSAT results.
