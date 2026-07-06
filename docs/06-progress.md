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

## 2026-07-07 棋桜サンプルスクリーンショット確認・OBS連携方針

### 実装した内容

- `docs/sample-screenshot/sample01.png` / `sample02.png` の表示レイアウトを確認
- 2064×1112の棋桜ウィンドウ向け盤面キャリブレーション雛形を追加
- Windowsのウィンドウタイトル `KIOU` から1フレーム保存する `capture-window` CLIを追加
- OBSは画面入力元ではなく、棋桜映像とKifuscopeオーバーレイの合成先として扱う方針をREADMEと設計文書へ追記

### 変更したファイル

- `src/kiou_eval/recognizer/capture.py`
- `src/kiou_eval/recognizer/__init__.py`
- `src/kiou_eval/__main__.py`
- `samples/calibration.kiou-2064x1112.example.json`
- `README.md`
- `docs/04-screen-recognition.md`
- `docs/05-obs-overlay.md`
- `docs/06-progress.md`

### 動作確認方法

```bash
uv run python -m kiou_eval capture-window --title KIOU --output captures/kiou.png
uv run pytest
uv run ruff check .
```

### 未解決の問題

- `capture-window` はWindows専用のため、このLinux環境では実ウィンドウ取得を未確認
- サンプル2枚は正解SFENが未確定のため、テンプレート生成には未使用
- 持ち駒欄と手番欄のキャリブレーションは追加調整が必要

### 次にやること

Windows実機でMVP 1・2を統合試験し、その後に棋桜スクリーンショットを用いたMVP 3のクロップ・テンプレート設計へ進む。

## 2026-07-07 盤面主入力・合法手追跡による手番/持ち駒補正

### 実装した内容

- 持ち駒欄・手番欄が未設定でも、盤面81マスが確定した場合は `board_observed` として扱うよう変更
- `recognize-image` の `board_observed` を正常終了扱いに変更
- `StableLegalTracker` が盤面だけの観測から合法手後局面を確定できることを単体テストで確認
- `sample06.png` から生成した初期局面テンプレートで、初期局面と矢印付き初期局面の盤面追跡を確認

### 変更したファイル

- `src/kiou_eval/shogi/board_state.py`
- `src/kiou_eval/recognizer/board_recognizer.py`
- `src/kiou_eval/__main__.py`
- `tests/test_recognizer.py`
- `tests/test_legal_tracker.py`
- `README.md`
- `docs/04-screen-recognition.md`
- `docs/06-progress.md`

### 動作確認

```bash
uv run python -m kiou_eval recognize-image docs/sample-screenshot/sample06.png \
  --calibration samples/calibration.kiou-2064x1112.example.json \
  --templates templates/kiou-initial

uv run python -m kiou_eval track-images \
  docs/sample-screenshot/sample06.png docs/sample-screenshot/sample04.png \
  --calibration samples/calibration.kiou-2064x1112.example.json \
  --templates templates/kiou-initial
```

### テスト結果

- `uv run pytest -q`: 33件成功
- `uv run ruff check .`: 成功

### 未解決の問題

- 連続対局フレームから1手ずつ追跡する実運用テストが必要
- 成駒を含む局面は、成駒テンプレートを正解SFEN付き画像から追加する必要がある
- 持ち駒欄を画像認識する場合は別途キャリブレーションが必要だが、初期運用では合法手追跡で補正する

## 2026-07-07 MVP 5リアルタイム運用基礎

### 実装した内容

- `RealtimeEvaluator` を追加し、キャプチャ、盤面認識、合法手追跡、評価配信を1つの非同期ループに統合
- キャプチャ元として `window`、`monitor`、`images` を選択可能にした
- Windows実運用向けに `KIOU` ウィンドウを直接キャプチャする `serve-realtime` CLIを追加
- Linux検証向けに画像列を使ったリアルタイムループを追加
- 確定した新しいSFENだけ評価要求を出し、評価中に新局面が来た場合はYaneuraOuへ `stop` を送る構成にした
- 認識失敗、局面未確定、評価中、評価完了を `EvaluationHub` 経由でOBSオーバーレイへ配信するようにした

### 変更したファイル

- `src/kiou_eval/runtime/__init__.py`
- `src/kiou_eval/runtime/realtime.py`
- `src/kiou_eval/server/app.py`
- `src/kiou_eval/__main__.py`
- `README.md`
- `docs/02-architecture.md`
- `docs/05-obs-overlay.md`
- `docs/06-progress.md`

### 動作確認

画像列入力・評価なしでサーバー起動し、`/api/eval` が初期局面を返すことを確認。

```bash
uv run python -m kiou_eval serve-realtime \
  --source images \
  --images docs/sample-screenshot/sample06.png docs/sample-screenshot/sample04.png \
  --calibration samples/calibration.kiou-2064x1112.example.json \
  --templates templates/kiou-initial \
  --no-evaluate
```

画像列入力・YaneuraOu評価込みで、初期局面の評価値、最善手、PVを `/api/eval` から取得できることを確認。

### テスト結果

- `uv run pytest -q`: 33件成功
- `uv run ruff check .`: 成功
- Linux NNUE版YaneuraOuでリアルタイム経路から評価成功

### 未解決の問題

- Windows実機で `serve-realtime --source window --window-title KIOU` の統合試験が必要
- 実対局の連続フレームで、1手ずつ追跡できるかの評価が必要
- 成駒・持ち駒が出る局面では追加テンプレートが必要
- 手動補正UIは未実装

## 2026-07-07 Windows起動要件と最善手日本語表記

### 実装・文書化した内容

- `bestmove_japanese` と `pv_japanese` を評価JSONへ追加
- オーバーレイで `bestmove_japanese` を優先表示するよう変更
- `▲7六歩`、`△3四歩`、`▲5五角打`、`▲2二角成` のような日本語指し手表記を追加
- `--source window --window-title KIOU` はWindows APIを使うため、KifuscopeをWindows側で起動する必要があることをREADMEと設計文書へ明記
- WSL Ubuntuは開発・テスト・画像列検証用であり、WindowsアプリのKIOUウィンドウ直接取得には使わない方針を明記

### 変更したファイル

- `src/kiou_eval/shogi/move_notation.py`
- `src/kiou_eval/engine/eval_result.py`
- `src/kiou_eval/engine/yaneuraou_client.py`
- `src/kiou_eval/server/schemas.py`
- `src/kiou_eval/overlay/overlay.js`
- `tests/test_move_notation.py`
- `README.md`
- `docs/04-screen-recognition.md`
- `docs/05-obs-overlay.md`
- `docs/06-progress.md`

### テスト結果

- `uv run pytest -q`: 38件成功
- `uv run ruff check .`: 成功

## 2026-07-07 ふかうら王TensorRT対応

### 実装・文書化した内容

- `usi` 応答中の `option name ...` を収集し、エンジンが宣言したUSIオプションだけ `setoption` するよう変更
- `Threads`、`USI_Hash`、`MultiPV` が未対応のエンジンでは自動スキップするよう変更
- `YANEAURAOU_EXTRA_OPTIONS` を追加し、TensorRT版などのエンジン固有USIオプションを `Name=Value;Name2=Value2` 形式で指定可能にした
- Windows版ふかうら王TensorRTの設定例と、公式Wiki/Releaseへの参考リンクをREADMEとUSI文書へ追加

### 変更したファイル

- `src/kiou_eval/config.py`
- `src/kiou_eval/engine/yaneuraou_client.py`
- `tests/test_yaneuraou_client.py`
- `README.md`
- `docs/03-usi-yaneuraou.md`
- `docs/06-progress.md`

### テスト結果

- `uv run pytest -q tests/test_yaneuraou_client.py`: 5件成功
