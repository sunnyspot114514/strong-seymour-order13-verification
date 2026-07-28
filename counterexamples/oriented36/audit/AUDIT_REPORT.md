# Independent audit of the order-36 oriented construction

The explicit six-cluster construction was independently checked on
2026-07-29.

Three direct routes agree:

1. the bundled Python Hall-enumeration and augmenting-path checker;
2. the separately implemented C++ Hall-enumeration and augmenting-path
   checker;
3. an audit implementation using reachable-right-mask dynamic programming,
   with NetworkX 3.6.1 as an additional cross-check.

All routes report:

```text
order = 36
arc count = 509
minimum out-degree = 13
strong vertex count = 0
matrix SHA-256 =
ce1ce6f2e86b7e4546477e1f821e2ccb155836c58ee27418252930fe4c585985
```

The six advertised class certificates were recomputed exactly:
`13>12`, `15>14`, `7>6`, `11>10`, `12>11`, and `14>13`.

The C++ checker was also compiled with AddressSanitizer and
UndefinedBehaviorSanitizer under Ubuntu 22.04/GCC 11.4.0 and produced no
diagnostics.

The audit covers the explicit construction. It does not certify global
minimality or rerun the multi-billion-vector weighted-template search.
