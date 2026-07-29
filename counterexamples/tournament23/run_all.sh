#!/usr/bin/env bash
set -euo pipefail

package_dir="$(cd "$(dirname "$0")" && pwd)"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

cd "$package_dir"
sha256sum -c SHA256SUMS.txt

python3 src/verify.py data/adjacency_matrix.txt \
  --output "$work_dir/python_verification.json" \
  >"$work_dir/python.log"
cmp "$work_dir/python_verification.json" data/full_verification.json

g++ -O3 -std=c++17 -Wall -Wextra -Wpedantic -Werror \
  src/verify.cpp -o "$work_dir/verify"
"$work_dir/verify" data/adjacency_matrix.txt >"$work_dir/cpp.log"
grep -Fxq 'order=23 strong_vertices=0 verified=true' \
  "$work_dir/cpp.log"

echo "order=23 strong_vertices=0 verified=true"
