# Kifuscope

棋桜の画面から得た将棋局面をYaneuraOuで評価し、配信・実況用のOBS Browser Sourceへ表示するローカルツールです。MVP 1〜4として、SFEN評価、Web API・オーバーレイ、静止画像テンプレート認識、前局面からの合法手追跡を実装しています。

## 注意事項

本ツールは配信者・実況者・解説者の支援専用です。対局者がリアルタイムの評価値や最善手を閲覧できる環境では使用しないでください。棋桜の通信や内部APIにはアクセスせず、将来も画面キャプチャだけを入力とします。

## 動作環境とセットアップ

- Python 3.11以上
- uv
- ローカルにインストールしたYaneuraOu
- OBS Studio（オーバーレイ利用時）

```bash
uv sync
```

YaneuraOu本体、DLL、評価モデルはリポジトリへコピーしません。外部に配置したエンジンを `.env.local` で指定します。設定の優先順位は、CLI引数、環境変数、`.env.local`、`.env`、既定値です。

### 推奨: まずWindows CPU版で接続確認する

最初はDeep ORT CPU版で `check-engine` と `analyze-sfen` を通してください。CPU版で通れば、Kifuscope本体、USI通信、モデル配置の基本経路が正常だと判断できます。その後にTensorRT版へ切り替えると、GPU/DLL/TensorRT初回最適化の問題を分離できます。

`.env.local` 例:

```dotenv
YANEAURAOU_ENGINE_PATH=C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\YaneuraOu-Deep-ORT-CPU.exe
YANEAURAOU_THREADS=0
YANEAURAOU_HASH_MB=1024
YANEAURAOU_MULTIPV=3
YANEAURAOU_MOVETIME_MS=500
YANEAURAOU_COMMAND_TIMEOUT_SEC=60
YANEAURAOU_EXTRA_OPTIONS=
SERVER_HOST=127.0.0.1
SERVER_PORT=8765
```

Deep系エンジンは `Threads` USIオプションを持たない場合があるため、Windowsでは `YANEAURAOU_THREADS=0` を基本にします。`0` の場合、Kifuscopeは `setoption name Threads ...` を送信しません。通常のYaneuraOuなどでThreadsを使いたい場合だけ `YANEAURAOU_THREADS=4` のように明示してください。

CPU版の配置例:

```text
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\
  YaneuraOu-Deep-ORT-CPU.exe
  onnxruntime.dll
  onnxruntime_providers_shared.dll
  eval\
    model.onnx
    model.onnx.ini
```

`model.onnx` はdlshogiの公開モデルを取得して配置します。例として、DeepLearningShogiの `dr2_exhi` Releaseから `model-dr2_exhi.zip` を取得し、展開後のファイルを次のようにリネームします。ライセンスは配布元で確認してください。

```text
model-dr2_exhi.onnx      -> C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\eval\model.onnx
model-dr2_exhi.onnx.ini  -> C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\eval\model.onnx.ini
```

確認:

```powershell
Test-Path C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\eval\model.onnx
Test-Path C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\onnxruntime.dll
Test-Path C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\onnxruntime_providers_shared.dll
uv run python -m kiou_eval check-engine
```

参考:

- [DeepLearningShogi dr2_exhi Release](https://github.com/TadaoYamaoka/DeepLearningShogi/releases/tag/dr2_exhi)
- [dlshogi Windows版ビルド済みファイル公開 - TadaoYamaokaの日記](https://tadaoyamaoka.hatenablog.com/entry/2021/08/17/000710)

### GPU版: ふかうら王TensorRT

CPU版で接続確認できた後に、TensorRT版へ切り替えます。

`.env.local` 例:

```dotenv
YANEAURAOU_ENGINE_PATH=C:\Apps\YaneuraOu-Deep-TensorRT_V940\YaneuraOu-Deep-TensorRT.exe
YANEAURAOU_THREADS=0
YANEAURAOU_HASH_MB=1024
YANEAURAOU_MULTIPV=3
YANEAURAOU_MOVETIME_MS=300
YANEAURAOU_COMMAND_TIMEOUT_SEC=180
YANEAURAOU_EXTRA_OPTIONS=
SERVER_HOST=127.0.0.1
SERVER_PORT=8765
```

TensorRT版はNVIDIA GPU向けです。CUDA/TensorRT/cuDNN DLL、評価モデル、NVIDIAドライバーの組み合わせが合っている必要があります。公式配布物のフォルダ構成を崩さず、エンジン本体、同梱DLL、`eval/` を同じ配布フォルダ内に置く構成を推奨します。初回起動やモデル最適化では `isready` 応答まで時間がかかることがあるため、`YANEAURAOU_COMMAND_TIMEOUT_SEC=180` 以上を使います。

TensorRT版固有のUSIオプションを渡す場合は `;` 区切りで指定できます。指定した名前がエンジン側に存在しない場合は送信せずスキップします。

```dotenv
YANEAURAOU_EXTRA_OPTIONS=SomeOption=Value;AnotherOption=123
```

参考:

- [ふかうら王のインストール手順 - yaneurao/YaneuraOu Wiki](https://github.com/yaneurao/YaneuraOu/wiki/%E3%81%B5%E3%81%8B%E3%81%86%E3%82%89%E7%8E%8B%E3%81%AE%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB%E6%89%8B%E9%A0%86)
- [YaneuraOu Releases - GitHub](https://github.com/yaneurao/YaneuraOu/releases)
- [ふかうら王のビルド手順 - yaneurao/YaneuraOu Wiki](https://github.com/yaneurao/YaneuraOu/wiki/%E3%81%B5%E3%81%8B%E3%81%86%E3%82%89%E7%8E%8B%E3%81%AE%E3%83%93%E3%83%AB%E3%83%89%E6%89%8B%E9%A0%86)

### Linux NNUE版

Linuxでは、エンジンをリポジトリ外へ配置して実行権限を付けます。NNUE版では通常、実行ファイルの親ディレクトリ以下に `eval/nn.bin` が必要です。

```bash
chmod +x /home/user/Apps/yaneuraou/YaneuraOu
```

```dotenv
YANEAURAOU_ENGINE_PATH=/home/user/Apps/yaneuraou/YaneuraOu
YANEAURAOU_THREADS=4
```

## 使い方

接続確認:

```bash
uv run python -m kiou_eval check-engine
```

SFEN評価:

```bash
uv run python -m kiou_eval analyze-sfen "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
```

サーバー起動:

```bash
uv run python -m kiou_eval serve
```

- オーバーレイ: `http://127.0.0.1:8765/overlay`
- 現在値API: `GET http://127.0.0.1:8765/api/eval`
- SFEN評価API: `POST http://127.0.0.1:8765/api/analyze`
- API仕様: `http://127.0.0.1:8765/docs`

エンジンなしで表示確認する場合:

```bash
uv run python -m kiou_eval demo-overlay
```

OBSの「ブラウザ」ソースへ `http://127.0.0.1:8765/overlay` を登録し、幅520、高さ220程度を指定します。対局者用画面にはこのソースを配置しないでください。

リアルタイム認識・評価込みで起動する場合は、後述のWindows用コマンドを使います。Windows上では、表示中の `KIOU` ウィンドウを直接キャプチャします。OBSは同じ `KIOU` ウィンドウを「ウィンドウキャプチャ」で取り込み、Kifuscopeの `/overlay` を「ブラウザ」ソースで重ねます。

重要: `--source window --window-title KIOU` はWindows APIでウィンドウを取得するため、KifuscopeもWindows側で起動する必要があります。WSL Ubuntu上で実行したKifuscopeからは、通常のWindowsアプリである棋桜のウィンドウを直接取得できません。

Windowsでの最小起動手順は次の通りです。

1. 棋桜を起動し、ウィンドウタイトルが `KIOU` になっていることを確認する
2. 初期局面で、駒選択・白矢印・黄色枠が出ていない状態にする
3. KIOUウィンドウを最小化せず、画面上に表示しておく
4. 初回だけ、スクリーンショットを保存してテンプレートを生成する
5. Kifuscopeをリアルタイム起動する

GitHubからチェックアウトした直後は `templates/kiou-initial` が存在しません。テンプレートは環境ごとの画面サイズ・テーマに依存する生成物なので、Git管理していません。初回だけ次を実行してください。

```powershell
uv run python -m kiou_eval capture-window --title KIOU --output captures/kiou-initial.png
```

続けて、初期局面SFENから盤面テンプレートを生成します。

```powershell
uv run python -m kiou_eval build-templates captures/kiou-initial.png --sfen "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1" --calibration samples/calibration.kiou-2064x1112.example.json --output templates/kiou-initial
```

認識確認:

```powershell
uv run python -m kiou_eval recognize-image captures/kiou-initial.png --calibration samples/calibration.kiou-2064x1112.example.json --templates templates/kiou-initial
```

`status` が `board_observed` または `ok` なら、リアルタイム起動へ進めます。

重要: `serve-realtime` は、既定では初期局面SFENから合法手を1手ずつ追跡します。そのため、起動時点のKIOU画面がすでに対局途中まで進んでいると、初期局面にも1手後の合法局面にも一致せず `recognition_failed` になります。CPU対局では、対局開始前または初期局面で一時停止している状態で `serve-realtime` を起動してください。

PowerShellで複数行に分ける場合、行末はバックスラッシュ `\` ではなくバッククォート `` ` `` です。コピーミスを避けるなら、まず1行版を使ってください。

```powershell
uv run python -m kiou_eval serve-realtime --calibration samples/calibration.kiou-2064x1112.example.json --templates templates/kiou-initial --source window --window-title KIOU
```

PowerShellで複数行に分ける場合:

```powershell
uv run python -m kiou_eval serve-realtime `
  --calibration samples/calibration.kiou-2064x1112.example.json `
  --templates templates/kiou-initial `
  --source window `
  --window-title KIOU
```

コマンドプロンプトの場合:

```cmd
uv run python -m kiou_eval serve-realtime --calibration samples/calibration.kiou-2064x1112.example.json --templates templates/kiou-initial --source window --window-title KIOU
```

起動後、ブラウザで `http://127.0.0.1:8765/overlay` を開いて表示確認します。OBSには同じURLを Browser Source として登録します。

画面が「評価待ち」のまま変わらない場合は、別のPowerShellで現在状態を確認します。

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/eval | ConvertTo-Json -Depth 10
```

PowerShellの文字化けが残る場合は、Windows標準の `curl.exe` で確認します。

```powershell
curl.exe -s http://127.0.0.1:8765/api/eval
```

切り分け手順:

```powershell
# 1. 評価エンジンを使わず、認識ループだけ確認
uv run python -m kiou_eval serve-realtime --calibration samples/calibration.kiou-2064x1112.example.json --templates templates/kiou-initial --source window --window-title KIOU --no-evaluate

# 2. 別PowerShellで状態確認
Invoke-RestMethod http://127.0.0.1:8765/api/eval | ConvertTo-Json -Depth 10
```

`--no-evaluate` で `status: "ok"` になれば、画面認識と合法手追跡は動いています。その場合はエンジン評価側の問題です。起動直後に `recognition_failed` や `realtime_error` の場合は、表示された `message` に従ってキャプチャ範囲・テンプレート・キャリブレーションを確認します。

一度でも正常な評価値が出た後は、配信画面の安定性を優先し、一時的な `recognition_failed` や `position_unconfirmed` をOBSオーバーレイへ表示しません。直前の評価値・最善手・深さを残し、詳細な失敗内容は `serve-realtime` を起動しているコンソールログへ出力します。盤面上の演出や選択枠で一瞬 `PPPP...` のような極端な誤認識が出ても、配信画面には出さない設計です。

`recognition_failed` のメッセージに `score=0.1` 前後のような低い値が出る場合、現在のKIOU画面が追跡開始局面と大きく違います。まずKIOUを初期局面へ戻してから `serve-realtime` を起動してください。対局途中から開始したい場合は、その局面の正確なSFENを用意し、`--initial-sfen "<SFEN>"` で指定する必要があります。

起動後に追跡状態だけを初期局面へ戻したい場合は、REST APIを使います。

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8765/api/realtime/reset
```

ブラウザから操作したい場合は、操作ボタン付きでオーバーレイを開きます。このURLは確認用です。OBSには通常の `/overlay` を使ってください。

```text
http://127.0.0.1:8765/overlay?controls=1
```

この画面には2つの操作があります。

- `追跡リセット`: Kifuscope内部の追跡状態だけを初期局面へ戻す
- `初期テンプレ再生成`: 現在のKIOU画面を初期局面として既存テンプレートを作り直し、追跡状態も戻す

`初期テンプレ再生成` は、KIOUが初期局面で、駒選択・白矢印・黄色枠が出ていない状態でだけ使ってください。現在画面が対局途中の場合、誤ったテンプレートが作られます。

REST APIで同じことを行う場合:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8765/api/realtime/reset `
  -ContentType "application/json" `
  -Body '{"rebuild_templates":true}'
```

対局途中の局面から追跡を開始したい場合は、正確なSFENを指定してリセットできます。

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8765/api/realtime/reset `
  -ContentType "application/json" `
  -Body '{"initial_sfen":"lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"}'
```

現在のKIOU画面が初期局面なら、指定するSFENは初期局面です。起動時に明示する場合は次のようにします。

```powershell
uv run python -m kiou_eval serve-realtime --initial-sfen "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1" --calibration samples/calibration.kiou-2064x1112.example.json --templates templates/kiou-initial --source window --window-title KIOU
```

起動後に初期局面へ戻す場合:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8765/api/realtime/reset `
  -ContentType "application/json" `
  -Body '{"initial_sfen":"lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"}'
```

PowerShellで日本語メッセージが文字化けする場合は、先にUTF-8へ切り替えます。

```powershell
chcp 65001
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

`recognition_failed` で `confidence` が `0.85`〜`0.90` 程度の場合は、盤面認識は概ね合っているが合法手追跡の閾値に届いていない状態です。`samples/calibration.kiou-2064x1112.example.json` の `legal_match_threshold` を `0.85` 程度に下げて再試行してください。

```json
"legal_match_threshold": 0.85
```

それでも失敗する場合は、起動中のKIOU画面をもう一度保存して単体認識を確認します。

```powershell
uv run python -m kiou_eval capture-window --title KIOU --output captures/kiou-live.png
uv run python -m kiou_eval recognize-image captures/kiou-live.png --calibration samples/calibration.kiou-2064x1112.example.json --templates templates/kiou-initial
```

`recognize-image` の `board_sfen_guess` が初期局面と違う場合、現在のKIOU画面は初期局面ではありません。`serve-realtime` のリセットAPIはKIOU画面自体を戻すものではないため、KIOU側を初期局面に戻すか、`board_sfen_guess` を参考に正確な現在局面SFENを作り、`POST /api/realtime/reset` の `initial_sfen` として指定してください。

KIOUは左右キャラクター、背景、演出で画面全体の色が変化します。Kifuscopeは盤面クロップだけを使うため、盤外のキャラクターや背景は原則として影響しません。一方で、盤面上の光・矢印・選択枠・木目差は認識に影響します。そのため、テンプレート照合ではマス全体ではなく中央領域を主に比較し、グリッド線や端の演出の影響を下げています。根本対策としては、次の順で安定化します。

1. テンプレート生成は、初期局面かつ選択枠・白矢印・黄色枠がない状態で行う
2. KIOUウィンドウサイズと表示倍率を固定する
3. 認識失敗時は `captures/kiou-live.png` を保存し、`board_sfen_guess` を確認する
4. 成駒や別テーマで誤認識する場合は、正解SFEN付き画像からテンプレートを追加する
5. それでも不安定なら、テンプレート方式から「駒文字・駒形状中心のマスク照合」または軽量分類器へ移行する

最善手はUSI表記に加えて、`▲7六歩` のような配信用日本語表記 `bestmove_japanese` も返します。オーバーレイでは日本語表記を優先表示します。

WSL Ubuntuは、開発、単体テスト、Linux版YaneuraOu検証、画像列入力による認識ループ確認に使います。WSLでリアルタイム確認する場合は `--source images` を使ってください。WSLからWindows画面を取得するにはOBS仮想カメラやNDIなど別経路が必要になり、現時点の推奨構成ではありません。

Linuxや開発環境で画像列から同じループを確認する場合:

```bash
uv run python -m kiou_eval serve-realtime \
  --source images \
  --images docs/sample-screenshot/sample06.png docs/sample-screenshot/sample04.png \
  --calibration samples/calibration.kiou-2064x1112.example.json \
  --templates templates/kiou-initial \
  --no-evaluate
```

`--no-evaluate` を外すと、確定局面だけをYaneuraOuへ送って評価値を配信します。新しい確定局面が来た場合は、古い探索へ停止要求を送ります。

## OBSと棋桜画面の連携

OBSからKifuscopeへ画面情報を渡す必要はありません。実運用では、OBSとKifuscopeを次のように分離します。

1. OBSは棋桜の `KIOU` ウィンドウを「ウィンドウキャプチャ」で配信用映像として取り込む
2. Kifuscopeは同じ `KIOU` ウィンドウをWindows APIで直接キャプチャして局面認識する
3. OBSはKifuscopeの `http://127.0.0.1:8765/overlay` を「ブラウザ」ソースとして重ねる

この構成にすると、OBSの内部映像をPythonへ戻すための仮想カメラ、NDI、プラグインが不要になります。

Windowsで `KIOU` ウィンドウを1フレーム保存してキャリブレーション確認するには次を実行します。

```bash
uv run python -m kiou_eval capture-window --title KIOU --output captures/kiou.png
```

ウィンドウタイトルに追加文字が付く環境では部分一致で検索できます。

```bash
uv run python -m kiou_eval capture-window --title KIOU --contains --output captures/kiou.png
```

対象ウィンドウは最小化せず、画面上に表示した状態にしてください。

## 静止画像認識と合法手追跡

最初に `samples/calibration.example.json` をコピーし、実際のスクリーンショットに合わせて盤面、持ち駒枚数、手番表示のピクセル矩形を設定します。サンプル座標は説明用で、そのまま棋桜へ適用できる値ではありません。

今回の `docs/sample-screenshot/sample01.png` / `sample02.png` と同じ 2064×1112 レイアウト向けの盤面雛形は `samples/calibration.kiou-2064x1112.example.json` です。実際のWindows環境で取得した画像と1〜2px単位でずれる可能性があるため、最終的には `capture-window` で保存した画像に合わせて調整してください。

既知局面の画像からテンプレートを生成します。同じ出力先へ異なる局面を追加すると、成駒や持ち駒枚数などのテンプレートを増やせます。

```bash
uv run python -m kiou_eval build-templates samples/screenshots/initial.png \
  --sfen "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1" \
  --calibration calibration.json \
  --output templates/kiou
```

1枚を認識します。

```bash
uv run python -m kiou_eval recognize-image samples/screenshots/position.png \
  --calibration calibration.json \
  --templates templates/kiou
```

持ち駒欄・手番欄をキャリブレーションしていない場合でも、盤面81マスが読めた場合は `status: "board_observed"` を返します。この状態は失敗ではなく、初期局面からの合法手追跡で手番・持ち駒を補正するための入力として使います。

時系列画像を合法手で追跡します。既定では同じ候補が3フレーム連続した場合だけ確定します。`--evaluate` を付けると、確定局面だけをYaneuraOuへ送ります。

```bash
uv run python -m kiou_eval track-images frame01.png frame02.png frame03.png \
  --calibration calibration.json \
  --templates templates/kiou \
  --evaluate
```

盤面が後手側から180度回転して表示される場合は `rotate_board_180` を `true` にします。認識失敗・合法手不一致・安定待ちのフレームは評価されません。

`sample06.png` のような選択枠・矢印なしの初期局面からは、次のように初期テンプレートを作成できます。

```bash
uv run python -m kiou_eval build-templates docs/sample-screenshot/sample06.png \
  --sfen "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1" \
  --calibration samples/calibration.kiou-2064x1112.example.json \
  --output templates/kiou-initial
```

## 開発

```bash
uv run pytest
uv run ruff check .
```

YaneuraOu実体を使う試験は通常の単体テストから分離します。

## トラブルシューティング

- 「YaneuraOuが見つかりません」: `YANEAURAOU_ENGINE_PATH` が `.exe` 本体を指すか確認します。
- 起動直後に終了する: `.exe` と同じディレクトリに必要なDLLと評価関数ファイルがあるか確認します。
- `eval/model.onnx file not found`: Deep ORT CPU版に必要なONNX評価モデルがありません。`C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\eval\model.onnx` を配置します。
- `No such option: Threads`: 使用中のエンジンが `Threads` オプション非対応です。`.env.local` に `YANEAURAOU_THREADS=0` を設定します。
- TensorRT版で `YaneuraOuからの応答がタイムアウトしました`: 初回最適化やGPU初期化に時間がかかっている可能性があります。まずCPU版で接続確認し、TensorRT版では `YANEAURAOU_COMMAND_TIMEOUT_SEC=180` 以上を試します。
- TensorRT版が起動しない: NVIDIA GPU、NVIDIAドライバー、CUDA/TensorRT/cuDNNのバージョン、`eval/*.model`、DLL配置を確認します。配布版では同梱DLLをエンジン本体と同じフォルダに置く構成を優先します。
- OBSが更新されない: サーバーが起動中か、OBSのURLとポートが一致するか確認します。
- 画像を認識できない: 画面解像度と拡大率をテンプレート作成時に揃え、キャリブレーション矩形を確認します。
- 成駒や持ち駒を誤認識する: 該当表示を含む既知局面からテンプレートを追加します。
- Windowsファイアウォールが表示された: 通常はローカル利用のため `SERVER_HOST=127.0.0.1` のまま使用します。
