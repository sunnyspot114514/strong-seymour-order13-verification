# A verified 23-vertex tournament counterexample

[English](README.md) | [中文说明](README_zh.md)

This package contains an explicit tournament of order 23 with no strong
Seymour vertex.  For every vertex \(x\), the bipartite graph from
\(N^+(x)\) to the strict second out-neighbourhood \(N^{++}(x)\) has no
matching that saturates \(N^+(x)\).

This improves the explicit upper bound in this repository from 24 to 23.
It does **not** yet prove that 23 is the minimum order: orders 14 through
22 still require complete exclusion or a smaller counterexample.

## Counterexample

The adjacency matrix is in
[`data/adjacency_matrix.txt`](data/adjacency_matrix.txt).  Entry \(A_{uv}=1\)
means \(u\to v\).  Its SHA-256 is:

```text
c6789b8adaf98b5d1da924a453243cad253d385263a7c08652f5bc7ff80f7612
```

The outdegrees are:

```text
10,12,11,10,11,11,12,12,10,11,11,10,11,13,11,10,12,11,11,10,11,12,10
```

The independently computed maximum matching sizes are:

```text
9,10,10,9,10,10,10,10,9,10,10,9,10,9,10,9,10,10,10,9,10,10,9
```

Every matching number is strictly smaller than the corresponding
outdegree, so all 23 vertices are non-strong.

## Verification

Two deliberately different checkers are included:

- `src/verify.py` uses finite-state dynamic programming for exact maximum
  matchings and enumerates every left subset to obtain a Hall defect.
- `src/verify.cpp` uses a Kuhn augmenting-path matcher and independently
  enumerates every left subset.

The complete per-vertex matching values and explicit Hall witnesses are in
[`data/full_verification.json`](data/full_verification.json).

Run the full check under Ubuntu/WSL:

```bash
./run_all.sh
```

The script verifies hashes, reruns both implementations from source, and
compares the regenerated JSON byte-for-byte with the published result.

## Discovery and current bound

The matrix was found as a satisfying assignment of the exact
minimum-degree branch \(d=10,p=4\), where \(p\) is the number of
out-neighbour vertices in a padded size-\(d-1\) vertex-cover witness for
the canonical minimum-outdegree root.

Together with the verified positive result through order 13, this gives

\[
14\le n_{\min}\le 23.
\]

The ongoing exact search for orders 14–22 is kept separate from the
counterexample claim so that bounded solver runs are never reported as
proofs.
