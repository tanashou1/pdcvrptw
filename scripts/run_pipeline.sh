#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

SOURCE_DIR="${1:-${LILIM_SOURCE_DIR:-}}"
ITERATIONS="${LILIM_ITERATIONS:-100}"
ORTOOLS_SECONDS="${LILIM_ORTOOLS_SECONDS:-5.0}"

if [[ -z "${SOURCE_DIR}" ]]; then
  echo "Usage: bash scripts/run_pipeline.sh <path-to-pdptw-data/100>" >&2
  exit 1
fi

python scripts/import_lilim_100.py \
  --source-dir "${SOURCE_DIR}" \
  --output-dir instances/li_lim_100 \
  --reference-dir results/li_lim_100/reference

python scripts/solve_with_ortools.py \
  --instances-dir instances/li_lim_100 \
  --output-dir results/li_lim_100/ortools \
  --time-limit-seconds "${ORTOOLS_SECONDS}"

cargo run --release -- solve \
  --instances-dir instances/li_lim_100 \
  --output-dir results/li_lim_100/rust \
  --iterations "${ITERATIONS}"

python scripts/compare_results.py \
  --instances-dir instances/li_lim_100 \
  --reference-dir results/li_lim_100/reference \
  --ortools-dir results/li_lim_100/ortools \
  --rust-dir results/li_lim_100/rust \
  --output-dir results/li_lim_100/comparison

python scripts/visualize_results.py \
  --instances-dir instances/li_lim_100 \
  --reference-dir results/li_lim_100/reference \
  --ortools-dir results/li_lim_100/ortools \
  --rust-dir results/li_lim_100/rust \
  --comparison-summary results/li_lim_100/comparison/summary.json \
  --output-dir results/li_lim_100/visualization
