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

YaneuraOu本体とDLLはリポジトリへコピーしません。既定では次のWindowsパスを参照します。

```text
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\YaneuraOu-Deep-ORT-CPU.exe
```

別の場所にある場合は、作業ディレクトリの `.env` に設定します。

```dotenv
YANEAURAOU_ENGINE_PATH=C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\YaneuraOu-Deep-ORT-CPU.exe
YANEAURAOU_HASH_MB=1024
YANEAURAOU_THREADS=4
YANEAURAOU_MULTIPV=3
YANEAURAOU_MOVETIME_MS=500
YANEAURAOU_EXTRA_OPTIONS=
SERVER_HOST=127.0.0.1
SERVER_PORT=8765
```

Linuxでは、エンジンをリポジトリ外へ配置して実行権限を付けます。

```bash
chmod +x /home/user/Apps/yaneuraou/YaneuraOu
```

```dotenv
YANEAURAOU_ENGINE_PATH=/home/user/Apps/yaneuraou/YaneuraOu
```

NNUE版では通常、実行ファイルの親ディレクトリ以下に `eval/nn.bin` が必要です。エンジンと評価関数のアーキテクチャが一致する配布物を使用してください。

Windowsの `YaneuraOu-Deep-ORT-CPU` 版では、通常 `eval/model.onnx` とONNX Runtime DLL群が必要です。次のエラーが出る場合は、Deep ORT CPU版の配布物から `eval/model.onnx` を配置してください。

```text
Error! : C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\eval/model.onnx file not found
```

PowerShellで確認できます。

```powershell
Test-Path C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\eval\model.onnx
Test-Path C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\onnxruntime.dll
Test-Path C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\onnxruntime_providers_shared.dll
```

また、Deep ORT CPU版が `Threads` USIオプションを持たない場合があります。その場合は `.env.local` に次を設定すると、Kifuscopeは `setoption name Threads ...` を送信しません。

```dotenv
YANEAURAOU_THREADS=0
```

### Windows版ふかうら王TensorRTを使う場合

ふかうら王TensorRT版もUSIエンジンとして起動するため、Kifuscopeから利用できます。`.env.local` の `YANEAURAOU_ENGINE_PATH` をTensorRT版の実行ファイルへ向けてください。

```dotenv
YANEAURAOU_ENGINE_PATH=C:\Apps\YaneuraOu-Deep-TensorRT_V940\YaneuraOu-Deep-TensorRT.exe
YANEAURAOU_THREADS=0
YANEAURAOU_HASH_MB=1024
YANEAURAOU_MULTIPV=3
YANEAURAOU_MOVETIME_MS=300
```

Kifuscopeは起動時にエンジンが宣言するUSIオプションを読み、存在するオプションだけ `setoption` します。これにより、`Threads` 非対応のDeep系エンジンやTensorRT版でも `No such option` で止まりにくくしています。

TensorRT版固有のUSIオプションを渡したい場合は、`;` 区切りで指定できます。指定した名前がエンジン側に存在しない場合は送信せずスキップします。

```dotenv
YANEAURAOU_EXTRA_OPTIONS=SomeOption=Value;AnotherOption=123
```

ふかうら王TensorRT版はNVIDIA GPU向けです。公式リリースでは、V9.40のTensorRT版はNVIDIA GPUが必要で、配布版にはCUDA/TensorRT/cuDNNランタイムが同梱されています。TensorRT/cuDNNのDLLをグローバルPATHで混在させると別バージョン競合が起きやすいため、公式Wikiのフォルダ構成例どおり、実行ファイルと同じフォルダへ必要DLLと `eval/*.model` を置く構成を推奨します。

参考:

- [ふかうら王のインストール手順 - yaneurao/YaneuraOu Wiki](https://github.com/yaneurao/YaneuraOu/wiki/%E3%81%B5%E3%81%8B%E3%81%86%E3%82%89%E7%8E%8B%E3%81%AE%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB%E6%89%8B%E9%A0%86)
- [YaneuraOu Releases - GitHub](https://github.com/yaneurao/YaneuraOu/releases)
- [ふかうら王のビルド手順 - yaneurao/YaneuraOu Wiki](https://github.com/yaneurao/YaneuraOu/wiki/%E3%81%B5%E3%81%8B%E3%81%86%E3%82%89%E7%8E%8B%E3%81%AE%E3%83%93%E3%83%AB%E3%83%89%E6%89%8B%E9%A0%86)

設定の優先順位は、CLI引数、環境変数、`.env.local`、`.env`、既定値です。

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

リアルタイム認識・評価込みで起動する場合:

```bash
uv run python -m kiou_eval serve-realtime \
  --calibration samples/calibration.kiou-2064x1112.example.json \
  --templates templates/kiou-initial \
  --source window \
  --window-title KIOU
```

Windows上では、表示中の `KIOU` ウィンドウを直接キャプチャします。OBSは同じ `KIOU` ウィンドウを「ウィンドウキャプチャ」で取り込み、Kifuscopeの `/overlay` を「ブラウザ」ソースで重ねます。

重要: `--source window --window-title KIOU` はWindows APIでウィンドウを取得するため、KifuscopeもWindows側で起動する必要があります。WSL Ubuntu上で実行したKifuscopeからは、通常のWindowsアプリである棋桜のウィンドウを直接取得できません。

Windowsでの最小起動手順は次の通りです。

1. 棋桜を起動し、ウィンドウタイトルが `KIOU` になっていることを確認する
2. KIOUウィンドウを最小化せず、画面上に表示しておく
3. Kifuscopeを起動する

```powershell
uv run python -m kiou_eval serve-realtime `
  --calibration samples/calibration.kiou-2064x1112.example.json `
  --templates templates/kiou-initial `
  --source window `
  --window-title KIOU
```

PowerShellではなくコマンドプロンプトを使う場合は、1行で実行します。

```cmd
uv run python -m kiou_eval serve-realtime --calibration samples/calibration.kiou-2064x1112.example.json --templates templates/kiou-initial --source window --window-title KIOU
```

起動後、ブラウザで `http://127.0.0.1:8765/overlay` を開いて表示確認します。OBSには同じURLを Browser Source として登録します。

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
- TensorRT版が起動しない: NVIDIA GPU、NVIDIAドライバー、CUDA/TensorRT/cuDNNのバージョン、`eval/*.model`、DLL配置を確認します。配布版では同梱DLLをエンジン本体と同じフォルダに置く構成を優先します。
- OBSが更新されない: サーバーが起動中か、OBSのURLとポートが一致するか確認します。
- 画像を認識できない: 画面解像度と拡大率をテンプレート作成時に揃え、キャリブレーション矩形を確認します。
- 成駒や持ち駒を誤認識する: 該当表示を含む既知局面からテンプレートを追加します。
- Windowsファイアウォールが表示された: 通常はローカル利用のため `SERVER_HOST=127.0.0.1` のまま使用します。
