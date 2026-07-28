# Independent audit of the order-24 tournament

The construction was audited on 2026-07-29 without importing either bundled
checker.

The independent checker reconstructs the graph from the ten explicit
template out-neighbourhoods and weights, verifies all 276 unordered vertex
pairs, and compares the resulting matrix byte-for-byte with the published
matrix. It then:

- computes strict second out-neighbourhoods directly from length-two paths;
- computes all 24 matching numbers by reachable-right-mask dynamic
  programming;
- enumerates a Hall defect for every root;
- validates every entry in `data/full_verification.json`;
- validates the ten weighted class-level Hall certificates;
- cross-checks the matching numbers with NetworkX 3.6.1 when available.

The audit found zero strong Seymour vertices and no DP/NetworkX disagreement.
The published matrix SHA-256 is:

```text
d3b70f40dd3cc33f66ba23dcbb99138580d6cd6d6684e3658028606d680d23ed
```

The bundled C++ checker was additionally compiled with AddressSanitizer and
UndefinedBehaviorSanitizer under Ubuntu 22.04/GCC 11.4.0. It terminated
successfully without sanitizer diagnostics.

This certifies an upper bound of 24; it does not prove order 24 minimal.
