#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p milp_results

for p in 0 1 2 3 4 5; do
  log="milp_results/vertex_cover_${p}.log"
  python3 milp_crosscheck/solve_vertex_cover_cases.py "$p" >"$log" 2>&1
  grep -q '^status 2$' "$log"
  grep -q 'infeasible' "$log"
  echo "vertex-cover case ${p}: infeasible"
done

for s in 1 2 3 4 5 6; do
  log="milp_results/hall_${s}.log"
  python3 milp_crosscheck/solve_hall_cases.py "$s" >"$log" 2>&1
  grep -q '^status 2$' "$log"
  grep -q 'infeasible' "$log"
  echo "Hall-witness size ${s}: infeasible"
done

python3 milp_crosscheck/verify_matrices.py \
  >milp_results/negative_controls.log

echo 'All twelve MILP branches are infeasible; negative controls verified.'
