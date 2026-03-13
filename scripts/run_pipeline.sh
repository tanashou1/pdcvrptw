#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python scripts/generate_instances.py --output-dir instances
python scripts/solve_with_pyvrp.py --instances-dir instances --output-dir results/pyvrp
cargo run --release -- solve --instances-dir instances --output-dir results/rust
python scripts/compare_results.py --instances-dir instances --pyvrp-dir results/pyvrp --rust-dir results/rust --output-dir results/comparison
python scripts/visualize_results.py --instances-dir instances --pyvrp-dir results/pyvrp --rust-dir results/rust --comparison-summary results/comparison/summary.json --output-dir results/visualization
