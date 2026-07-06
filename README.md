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

## 静止画像認識と合法手追跡

最初に `samples/calibration.example.json` をコピーし、実際のスクリーンショットに合わせて盤面、持ち駒枚数、手番表示のピクセル矩形を設定します。サンプル座標は説明用で、そのまま棋桜へ適用できる値ではありません。

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

時系列画像を合法手で追跡します。既定では同じ候補が3フレーム連続した場合だけ確定します。`--evaluate` を付けると、確定局面だけをYaneuraOuへ送ります。

```bash
uv run python -m kiou_eval track-images frame01.png frame02.png frame03.png \
  --calibration calibration.json \
  --templates templates/kiou \
  --evaluate
```

盤面が後手側から180度回転して表示される場合は `rotate_board_180` を `true` にします。認識失敗・合法手不一致・安定待ちのフレームは評価されません。

## 開発

```bash
uv run pytest
uv run ruff check .
```

YaneuraOu実体を使う試験は通常の単体テストから分離します。

## トラブルシューティング

- 「YaneuraOuが見つかりません」: `YANEAURAOU_ENGINE_PATH` が `.exe` 本体を指すか確認します。
- 起動直後に終了する: `.exe` と同じディレクトリに必要なDLLと評価関数ファイルがあるか確認します。
- OBSが更新されない: サーバーが起動中か、OBSのURLとポートが一致するか確認します。
- 画像を認識できない: 画面解像度と拡大率をテンプレート作成時に揃え、キャリブレーション矩形を確認します。
- 成駒や持ち駒を誤認識する: 該当表示を含む既知局面からテンプレートを追加します。
- Windowsファイアウォールが表示された: 通常はローカル利用のため `SERVER_HOST=127.0.0.1` のまま使用します。
