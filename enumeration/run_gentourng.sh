#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORK="$ROOT/work/gentourng"
ARCHIVE="$WORK/nauty2_9_3.tar.gz"
NAUTY_URL="https://users.cecs.anu.edu.au/~bdm/nauty/nauty2_9_3.tar.gz"
NAUTY_SHA256="9fc4edae04f88a0f5883985be3b39cf7f898fd6cc96e96b9ee25452743cc1b5b"

mkdir -p "$WORK"
BUILD_ROOT="$(mktemp -d "$WORK/nauty-build.XXXXXX")"
SOURCE="$BUILD_ROOT/nauty2_9_3"
SOURCE_REL="$(basename "$BUILD_ROOT")/nauty2_9_3"

cleanup() {
  case "$BUILD_ROOT" in
    "$WORK"/nauty-build.*) rm -rf -- "$BUILD_ROOT" ;;
    *) echo "refusing to remove unexpected build path" >&2; return 1 ;;
  esac
}
trap cleanup EXIT

echo "[1/8] Obtain and authenticate the official nauty 2.9.3 source"
if [[ ! -f "$ARCHIVE" ]]; then
  curl -L --fail --retry 3 -o "$ARCHIVE" "$NAUTY_URL"
fi
ACTUAL_SHA256="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
if [[ "$ACTUAL_SHA256" != "$NAUTY_SHA256" ]]; then
  echo "nauty source SHA-256 mismatch" >&2
  exit 1
fi

echo "[2/8] Configure and compile gentourng and labelg from source"
tar -xzf "$ARCHIVE" -C "$BUILD_ROOT"
(
  cd "$SOURCE"
  ./configure > "$WORK/configure.generated.log" 2>&1
  make -j2 gentourng labelg > "$WORK/make.generated.log" 2>&1
)
sha256sum "$SOURCE/gentourng" "$SOURCE/labelg" \
  > "$WORK/NAUTY_BINARIES.generated.sha256"

echo "[3/8] Compile the direct Hall/matching verifier"
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -Werror \
  "$ROOT/verify_rt13_catalog.cpp" -o "$WORK/verify_rt13_catalog"

echo "[4/8] Generate all regular order-13 tournaments and verify the stream"
(
  cd "$WORK"
  set -o pipefail
  {
    /usr/bin/time -v "$SOURCE_REL/gentourng" -d6 -D6 13 \
      2> GENTOURNG_GENERATOR.generated.log
  } |
    /usr/bin/time -v ./verify_rt13_catalog \
      --exceptions-file GENTOURNG_EXCEPTIONAL_CLASSES.generated.jsonl \
      > GENTOURNG_RESULTS.generated.json \
      2> GENTOURNG_VERIFIER.generated.log
)

echo "[5/8] Compare the deterministic gentourng artifacts"
cmp "$ROOT/GENTOURNG_RESULTS.json" \
  "$WORK/GENTOURNG_RESULTS.generated.json"
cmp "$ROOT/GENTOURNG_EXCEPTIONAL_CLASSES.jsonl" \
  "$WORK/GENTOURNG_EXCEPTIONAL_CLASSES.generated.jsonl"

echo "[6/8] Independently verify all regenerated exceptional records"
python3 "$ROOT/verify_exceptional_classes.py" \
  "$WORK/GENTOURNG_EXCEPTIONAL_CLASSES.generated.jsonl" \
  > "$WORK/GENTOURNG_EXCEPTIONAL_VERIFICATION.generated.json"
cmp "$ROOT/GENTOURNG_EXCEPTIONAL_VERIFICATION.json" \
  "$WORK/GENTOURNG_EXCEPTIONAL_VERIFICATION.generated.json"

echo "[7/8] Compare summaries and canonical exceptional isomorphism classes"
python3 "$ROOT/compare_enumeration_results.py" \
  "$ROOT/RESULTS.json" "$WORK/GENTOURNG_RESULTS.generated.json" \
  > "$WORK/GENTOURNG_COMPARISON.generated.json"
cmp "$ROOT/GENTOURNG_COMPARISON.json" \
  "$WORK/GENTOURNG_COMPARISON.generated.json"
python3 "$ROOT/compare_exception_sets.py" \
  "$ROOT/EXCEPTIONAL_CLASSES.jsonl" \
  "$WORK/GENTOURNG_EXCEPTIONAL_CLASSES.generated.jsonl" \
  --labelg "$SOURCE/labelg" \
  > "$WORK/EXCEPTION_SET_COMPARISON.generated.json"
cmp "$ROOT/EXCEPTION_SET_COMPARISON.json" \
  "$WORK/EXCEPTION_SET_COMPARISON.generated.json"

echo "[8/8] SUCCESS"
echo "generated=1495297 distribution=11:13,12:48,13:1495236"
