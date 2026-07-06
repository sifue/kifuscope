# OBSオーバーレイ

サーバー起動後、OBS Browser Sourceへ `http://127.0.0.1:8765/overlay` を登録する。推奨サイズは幅520、高さ220以上。背景は透過で、形勢バー、先手視点評価値、最善手、深さ、状態を表示する。

## OBSとの役割分担

OBSはKifuscopeへの画面入力元ではなく、配信画面の合成先として扱う。

- OBS Window Capture: 棋桜の `KIOU` ウィンドウを配信用映像として取り込む
- Kifuscope: `KIOU` ウィンドウを直接キャプチャして盤面認識・評価する
- OBS Browser Source: Kifuscopeの `/overlay` を重ねて評価値を表示する

OBSのWindow Capture映像をPythonへ戻す構成は、仮想カメラやNDIなどの追加経路が必要になり、遅延と運用ミスの原因になる。Kifuscopeは棋桜の通信内容や内部APIには触れず、画面キャプチャだけを入力にする。

OBS側の最小構成は次の2ソース。

1. `ウィンドウキャプチャ`: 対象ウィンドウ `KIOU`
2. `ブラウザ`: URL `http://127.0.0.1:8765/overlay`

対局者が見る画面・プロジェクター・共有画面には、ブラウザソースを含めない。

リアルタイム認識・評価込みで起動する場合は次を使う。

```bash
uv run python -m kiou_eval serve-realtime \
  --calibration samples/calibration.kiou-2064x1112.example.json \
  --templates templates/kiou-initial \
  --source window \
  --window-title KIOU
```

起動後、OBS Browser Sourceは通常通り `http://127.0.0.1:8765/overlay` を参照する。Kifuscope側は `KIOU` ウィンドウを直接キャプチャし、局面未確定・認識失敗・評価中・評価完了の状態をWebSocketで配信する。

この `--source window` 構成では、棋桜、Kifuscope、OBSをすべてWindows側で起動する。WSL Ubuntu上でKifuscopeを起動しても、Windows側の `KIOU` ウィンドウは直接取得できない。WSLは開発・テスト・画像列検証用とし、本番配信ではWindows側のPython環境から起動する。

## 更新仕様

`GET /api/eval` は最新状態をJSONで返す。`POST /api/analyze` は `sfen` と任意の `movetime_ms` を受け取り、探索結果を最新状態にする。`/ws/eval` は接続時と状態変更時に同じJSONを配信する。ブラウザ側は切断時に自動再接続する。

評価値バーはcpを非線形変換して極端な値でも視認可能にする。詰みは「詰みまでN手」としてcpと区別する。エンジンエラーや将来の認識失敗は警告色にし、古い評価値を残さない。
