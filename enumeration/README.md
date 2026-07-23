# Complete Enumeration of Order-13 Regular Tournaments

[US English](README.md) | [CN 中文说明](README_zh.md)

## Result

This directory gives a second computational proof route for the exact
extremal result:

> Every regular tournament on 13 vertices has at least eleven strong
> Seymour vertices, and the bound is sharp.

Unlike the SAT proof, this computation uses no CNF generator, failure
flags, cardinality encoding, symmetry branches, SAT solver, or RUP
certificate.

## Complete catalogue

The input is Brendan McKay's catalogue containing one representative of
every isomorphism class of regular tournaments on 13 vertices:

- source:
  `https://users.cecs.anu.edu.au/~bdm/data/rt13.txt.gz`;
- compressed size: 8,498,810 bytes;
- SHA-256:
  `df63dbf6d173094b7fc31866f928410bd6738403d06be9b407eb5e28970fd058`;
- records after decompression: 1,495,297.

The catalogue itself is downloaded from its authoritative source and is not
mirrored in this repository. See [DATASET_PROVENANCE.md](DATASET_PROVENANCE.md).

## Direct verification method

For every catalogue record, the C++ verifier:

1. decodes the 78-bit upper triangle;
2. checks that all thirteen out-degrees are 6;
3. for each vertex `x`, forms the `6 x 6` bipartite graph of arcs from
   `N+(x)` to `N-(x)`;
4. tests for a perfect matching by exhaustive Hall-subset enumeration;
5. independently computes a maximum matching with a Kuhn augmenting-path
   implementation;
6. aborts if the two methods disagree even once.

All 1,495,297 records and all 19,438,861 vertex checks completed without a
disagreement.

## Distribution over isomorphism classes

| Number of strong vertices | Isomorphism classes |
|---:|---:|
| 11 | 13 |
| 12 | 48 |
| 13 | 1,495,236 |
| **Total** | **1,495,297** |

This is an unlabelled distribution: each isomorphism class is counted once,
not weighted by the number of labelled tournaments in the class.

The first minimum witness in catalogue order occurs at one-based record
764,615. It has matching-size vector

```text
[5, 6, 6, 6, 5, 6, 6, 6, 6, 6, 6, 6, 6].
```

Its non-strong vertices are 0 and 4. Explicit Hall defects and the full
adjacency matrix are stored in [RESULTS.json](RESULTS.json). A separate
Python verifier checks this witness by exhaustive partial injections and
exhaustive Hall subsets, without using the C++ matching implementation.

## Reproduce

Requirements:

- Bash, `curl`, `gzip`, and GNU coreutils;
- a C++17 compiler exposed as `g++`;
- Python 3;
- `/usr/bin/time`.

Run:

```bash
cd enumeration
bash run_enumeration.sh
```

The script downloads and authenticates the catalogue, compiles the verifier,
enumerates all records, compares the deterministic JSON result with the
published file, and independently verifies the first extremal witness.
Generated files remain in the ignored `enumeration/work/` directory.

## Trust boundary

This route is independent of the SAT encoding but relies on the completeness
and correctness of McKay's isomorphism-class catalogue, the documented
78-bit format, and the two direct graph algorithms. It is therefore a
substantially different computational cross-check, not an independent
regeneration of the catalogue.
