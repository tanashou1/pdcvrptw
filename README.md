# pdcvrptw
Pickup and Delivery Capacitated Vehicle Routing Problem with Time Windowのrust実装です。
下記を含みます。
- instances
  - 10 instances
  - 8:00 - 18:00を想定
  - 時間枠は、午前、午後、無し、の大雑把な括り。大部分は無し
  - 50リクエスト（100ノード）
  - ノードの位置は20か所から選ばれる
  - 移動コストはユークリッド距離
  - キャパシティは6
  - トラック数は所与
  - マルチデポ
- ベンチマーク相手としてのpyvrp
  - ベンチマーク回答を出すためにのみ使用
- rustによるソルバー
  - 貪欲法による初期解構築
  - ALNSによる解の改善
  - 差分評価による高速化
  - キャパシティの判定や目的関数を関数で与えられるようにするなど、高いカスタマイズ性

rust実装は、関数型に寄せて書き、意味のある単位で関数を細かく分ける。structを多用して責務を分け、変更容易性を保つ。
rust api guidlinesに従う