#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

SOURCE_DIR="${1:-${LILIM_SOURCE_DIR:-}}"
ITERATIONS="${LILIM_ITERATIONS:-100}"
PYVRP_RUNTIME="${LILIM_PYVRP_RUNTIME:-2.5}"
if [[ -z "${SOURCE_DIR}" ]]; then
  echo "Usage: bash scripts/run_lilim_100_pipeline.sh <path-to-pdptw-data/100>" >&2
  exit 1
fi

python scripts/import_lilim_100.py \
  --source-dir "${SOURCE_DIR}" \
  --output-dir instances/li_lim_100 \
  --reference-dir results/li_lim_100/reference

python scripts/solve_lilim_100_with_pyvrp.py \
  --instances-dir instances/li_lim_100 \
  --output-dir results/li_lim_100/pyvrp \
  --runtime-limit "${PYVRP_RUNTIME}"

cargo run --release -- solve \
  --instances-dir instances/li_lim_100 \
  --output-dir results/li_lim_100/rust \
  --iterations "${ITERATIONS}"

python scripts/compare_lilim_100.py \
  --instances-dir instances/li_lim_100 \
  --reference-dir results/li_lim_100/reference \
  --pyvrp-dir results/li_lim_100/pyvrp \
  --rust-dir results/li_lim_100/rust \
  --output-dir results/li_lim_100/comparison

python scripts/visualize_lilim_100.py \
  --instances-dir instances/li_lim_100 \
  --reference-dir results/li_lim_100/reference \
  --pyvrp-dir results/li_lim_100/pyvrp \
  --rust-dir results/li_lim_100/rust \
  --comparison-summary results/li_lim_100/comparison/summary.json \
  --output-dir results/li_lim_100/visualization
