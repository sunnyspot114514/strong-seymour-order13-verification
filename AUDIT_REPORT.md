# Independent verification report

## Verdict

The published artifacts support the finite claim:

> No regular tournament on 13 vertices has all 13 vertices non-strong.

Equivalently, every regular tournament on 13 vertices contains at least one
strong Seymour vertex.

## Audit environment

- Ubuntu 22.04.5 LTS under WSL2
- Python 3.10.12
- GNU g++ 11.4.0
- SciPy 1.15.3
- NumPy 2.2.6
- Debian `drat-trim` 0.0~git20240428.effa1dc-2

The third-party Debian package had SHA-256:

```text
a2613ed11f3b2ee1a183ed64ba265a7d88b9b892cef1a40a9097132ccabcc31f
```

## SAT reproduction

The solver and watched-literal checker were rebuilt from source. The six
CNFs were regenerated and were byte-identical to the published instances.
The newly generated RUP proofs were byte-identical to the published proofs.

| Branch | Variables | Clauses | RUP steps | Built-in checker | Naive checker | drat-trim |
|---:|---:|---:|---:|---|---|---|
| 0 | 3601 | 8656 | 1 | verified | verified | verified |
| 1 | 3601 | 8656 | 1 | verified | verified | verified |
| 2 | 3601 | 8656 | 817 | verified | verified | verified |
| 3 | 3601 | 8656 | 630 | verified | verified | verified |
| 4 | 3601 | 8656 | 1 | verified | verified | verified |
| 5 | 3601 | 8656 | 1 | verified | verified | verified |

The satisfiable negative-control CNF and model were also regenerated
byte-for-byte. Direct checking confirmed:

- all CNF clauses are satisfied;
- all 13 tournament vertices have out-degree 6;
- vertices 0 and 9 have maximum matching size 5;
- every other vertex has maximum matching size 6.

## Independent MILP reproduction

Both exact integer formulations were rerun in the Ubuntu environment:

- vertex-cover cases `p=0,...,5`: all six infeasible;
- Hall-witness cases `|S|=1,...,6`: all six infeasible.

The three weaker negative-control matrices were checked directly. Each is a
regular tournament in which the specified root has matching number 5 and the
remaining twelve vertices have matching number 6.

## Integrity and privacy checks

- All published scripts use repository-relative paths.
- Generated output is confined to ignored repository-relative directories.
- Precompiled binaries and virtual environments are excluded.
- A recursive scan found no local absolute path, original workspace name,
  host user name, attachment path, or local application directory.
- The repository was initialized only after sanitization, so excluded source
  paths are not present in Git history.

## Trust boundary

The RUP certificates establish unsatisfiability of the generated CNFs. The
graph-theoretic statement additionally relies on the mathematical reduction
and the correctness of `generate_cnf.py`. The SAT encoding was inspected
against both the vertex-cover characterization and the independent
Hall-witness MILP formulation.
