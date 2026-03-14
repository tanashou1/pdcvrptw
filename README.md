# pdcvrptw

Pickup and Delivery Capacitated Vehicle Routing Problem with Time Window を題材に、

- `instances/` の生成
- `PyVRP` によるベンチマーク解の作成
- Rust ソルバーの実装
- 両者の結果比較

を一通り再現できるリポジトリです。

## 問題設定

- 10 instances
- 稼働時間は 8:00 - 18:00
- 時間枠は `morning` / `afternoon` / `none` の 3 種類で、大部分は `none`
- 50 requests = 100 service nodes
- ノードの位置は 20 か所の location catalog から選択
- 移動コストはユークリッド距離の整数丸め
- キャパシティは 6
- トラック数は所与
- マルチデポ

## この実装で扱うバリアント

PyVRP と Rust を同一条件で比較するため、各 request は

- `pickup` ノード 1 個
- `delivery` ノード 1 個

で表現し、容量評価は signed-demand 方式で行います。

- `pickup` は正の需要
- `delivery` は負の需要
- ルート開始時積載量は、そのルート内の全 `delivery` 需要の合計

とし、容量制約と時間枠制約を両ソルバで同じ評価器に通して比較します。

注: PyVRP の公開 API に明示的な pickup-delivery pair 制約が見当たらないため、本リポジトリでは pair precedence ではなく benchmark-compatible な multi-depot signed-demand PDCVRPTW として整理しています。

## ディレクトリ構成

- `instances/`: 生成済みの 10 インスタンス
- `scripts/generate_instances.py`: インスタンス生成
- `scripts/solve_with_pyvrp.py`: PyVRP での解生成
- `scripts/compare_results.py`: 共通評価器による比較
- `scripts/visualize_results.py`: 訪問可視化とスコア棒グラフの生成
- `scripts/import_lilim_100.py`: Li-Lim 100-case の import と参照解の正規化
- `scripts/solve_lilim_100_with_pyvrp.py`: Li-Lim 100-case を PyVRP の緩和モデルで解く
- `scripts/compare_lilim_100.py`: Li-Lim 参照解、PyVRP、Rust の 3 者比較
- `scripts/visualize_lilim_100.py`: Li-Lim の訪問順可視化
- `src/`: Rust ソルバー
- `results/pyvrp/`: PyVRP の解
- `results/rust/`: Rust の解
- `results/comparison/`: 比較結果
- `results/visualization/`: ルート可視化と棒グラフ
- `results/li_lim_100/`: Li-Lim 100-case の参照解、PyVRP 解、Rust 解、比較結果、可視化

## 依存関係

- Python 3.12+
- `pyvrp==0.13.3`
- `matplotlib`
- Rust 1.75+

Python 依存は下記で入ります。

```bash
python -m pip install -r requirements.txt
```

## 実行方法

インスタンス生成から比較までを一気に回す場合:

```bash
bash scripts/run_pipeline.sh
```

個別に実行する場合:

```bash
python scripts/generate_instances.py --output-dir instances
python scripts/solve_with_pyvrp.py --instances-dir instances --output-dir results/pyvrp
cargo run --release -- solve --instances-dir instances --output-dir results/rust
python scripts/compare_results.py --instances-dir instances --pyvrp-dir results/pyvrp --rust-dir results/rust --output-dir results/comparison
python scripts/visualize_results.py --instances-dir instances --pyvrp-dir results/pyvrp --rust-dir results/rust --comparison-summary results/comparison/summary.json --output-dir results/visualization
```

## Rust 実装の方針

- 小さな関数に分割
- struct で責務分離
- 貪欲法による初期解構築
- ALNS による改善
- 挿入・削除候補の距離差分評価による高速化

`results/comparison/summary.md` に比較サマリ、`results/visualization/route_visits_overview.png` に全インスタンス訪問可視化、`results/visualization/score_comparison.png` にスコア比較棒グラフが出力されます。

## Li-Lim 100-case benchmark

Li-Lim benchmark は synthetic instance と意味論が異なります。

- single depot
- pickup-delivery sibling precedence を厳密に適用
- ルート開始時積載量は 0
- 距離と移動時間は double precision Euclidean
- 目的関数は `min vehicles -> min distance`

`PyVRP` の公開 API には Li-Lim の sibling precedence と same-request load transfer をそのまま表現する仕組みがないため、Li-Lim では緩和モデルを解いてから strict evaluator で再評価します。したがって、`PyVRP` は自身のモデルでは feasible でも、Li-Lim の厳密評価では infeasible になる場合があります。

データは SINTEF 公開ベンチマークのミラーを使って取得できます。たとえば:

```bash
gh repo clone zhu-he/pdptw-data /tmp/pdptw-data -- --depth 1
bash scripts/run_lilim_100_pipeline.sh /tmp/pdptw-data/100
```

必要なら iteration 数は `LILIM_ITERATIONS=400`、PyVRP 実行時間は `LILIM_PYVRP_RUNTIME=5.0` のように上書きできます。

個別に実行する場合:

```bash
python scripts/import_lilim_100.py --source-dir /tmp/pdptw-data/100 --output-dir instances/li_lim_100 --reference-dir results/li_lim_100/reference
python scripts/solve_lilim_100_with_pyvrp.py --instances-dir instances/li_lim_100 --output-dir results/li_lim_100/pyvrp --runtime-limit 2.5
cargo run --release -- solve --instances-dir instances/li_lim_100 --output-dir results/li_lim_100/rust --iterations 100
python scripts/compare_lilim_100.py --instances-dir instances/li_lim_100 --reference-dir results/li_lim_100/reference --pyvrp-dir results/li_lim_100/pyvrp --rust-dir results/li_lim_100/rust --output-dir results/li_lim_100/comparison
python scripts/visualize_lilim_100.py --instances-dir instances/li_lim_100 --reference-dir results/li_lim_100/reference --pyvrp-dir results/li_lim_100/pyvrp --rust-dir results/li_lim_100/rust --comparison-summary results/li_lim_100/comparison/summary.json --output-dir results/li_lim_100/visualization
```

比較サマリは `results/li_lim_100/comparison/summary.md`、訪問順可視化は `results/li_lim_100/visualization/instances/*.png` に出力されます。
