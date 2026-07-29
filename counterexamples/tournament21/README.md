# A verified 21-vertex tournament counterexample

[US English](README.md) | [CN 中文说明](README_zh.md)

This package contains an explicit tournament of order 21 with no strong
Seymour vertex. For every vertex \(x\), the bipartite graph from
\(N^+(x)\) to the strict second out-neighbourhood \(N^{++}(x)\) has no
matching that saturates \(N^+(x)\).

The construction improves the explicit upper bound in this repository from
23 to 21. It does **not** by itself prove that 21 is the minimum order.

## Counterexample

The adjacency matrix is in
[`data/adjacency_matrix.txt`](data/adjacency_matrix.txt). Entry \(A_{uv}=1\)
means \(u\to v\). Its canonical LF-terminated SHA-256 is:

```text
9773f6f889db845bd727c726988b7017a99a8f3bff79896fed214b2aed9a6d5e
```

The outdegrees are:

```text
9,10,10,9,9,9,10,10,11,12,9,9,9,11,11,11,9,10,10,10,12
```

The independently computed maximum matching sizes are:

```text
8,9,9,8,8,8,8,9,8,8,8,8,8,9,9,9,8,9,9,9,8
```

Every matching number is smaller than the corresponding outdegree, so all
21 vertices are non-strong.

## Verification

Two deliberately different checkers are included:

- `src/verify.py` uses finite-state dynamic programming for exact maximum
  matchings and enumerates every left subset to obtain a Hall defect.
- `src/verify.cpp` uses a Kuhn augmenting-path matcher and independently
  enumerates every left subset.

The complete matching values and explicit Hall witnesses are in
[`data/full_verification.json`](data/full_verification.json).

Run the full check under Ubuntu or WSL:

```bash
./run_all.sh
```

The script verifies hashes, rebuilds the C++ checker, reruns both
implementations, and compares the regenerated JSON byte-for-byte with the
published result.

## Discovery and current bound

An exact order-22 SAT search first found a model in branch \(d=9,p=2\).
That model had a universal source. Deleting that source left the 21-vertex
tournament published here, and direct recomputation confirmed that every
remaining vertex was still non-strong.

Together with the verified positive result through order 13, this gives:

\[
14\le n_{\min}\le 21.
\]

The exact order-20 search is kept separate from this counterexample claim:
timeouts and unsuccessful heuristic searches are not nonexistence proofs.
