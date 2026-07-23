#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build regenerated

echo '[1/5] Compile solver and two independent RUP checkers'
g++ -O3 -std=c++17 src/cdcl.cpp -o build/cdcl
g++ -O3 -std=c++17 src/rupcheck.cpp -o build/rupcheck
g++ -O3 -std=c++17 src/scan_rupcheck.cpp -o build/scan_rupcheck

echo '[2/5] Regenerate and solve all six branches for >=3 non-strong vertices'
for p in 0 1 2 3 4 5; do
  python3 src/generate_extremal_cnf.py 3 "$p" "regenerated/m3_p${p}.cnf"
  cmp "regenerated/m3_p${p}.cnf" "certificates/m3_p${p}.cnf"
  cmp "regenerated/m3_p${p}.json" "certificates/m3_p${p}.json"
  set +e
  build/cdcl "regenerated/m3_p${p}.cnf" "regenerated/m3_p${p}.rup" \
    >"regenerated/m3_p${p}.solver.out" 2>"regenerated/m3_p${p}.solver.log"
  rc=$?
  set -e
  if [[ $rc -ne 20 ]]; then
    echo "branch p=$p: expected UNSAT exit code 20, got $rc" >&2
    exit 1
  fi
  cmp "regenerated/m3_p${p}.rup" "certificates/m3_p${p}.rup"
  build/rupcheck "regenerated/m3_p${p}.cnf" "regenerated/m3_p${p}.rup"
  build/scan_rupcheck "regenerated/m3_p${p}.cnf" "regenerated/m3_p${p}.rup"
  if command -v drat-trim >/dev/null 2>&1; then
    drat-trim "regenerated/m3_p${p}.cnf" "regenerated/m3_p${p}.rup" -U
  fi
done

echo '[3/5] Regenerate a tight witness with >=2 non-strong vertices'
python3 src/generate_extremal_cnf.py 2 2 regenerated/m2_p2.cnf
cmp regenerated/m2_p2.cnf tight/m2_p2.cnf
cmp regenerated/m2_p2.json tight/m2_p2.json
set +e
build/cdcl regenerated/m2_p2.cnf regenerated/m2_p2.rup regenerated/m2_p2.model \
  >regenerated/m2_p2.solver.out 2>regenerated/m2_p2.solver.log
rc=$?
set -e
if [[ $rc -ne 10 ]]; then
  echo "tight witness: expected SAT exit code 10, got $rc" >&2
  exit 1
fi
cmp regenerated/m2_p2.model tight/m2_p2.model
python3 src/analyze_tight_instance.py regenerated/m2_p2.cnf regenerated/m2_p2.model regenerated/tight_instance_analysis.json >/dev/null
cmp regenerated/tight_instance_analysis.json tight/tight_instance_analysis.json

echo '[4/5] Verify archive hashes'
sha256sum -c SHA256SUMS.txt

echo '[5/5] SUCCESS'
echo 'Certified exact extremal value: minimum strong vertices = 11, maximum non-strong vertices = 2.'
