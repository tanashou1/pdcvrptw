# pdcvrptw

このリポジトリは、**Li-Lim PDPTW 100-case benchmark** を対象に

- ベンチマークインスタンスの import
- `OR-Tools` による strict 解の作成
- Rust ソルバーの実装
- 参照解 / OR-Tools / Rust の比較
- OR-Tools と Rust の直接比較
- 訪問順可視化とスコア比較グラフの生成

を再現するためのものです。

以前の synthetic instance workflow は削除し、今後の評価は Li-Lim に統一しています。

## Li-Lim で使う制約と評価

この実装では Li-Lim benchmark の意味論に合わせて、次を前提に評価します。

- single depot
- pickup-delivery sibling precedence を厳密に適用
- 同一 request の pickup / delivery は同一ルートで処理
- ルート開始時積載量は `0`
- 距離と移動時間は double precision Euclidean
- 目的関数は `min vehicles -> min distance`

つまり、**time windows / capacity / precedence / same-route pairing** をすべて満たしたうえで、まず使用車両数、次に距離を比較します。

## PyVRP について

`PyVRP` の公開 API には Li-Lim の sibling precedence と same-request load transfer をそのまま表現する仕組みがないため、このリポジトリでは **relaxed model** を解いてから strict evaluator で再評価しています。

そのため、

- `PyVRP` の内部モデルでは feasible
- ただし Li-Lim の strict evaluator では infeasible

というケースが発生します。

strict な比較用ベースラインとしては、`OR-Tools` 側で

- `AddPickupAndDelivery`
- same-route pairing
- pickup-before-delivery precedence
- capacity
- time windows

をそのままモデル化しています。

そのため、**公式の結果比較と可視化では PyVRP を除外**し、`reference / OR-Tools / Rust` の 3 者と `OR-Tools vs Rust` の直接比較だけを出力します。`scripts/solve_with_pyvrp.py` は検証用に残していますが、標準パイプラインには含めていません。

## ディレクトリ構成

- `instances/li_lim_100/`: import 済み Li-Lim 100-case instances
- `scripts/import_lilim_100.py`: ベンチマーク import と参照解の正規化
- `scripts/solve_with_ortools.py`: Li-Lim を OR-Tools strict model で解く
- `scripts/solve_with_pyvrp.py`: Li-Lim を PyVRP relaxed model で解く任意の補助スクリプト
- `scripts/compare_results.py`: 参照解 / OR-Tools / Rust の比較と OR-Tools vs Rust 直接比較
- `scripts/visualize_results.py`: Li-Lim の訪問順可視化とスコア比較グラフ
- `scripts/run_pipeline.sh`: import から比較・可視化までの一括実行
- `src/`: Rust ソルバー
- `results/li_lim_100/reference/`: 正規化した参照解
- `results/li_lim_100/ortools/`: OR-Tools strict 解
- `results/li_lim_100/rust/`: Rust 解
- `results/li_lim_100/comparison/`: 比較結果
- `results/li_lim_100/visualization/`: 可視化結果

## 依存関係

- Python 3.12+
- `pyvrp==0.13.3`
- `matplotlib`
- `ortools`
- Rust 1.75+

Python 依存は下記で入ります。

```bash
python -m pip install -r requirements.txt
```

## 実行方法

SINTEF 公開ベンチマークのミラーを手元に用意して、一括実行する場合:

```bash
gh repo clone zhu-he/pdptw-data /tmp/pdptw-data -- --depth 1
bash scripts/run_pipeline.sh /tmp/pdptw-data/100
```

必要なら iteration 数と OR-Tools 実行時間は上書きできます。

```bash
LILIM_ITERATIONS=400 LILIM_ORTOOLS_SECONDS=10.0 \
  bash scripts/run_pipeline.sh /tmp/pdptw-data/100
```

個別に実行する場合:

```bash
python scripts/import_lilim_100.py --source-dir /tmp/pdptw-data/100
python scripts/solve_with_ortools.py
cargo run --release -- solve
python scripts/compare_results.py
python scripts/visualize_results.py
```

PyVRP relaxed 解を個別に確認したい場合だけ、別途

```bash
python scripts/solve_with_pyvrp.py
```

を実行してください。比較レポートには使いません。

`python scripts/solve_with_ortools.py` はデフォルトで `instances/li_lim_100` を読み、`results/li_lim_100/ortools` に strict 解を出力します。

`cargo run --release -- solve` はデフォルトで `instances/li_lim_100` を読み、`results/li_lim_100/rust` に出力します。

## Rust 実装の方針

- 小さな関数に分割
- struct で責務分離
- 貪欲法による初期解構築
- ALNS による改善
- Li-Lim では request pair 単位の destroy / repair を使用
- 訪問ノード数が 20 以下のルートは、subset × last の exact DP で順序を定期的に polish

## 出力

- 比較サマリ: `results/li_lim_100/comparison/summary.md`
- 比較 JSON/CSV: `results/li_lim_100/comparison/summary.{json,csv}`
- 訪問順可視化: `results/li_lim_100/visualization/instances/*.png`
- スコア比較グラフ: `results/li_lim_100/visualization/score_comparison.png`

集計結果は `results/li_lim_100/comparison/summary.md` に、`OR-Tools` と `Rust` の strict feasibility / 使用車両数 / 距離ギャップに加えて、`OR-Tools vs Rust` の直接比較もまとまります。
