# Exact Strong Seymour extremum at order 13

This repository contains a reproducible computer-assisted verification of
the following exact finite result:

> **Every regular tournament on 13 vertices has at least eleven strong
> Seymour vertices, and this bound is sharp.**

Equivalently, such a tournament has at most two non-strong vertices, and a
tournament attaining two is included.

Chinese documentation is available in [README_zh.md](README_zh.md). The
strengthened experiment, certificates, and tight witness are in
[`extremal/`](extremal/).

## Evidence at a glance

The upper-bound computation asks whether a 13-vertex regular tournament can
have at least three non-strong vertices. After choosing one failing vertex
as root and normalizing a padded size-five vertex cover, every candidate
falls into one of six branches `p = 0,...,5`. All six branches are UNSAT.

| Root branch `p` | Status | RUP steps |
|---:|---|---:|
| 0 | UNSAT | 1 |
| 1 | UNSAT | 1 |
| 2 | UNSAT | 19,031 |
| 3 | UNSAT | 19,236 |
| 4 | UNSAT | 1 |
| 5 | UNSAT | 1 |

Each proof was accepted by:

- the included watched-literal C++ RUP checker;
- the independently implemented full-scan/occurrence C++ RUP checker;
- Debian `drat-trim` 0.0~git20240428.effa1dc-2 in an independent audit.

Sharpness is witnessed by the included regular tournament with matching
sizes

```text
[5, 6, 6, 6, 6, 5, 6, 6, 6, 6, 6, 6, 6].
```

Thus vertices 0 and 5 are non-strong and the other eleven are strong.
Explicit Hall-defect certificates are included for both failing vertices.

## Reproduce the exact extremal verification

Requirements are Python 3, Bash, and a C++17 compiler exposed as `g++`.
`drat-trim` is optional but recommended.

```bash
cd extremal
bash run_all.sh
```

This rebuilds every executable from source, regenerates every CNF, proof,
model, and analysis file, runs the two bundled proof checkers and optional
`drat-trim`, and compares all regenerated artifacts with the published
files.

See [`extremal/README.md`](extremal/README.md) for the mathematical
reduction and [`extremal/AUDIT_REPORT.md`](extremal/AUDIT_REPORT.md) for the
independent WSL/Ubuntu and third-party-checker audit.

## Earlier baseline experiment

The repository root also preserves the earlier, weaker verification that
every regular tournament on 13 vertices contains at least one strong
Seymour vertex. Its original one-command reproduction remains:

```bash
bash run_all.sh
```

The independent MILP cross-check for that baseline remains available as:

```bash
bash run_milp_all.sh
```

Together with Theorem 1.5 of Bai, Li, and Park,
[*Towards a strengthening of the second neighborhood conjecture*](https://arxiv.org/abs/2607.18047),
the existence result implies that every oriented graph on at most 13
vertices contains a strong Seymour vertex. The strengthened lower bound of
eleven applies specifically to 13-vertex regular tournaments.

## Scope and trust boundary

This is a finite computer-assisted result and has not been peer reviewed.
The RUP certificates establish unsatisfiability of the published CNFs. The
graph-theoretic conclusion additionally relies on the documented reduction
and the correctness of the CNF generator. No precompiled executable,
virtual environment, local absolute path, user name, or host-specific
working directory is published.
