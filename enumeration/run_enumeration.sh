#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORK="$ROOT/work"
DATASET="$WORK/rt13.txt.gz"
DATASET_URL="https://users.cecs.anu.edu.au/~bdm/data/rt13.txt.gz"
DATASET_SHA256="df63dbf6d173094b7fc31866f928410bd6738403d06be9b407eb5e28970fd058"
EXPECTED_RECORDS=1495297

mkdir -p "$WORK"

echo "[1/7] Obtain Brendan McKay's order-13 regular-tournament catalogue"
if [[ ! -f "$DATASET" ]]; then
  curl -L --fail --retry 3 -o "$DATASET" "$DATASET_URL"
fi

echo "[2/7] Verify catalogue integrity and record count"
ACTUAL_SHA256="$(sha256sum "$DATASET" | awk '{print $1}')"
if [[ "$ACTUAL_SHA256" != "$DATASET_SHA256" ]]; then
  echo "catalogue SHA-256 mismatch" >&2
  exit 1
fi
gzip -t "$DATASET"
ACTUAL_RECORDS="$(gzip -cd "$DATASET" | wc -l)"
if [[ "$ACTUAL_RECORDS" -ne "$EXPECTED_RECORDS" ]]; then
  echo "catalogue record-count mismatch" >&2
  exit 1
fi

echo "[3/7] Compile the direct Hall/matching enumerator"
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -Werror \
  "$ROOT/verify_rt13_catalog.cpp" -o "$WORK/verify_rt13_catalog"

echo "[4/7] Enumerate every non-isomorphic regular tournament"
(
  cd "$WORK"
  set -o pipefail
  gzip -cd rt13.txt.gz |
    /usr/bin/time -v ./verify_rt13_catalog \
      --exceptions-file EXCEPTIONAL_CLASSES.generated.jsonl \
      > RESULTS.generated.json 2> REPRODUCTION.generated.log
)

echo "[5/7] Compare deterministic results and all exceptional classes"
cmp "$ROOT/RESULTS.json" "$WORK/RESULTS.generated.json"
cmp "$ROOT/EXCEPTIONAL_CLASSES.jsonl" \
  "$WORK/EXCEPTIONAL_CLASSES.generated.jsonl"

echo "[6/7] Independently verify the witness and 61 exceptional records"
python3 "$ROOT/verify_witness.py" "$WORK/RESULTS.generated.json" \
  --catalog-gz "$DATASET" > "$WORK/WITNESS_VERIFICATION.generated.json"
cmp "$ROOT/WITNESS_VERIFICATION.json" \
  "$WORK/WITNESS_VERIFICATION.generated.json"
python3 "$ROOT/verify_exceptional_classes.py" \
  "$WORK/EXCEPTIONAL_CLASSES.generated.jsonl" \
  --catalog-gz "$DATASET" > "$WORK/EXCEPTIONAL_VERIFICATION.generated.json"
cmp "$ROOT/EXCEPTIONAL_VERIFICATION.json" \
  "$WORK/EXCEPTIONAL_VERIFICATION.generated.json"

echo "[7/7] SUCCESS"
echo "records=$EXPECTED_RECORDS minimum_strong=11 tight_classes=13"
