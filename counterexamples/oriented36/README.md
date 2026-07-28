# A Structured Order-36 Oriented Counterexample

[US English](README.md) | [CN 中文说明](README_zh.md)

Take six independent clusters of sizes

```text
(11, 7, 3, 3, 3, 9)
```

and orient every inter-cluster pair according to the tournament

```text
0 -> 1,2,4
1 -> 3,4,5
2 -> 1,5
3 -> 0,2
4 -> 2,3,5
5 -> 0,3
```

The resulting oriented graph has 36 vertices and no strong Seymour vertex.
For a root in each cluster, the following unions of out-neighbour clusters
violate Hall's condition:

| Root | Selected classes | Reachable strict-second classes | Weights |
|---:|---|---|---:|
| 0 | 1,2,4 | 3,5 | 13 > 12 |
| 1 | 3,4,5 | 0,2 | 15 > 14 |
| 2 | 1 | 3,4 | 7 > 6 |
| 3 | 0 | 1,4 | 11 > 10 |
| 4 | 3,5 | 0 | 12 > 11 |
| 5 | 0,3 | 1,2,4 | 14 > 13 |

Vertices in one cluster have identical neighbourhoods, so these six
certificates cover all 36 vertices. Scaling every cluster size by the same
positive integer preserves every strict inequality and gives an infinite
family of orders `36, 72, 108, ...`.

Run:

```bash
bash run_all.sh
```

The script rebuilds the C++ checker, runs the Python and C++ implementations,
runs a third finite-state-DP audit, compares the regenerated full JSON with
the published JSON, and checks all fixed hashes. NetworkX is an optional
additional cross-check.

This directory certifies the explicit construction only. It makes no
minimality claim and does not include the much larger weighted-template
search.
