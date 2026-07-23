# Independent audit of the exact extremal experiment

## Verdict

The package was independently inspected and reproduced. The available
evidence supports:

> The minimum number of strong Seymour vertices among 13-vertex regular
> tournaments is exactly 11.

## Artifact integrity

The supplied archive had SHA-256:

```text
a4ca8b8d0ab5c262b0baf92eea32826d770a1892d40b4428d27756916414b7c8
```

All 49 entries listed in its internal manifest were present and had the
declared SHA-256. A recursive source and text scan found no local absolute
path, original attachment path, host user name, or workspace-specific
directory.

## Independent reproduction

The complete `run_all.sh` workflow was run under:

- Ubuntu 22.04.5 LTS on WSL2;
- Python 3.10.12;
- GNU g++ 11.4.0;
- Debian `drat-trim` 0.0~git20240428.effa1dc-2.

It rebuilt the solver and checkers from source, regenerated all six
`min_fail = 3` CNFs, regenerated their RUP proofs, and reproduced the
`min_fail = 2` satisfiable witness. The regenerated instances, proofs,
model, and witness analysis matched the published files.

The raw successful run is preserved in
[`INDEPENDENT_REPRODUCTION.log`](INDEPENDENT_REPRODUCTION.log).

All six UNSAT branches were accepted by:

| Branch `p` | Included watched checker | Included scan checker | `drat-trim -U` |
|---:|---|---|---|
| 0 | verified | verified | verified |
| 1 | verified | verified | verified |
| 2 | verified | verified | verified |
| 3 | verified | verified | verified |
| 4 | verified | verified | verified |
| 5 | verified | verified | verified |

The official upstream source was also cloned independently and compiled
using the command from its Makefile:

```text
gcc drat-trim.c -std=c99 -O2 -o drat-trim
```

The audited upstream build was:

```text
repository:    https://github.com/marijnheule/drat-trim.git
commit:        2e3b2dc0ecf938addbd779d42877b6ed69d9a985
compiler:      GCC 11.4.0
binary SHA256: b535cc5334e97fba5b5db6013625c5a0b16ce348a98d59ff91b45a83fa56b39e
mode:          -U (RUP-only)
```

All six upstream-checker processes exited with code zero, reported
`s VERIFIED`, and reported zero RAT lemmas. Complete logs are in
`upstream_drat_trim/`.

The Debian `drat-trim` package used in the audit had SHA-256:

```text
a2613ed11f3b2ee1a183ed64ba265a7d88b9b892cef1a40a9097132ccabcc31f
```

## Encoding inspection

The generator was inspected separately from proof checking:

- 78 orientation variables encode exactly one direction for every pair;
- degree constraints force every vertex to have out-degree 6;
- `f[x]` activates a size-at-most-five vertex-cover certificate for vertex
  `x`;
- a cardinality constraint requires at least three activated failure
  certificates;
- `f[0]` and the root-neighborhood orientation fix a failing root;
- `p=0,...,5` exhausts its padded size-five cover after relabeling within
  each side.

By Kőnig's theorem, a size-at-most-five cover is equivalent to failure of a
perfect matching in the relevant `6 x 6` bipartite graph. No discrepancy was
found between the stated reduction and the implemented clauses.

## Independent sharpness check

The published adjacency matrix was checked with a separate exhaustive
matching procedure based on enumerating permutations and Hall subsets,
rather than the augmenting-path implementation in the package. It confirmed:

- tournament antisymmetry and zero diagonal;
- out-degree 6 at every vertex;
- matching sizes
  `[5,6,6,6,6,5,6,6,6,6,6,6,6]`;
- non-strong vertices exactly `{0,5}`;
- Hall defects
  `S={3,4,5,6}, Gamma(S)={7,8,9}` for vertex 0 and
  `S={3,4,6}, Gamma(S)={7,9}` for vertex 5;
- adjacency-matrix SHA-256
  `8f7926e1544e8bc087fbce2595754b7a9c30719be7ced398368c053cf45c09fb`.

## Trust boundary

The RUP proofs certify the unsatisfiability of the six generated CNFs. The
extremal theorem also relies on the mathematical reduction, the CNF
generator, and the interpretation of the tight witness. The independent
encoding inspection and separately implemented witness check reduce, but do
not eliminate, this trusted base. The result has not been peer reviewed or
formalized in a theorem prover.
