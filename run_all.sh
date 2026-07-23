#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build regenerated

echo '[1/6] Compile solver and checkers'
g++ -O3 -std=c++17 cdcl.cpp -o build/cdcl
g++ -O3 -std=c++17 rupcheck.cpp -o build/rupcheck

echo '[2/6] Generate, solve, and verify six exhaustive branches'
for p in 0 1 2 3 4 5; do
  python3 generate_cnf.py "$p" "regenerated/case${p}.cnf"
  cmp "cases/case${p}.cnf" "regenerated/case${p}.cnf"
  set +e
  build/cdcl "regenerated/case${p}.cnf" "regenerated/case${p}.rup" \
    >"regenerated/case${p}.solver.out" 2>"regenerated/case${p}.solver.log"
  rc=$?
  set -e
  if [[ $rc -ne 20 ]]; then
    echo "case $p: expected UNSAT exit code 20, got $rc" >&2
    exit 1
  fi
  build/rupcheck "regenerated/case${p}.cnf" "regenerated/case${p}.rup"
  python3 naive_rupcheck.py "regenerated/case${p}.cnf" "regenerated/case${p}.rup"
  if command -v drat-trim >/dev/null 2>&1; then
    drat-trim "regenerated/case${p}.cnf" "regenerated/case${p}.rup"
  fi
done

echo '[3/6] Generate a satisfiable negative control'
python3 generate_control.py 3 regenerated/control3.cnf
set +e
build/cdcl regenerated/control3.cnf regenerated/control3.rup regenerated/control3.model \
  >regenerated/control3.solver.out 2>regenerated/control3.solver.log
rc=$?
set -e
if [[ $rc -ne 10 ]]; then
  echo "control: expected SAT exit code 10, got $rc" >&2
  exit 1
fi
python3 verify_control.py regenerated/control3.cnf regenerated/control3.model \
  >regenerated/control3.verify

echo '[4/6] Compare deterministic published artifacts'
cmp control3.cnf regenerated/control3.cnf
cmp control3.model regenerated/control3.model

echo '[5/6] Optional negative-control matrix check (requires scipy)'
if python3 - <<'PY' >/dev/null 2>&1
import scipy
PY
then
  python3 milp_crosscheck/verify_matrices.py
else
  echo 'scipy not available; skipped MILP cross-check'
fi

echo '[6/6] Done: all six UNSAT certificates and the SAT control verified.'
