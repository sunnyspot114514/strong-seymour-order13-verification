#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD="$ROOT/build"
WORK="$ROOT/work"
rm -rf "$BUILD" "$WORK"
mkdir -p "$BUILD" "$WORK"

python3 "$ROOT/src/verify.py" > "$WORK/python_verification.json"
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic -Werror \
  "$ROOT/src/verify.cpp" -o "$BUILD/verify"
"$BUILD/verify" > "$WORK/cpp_verification.out" \
  2> "$WORK/cpp_verification.log"
python3 "$ROOT/audit/independent_audit.py" \
  > "$WORK/independent_audit.json"

(
  cd "$ROOT"
  sha256sum -c SHA256SUMS.txt
)
cat "$WORK/cpp_verification.out"
