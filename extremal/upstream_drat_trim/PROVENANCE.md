# Upstream drat-trim verification provenance

- Repository: `https://github.com/marijnheule/drat-trim.git`
- Commit: `2e3b2dc0ecf938addbd779d42877b6ed69d9a985`
- Commit date: `2024-11-25T10:20:26-05:00`
- Compiler: `gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0`
- Build command: `gcc drat-trim.c -std=c99 -O2 -o drat-trim`
- Executable SHA-256:
  `b535cc5334e97fba5b5db6013625c5a0b16ce348a98d59ff91b45a83fa56b39e`
- Verification command template:
  `drat-trim certificates/m3_pP.cnf certificates/m3_pP.rup -U`
- Verification mode: upstream `-U` option, which only permits RUP
  additions.

The executable is not included. It is rebuilt from the pinned upstream
source so that the checker binary is not part of the trusted distribution.
Each `m3_pP.official_drat_trim.log` file records the complete checker output
and process exit code for one branch.
