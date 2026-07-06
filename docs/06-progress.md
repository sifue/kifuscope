# 進捗報告

## 2026-07-06

### 実装した内容

- uv対応のPythonプロジェクト骨格と設定読み込み
- SFEN構文検証、USI `info` パーサー、先手視点正規化
- YaneuraOu起動・初期化・評価・終了処理
- `check-engine`、`analyze-sfen`、`serve`、`demo-overlay` CLI
- FastAPIの最新評価API、評価API、WebSocket配信
- OBS用形勢バー・評価値・最善手・状態表示
- エンジン不要の単体テストと偽USIエンジンによるプロセス試験

### 主な変更ファイル

`pyproject.toml`、`src/kiou_eval/`、`tests/`、`README.md`、`docs/`、`samples/sfens.txt`

### 動作確認方法

```bash
uv sync
uv run pytest
uv run ruff check .
uv run python -m kiou_eval demo-overlay
```

実エンジンの確認はWindowsで `uv run python -m kiou_eval check-engine` と `analyze-sfen` を実行する。

### テスト結果

- `uv run pytest -q`: 20件成功
- `uv run ruff check .`: 成功
- `uv build`: sdistとwheelの生成に成功（オーバーレイ静的ファイルの包含を確認）
- `demo-overlay`: 実プロセスで起動し、`/overlay`、`/api/eval`、OpenAPIをHTTP確認済み

### 未解決の問題

- 実際のYaneuraOu Deep構成を使ったWindows統合試験が必要
- USIの不定手数詰み表記を返すエンジン構成では追加の表示確認が必要
- 棋譜表記への変換は未実装で、最善手はUSI表記
- 画像認識は未実装

## 2026-07-06 Linux実エンジン統合確認

- `/home/sifue/Apps/yaneuraou/YaneuraOuNNUE` はUSI応答を確認したが、対応する `eval/nn.bin` が未配置のため `isready` で終了することを確認
- 同じソースからAVX2向けMaterial Level 1版をビルド
- `.env.local` にMaterial版の外部パスを設定
- `check-engine`、初期局面の500ms評価、MultiPV 3本の取得に成功
- FastAPIの `POST /api/analyze` と `GET /api/eval` を実エンジンで確認
- 評価関数欠落などを診断しやすいよう、異常終了時にエンジン末尾出力を報告するよう改善

## 2026-07-06 Linux NNUE版統合確認

- `/home/sifue/Apps/yaneuraou/eval/nn.bin`（約62MB）の配置を確認
- `.env.local` の既定エンジンを `/home/sifue/Apps/yaneuraou/YaneuraOuNNUE` へ切り替え
- NNUE評価関数の読み込み、`check-engine`、500msの初期局面評価に成功
- CLIで深さ19、MultiPV 3本、最善手を取得
- FastAPIの `POST /api/analyze` でもNNUE評価に成功
- 切り替え後も単体テスト20件とruffが成功

## 2026-07-06 MVP 3・MVP 4

### 実装した内容

- JSONキャリブレーションによる盤面・持ち駒・手番領域設定
- 9×9グリッド分割と先手/後手、成駒、空マスのテンプレート照合
- 180度回転盤面への対応
- 既知SFEN画像からのテンプレート自動生成
- `BoardObservation` と検証済み `BoardState` の分離
- 王、二歩、駒数、cshogiによる局面検証
- 前局面と全合法手後局面の画像一致率比較
- 候補閾値、2位候補との差、連続安定フレームによる誤確定防止
- 持ち駒増減と手番を含む合法手追跡
- `recognize-image`、`track-images`、`build-templates` CLI
- 安定局面だけを評価する `track-images --evaluate`

### 変更した主なファイル

- `src/kiou_eval/recognizer/`
- `src/kiou_eval/shogi/board_state.py`
- `src/kiou_eval/shogi/legal_tracker.py`
- `tests/test_board_state.py`
- `tests/test_recognizer.py`
- `tests/test_legal_tracker.py`
- `samples/calibration.example.json`

### 動作確認

- 合成棋桜相当画像による81マス、持ち駒、手番の一括認識
- 既知局面から生成したテンプレートでの再認識
- 初期局面から▲7六歩への合法手追跡と2フレーム安定化
- 単体テスト32件成功
- `uv run ruff check .` 成功
- `uv build` でバージョン0.2.0のsdist・wheel生成に成功
- cshogi局面検証を経由したLinux NNUE版の実探索に成功

### 未解決の問題

- 棋桜の実スクリーンショットが未提供のため、実座標と実駒テンプレートは未調整
- テンプレート照合の実画像精度、閾値、照明・拡大率変動への耐性は実データ評価が必要
- リアルタイム連続キャプチャとOBSへの自動評価配信はMVP 5の対象

### 次にやること

棋桜の初期局面、先後の手番、持ち駒、成駒を含むスクリーンショットでテンプレートを構築し、誤認識率と合法手追跡成功率を測定する。

### 次にやること

Windows実機でMVP 1・2を統合試験し、その後に棋桜スクリーンショットを用いたMVP 3のクロップ・テンプレート設計へ進む。
