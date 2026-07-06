# AGENTS.md

This file provides guidance to AI Coding Agents when working with code in this repository.

## 言語設定

このプロジェクトは日本語環境での利用・開発を前提とする。

* コミュニケーションは日本語で行うこと
* README・設計文書・技術文書・進捗報告書は日本語で作成すること
* コードコメントは日本語で記述すること
* エラーメッセージ・ログメッセージは可能な限り日本語で表示すること
* 変数名・関数名・型名・ファイル名・ディレクトリ名は英語を使用すること
* 将棋用語は必要に応じて日本語コメントで補足すること

## プロジェクトの目的

このプロジェクトは、画面共有された将棋対局サービス「棋桜」の画面から局面を認識し、ローカルにインストール済みの `YaneuraOu` を用いて評価値を計算し、OBSに評価値・形勢バー・最善手などを表示するためのシステムを開発することを目的とする。

想定用途は、大学内イベント・配信・実況解説である。

重要な前提として、本システムは **対局者にリアルタイム評価値を見せるためのものではない**。配信者・実況・解説・OBSオーバーレイ向けの支援ツールとして実装する。対局者が評価値や最善手を閲覧できる形にしてはならない。

## 最終的なゴール

最終的には、以下の流れを実現する。

```text
棋桜の画面共有 / OBS入力 / スクリーンキャプチャ
        ↓
盤面・持ち駒・手番の画像認識
        ↓
局面をSFENに変換
        ↓
cshogi等で合法局面・合法手として検証
        ↓
YaneuraOuへUSIプロトコルで局面を送信
        ↓
評価値・最善手・読み筋を取得
        ↓
ローカルWebサーバー / WebSocket / JSON
        ↓
OBS Browser Source に評価値オーバーレイを表示
```

## 開発方針

いきなりリアルタイム画像認識まで作らず、以下のMVP順に段階的に進めること。

### MVP 1: 手入力SFENから評価値を取得する

最初に完成させるべき最小機能。

* 手入力またはサンプルSFENを受け取る
* YaneuraOuをサブプロセスとして起動する
* USIプロトコルで `position sfen ...` と `go movetime ...` を送る
* `info score cp` / `info score mate` / `bestmove` を取得する
* 結果をJSONで返す
* pytestで最低限のテストを書く

### MVP 2: OBS用オーバーレイを表示する

* FastAPI等でローカルサーバーを起動する
* `/api/eval` などで現在評価値を返す
* `/overlay` または `overlay.html` でOBS Browser Source向けの画面を表示する
* 評価値バー、先手視点評価値、最善手、認識状態を表示する
* WebSocketまたはServer-Sent Eventsで更新する

### MVP 3: スクリーンショットから盤面を認識する

* まずは静止画像を入力として扱う
* 盤面クロップ領域を設定ファイルで指定できるようにする
* 9×9マスに分割する
* OpenCVのテンプレートマッチング、または軽量な画像分類で駒を認識する
* 認識結果を内部局面に変換する
* cshogiで局面として妥当か検証する

### MVP 4: 初期局面からの合法手追跡

* 毎フレームの完全認識だけに依存しない
* 前局面からの合法手一覧を生成する
* 現在画像と最も一致する合法手を採用する
* 持ち駒の増減も合法手から補正する
* 一定時間局面が安定してから評価を開始する

### MVP 5: リアルタイム運用

* Windows上で棋桜画面をキャプチャする
* 局面変化を検知する
* 最新局面のみ評価する
* 古い探索は `stop` で停止する
* OBS Browser Sourceでリアルタイム表示する
* 認識に失敗した場合は評価表示を止め、「認識中」「認識失敗」などを表示する

## 技術構成

原則としてPythonを中心に構築する。

* Python 3.11以上
* uv
* FastAPI
* Uvicorn
* WebSocket
* OpenCV
* NumPy
* cshogi
* pydantic
* pytest
* ruff
* mss または同等のスクリーンキャプチャライブラリ
* YaneuraOu
* OBS Browser Source

OBSオーバーレイの表示にはHTML/CSSが必要になる。WebSocket受信など、OBS Browser Source上で動作させるために最小限のJavaScriptを使用することは許容する。ただし、システム本体・評価処理・画像認識・USI制御はPythonで実装すること。

## 環境構築

依存関係管理には `uv` を使用すること。

グローバル環境に直接 `pip install` しないこと。

初期構築では以下のような構成を作る。

```bash
uv init
uv add fastapi uvicorn opencv-python numpy pydantic cshogi mss
uv add --dev pytest ruff
```

`pyproject.toml` を作成し、依存関係・開発用コマンド・ruff設定を管理すること。

Python実行は原則として以下の形式を使う。

```bash
uv run python -m kiou_eval
uv run pytest
uv run ruff check .
```

## YaneuraOuのインストール場所

開発環境では、YaneuraOuが以下にインストール済みである。

```text
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\YaneuraOu-Deep-ORT-CPU.exe
```

同じディレクトリに以下のDLLが存在する。

```text
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\onnxruntime.dll
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\onnxruntime_providers_shared.dll
```

このパスをデフォルト値として扱ってよい。ただし、他環境でも動かせるように、設定ファイルまたは環境変数で変更可能にすること。

推奨する環境変数名は以下。

```text
YANEAURAOU_ENGINE_PATH
```

デフォルト値は以下。

```text
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\YaneuraOu-Deep-ORT-CPU.exe
```

YaneuraOu本体やDLLをリポジトリにコピーしないこと。外部インストール済みバイナリとして参照すること。

## USI連携方針

YaneuraOuはライブラリとして組み込まず、サブプロセスとして起動し、標準入力・標準出力でUSIプロトコル通信を行う。

起動時の基本シーケンスは以下。

```text
usi
setoption name USI_Hash value 1024
setoption name Threads value 4
setoption name MultiPV value 3
isready
usinewgame
```

局面解析時の基本シーケンスは以下。

```text
position sfen <SFEN>
go movetime 500
```

探索中に新しい局面が来た場合は、古い探索を放置せず、必要に応じて以下を送る。

```text
stop
```

取得する主な情報。

* `score cp`
* `score mate`
* `depth`
* `seldepth`
* `nodes`
* `nps`
* `multipv`
* `pv`
* `bestmove`

評価値はOBS表示では原則として **先手視点** に正規化すること。

* 先手有利: 正
* 後手有利: 負

USIエンジンから返る評価値の符号が手番視点の場合は、手番を考慮して先手視点に変換すること。

## SFEN方針

画像認識側がUSIを直接扱う必要はない。画像認識側の責務は、以下を復元し、SFENを作ることである。

* 盤上81マス
* 先手持ち駒
* 後手持ち駒
* 手番
* 手数

初期局面SFENは以下。

```text
lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
```

USIへの送信例。

```text
position sfen lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
go movetime 500
```

## 画像認識方針

最初から複雑な機械学習モデルを作らない。まずは以下の順で実装する。

1. 固定クロップ領域による盤面抽出
2. 9×9グリッド分割
3. 駒テンプレートによるテンプレートマッチング
4. 持ち駒領域の認識
5. 手番表示の認識
6. cshogiによる合法性チェック
7. 前局面からの合法手追跡

認識対象はおおむね以下。

```text
空マス
先手: 歩 香 桂 銀 金 角 飛 玉 と 成香 成桂 成銀 馬 龍
後手: 歩 香 桂 銀 金 角 飛 玉 と 成香 成桂 成銀 馬 龍
```

駒の文字OCRだけに依存しないこと。棋桜の画面が固定デザインであるなら、駒画像テンプレートとして扱う方が安定しやすい。

画面認識結果をそのままSFENにしてはならない。必ず以下の補正・検証を行うこと。

* 局面として妥当か
* 王が双方に存在するか
* 二歩などの明らかな違反がないか
* 前局面から合法手で到達可能か
* 持ち駒の増減が合法手と一致するか
* 局面が一定時間安定しているか

## 認識失敗時の方針

認識に失敗した場合、間違った評価値を出すより、表示を止めることを優先する。

OBSオーバーレイには以下のような状態を表示できるようにする。

* `認識中`
* `局面未確定`
* `認識失敗`
* `評価停止`
* `YaneuraOu未接続`
* `評価中`

誤った最善手や評価値を配信に出すことは避ける。

## OBS表示方針

OBSには Browser Source で表示する。

表示項目の優先度は以下。

1. 形勢バー
2. 先手視点の評価値
3. 最善手
4. 短い読み筋
5. 深さ
6. 認識信頼度
7. エンジン状態

初心者向け配信では情報を出しすぎない。最初は以下だけでよい。

```text
先手 +235
最善手 ▲2六歩
認識: OK
```

詰み評価の場合は、通常のcp評価と区別して表示する。

例。

```text
先手 詰みまで 7手
後手 詰みまで 5手
```

## 推奨ディレクトリ構成

以下の構成を基本とする。

```text
kiou-eval/
  AGENTS.md
  README.md
  pyproject.toml
  .gitignore

  docs/
    01-overview.md
    02-architecture.md
    03-usi-yaneuraou.md
    04-screen-recognition.md
    05-obs-overlay.md
    06-progress.md

  src/
    kiou_eval/
      __init__.py
      __main__.py

      config.py

      engine/
        __init__.py
        yaneuraou_client.py
        usi_parser.py
        eval_result.py

      shogi/
        __init__.py
        sfen.py
        board_state.py
        legal_tracker.py
        move_notation.py

      recognizer/
        __init__.py
        capture.py
        calibration.py
        board_recognizer.py
        hand_recognizer.py
        templates.py

      server/
        __init__.py
        app.py
        websocket.py
        schemas.py

      overlay/
        overlay.html
        overlay.css
        overlay.js

  tests/
    test_usi_parser.py
    test_sfen.py
    test_yaneuraou_client.py
    test_eval_normalization.py

  samples/
    sfens.txt
    screenshots/
```

## ドキュメント作成方針

実装と並行して `docs/` 以下に文書を作成すること。

最低限、以下を作成する。

### `docs/01-overview.md`

* プロジェクト概要
* 想定利用シーン
* 倫理・不正利用防止方針
* 非ゴール

### `docs/02-architecture.md`

* 全体構成
* データフロー
* 各モジュールの責務
* MVPごとの実装範囲

### `docs/03-usi-yaneuraou.md`

* YaneuraOu起動方法
* USI通信シーケンス
* 評価値の解釈
* 先手視点への正規化
* エラー時の扱い

### `docs/04-screen-recognition.md`

* 盤面クロップ
* 9×9分割
* テンプレートマッチング
* 持ち駒認識
* 合法手追跡
* 認識信頼度の計算

### `docs/05-obs-overlay.md`

* OBS Browser Source設定方法
* 表示項目
* WebSocket仕様
* オーバーレイのデザイン方針

### `docs/06-progress.md`

* 進捗報告
* 実装済み機能
* 未実装機能
* 既知の問題
* 次にやること

## README.mdに書くべき内容

README.mdには最低限以下を書く。

* プロジェクト概要
* 注意事項
* 動作環境
* YaneuraOuのパス設定
* uvによるセットアップ
* サンプルSFENでの評価値取得方法
* ローカルサーバー起動方法
* OBS Browser Sourceへの登録方法
* テスト実行方法
* トラブルシューティング

## .gitignore方針

以下を含む `.gitignore` を作成すること。

```text
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.env
.env.local
.DS_Store
Thumbs.db

# 外部エンジン本体はコミットしない
YaneuraOu*/
*.exe
*.dll
*.bin
*.onnx

# 生成物
dist/
build/
coverage/
```

ただし、サンプル画像やテスト用の小さなファイルが必要な場合は `samples/` 以下に配置してよい。大きなバイナリは避けること。

## 設定ファイル方針

設定は以下の優先順位で読み込む。

1. コマンドライン引数
2. 環境変数
3. `.env`
4. デフォルト値

最低限、以下の設定を持つこと。

```text
YANEAURAOU_ENGINE_PATH
YANEAURAOU_HASH_MB
YANEAURAOU_THREADS
YANEAURAOU_MULTIPV
YANEAURAOU_MOVETIME_MS
SERVER_HOST
SERVER_PORT
```

デフォルト例。

```text
YANEAURAOU_ENGINE_PATH=C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\YaneuraOu-Deep-ORT-CPU.exe
YANEAURAOU_HASH_MB=1024
YANEAURAOU_THREADS=4
YANEAURAOU_MULTIPV=3
YANEAURAOU_MOVETIME_MS=500
SERVER_HOST=127.0.0.1
SERVER_PORT=8765
```

## テスト方針

最低限、以下のテストを書くこと。

* USIの `info` 行を正しくパースできる
* `score cp` を取得できる
* `score mate` を取得できる
* MultiPVを取得できる
* SFENを扱える
* 評価値を先手視点に正規化できる
* YaneuraOuのパス未設定時に分かりやすいエラーを出す
* エンジン起動失敗時に分かりやすいエラーを出す

YaneuraOu実体が必要なテストは、通常の単体テストから分離すること。

例。

```text
unit test: エンジン不要
integration test: YaneuraOu実体が必要
```

環境変数が設定されていない場合、integration testはskipしてよい。

## コーディング規約

* 型ヒントを付けること
* `dataclass` または `pydantic` を適切に使うこと
* ログを適切に出すこと
* 例外を握りつぶさないこと
* 日本語で分かりやすいエラーメッセージを出すこと
* OS依存パスは `pathlib.Path` を使うこと
* Windowsでの動作を最優先にすること
* 将来的なLinux/macOS対応を妨げないようにすること
* 長い関数を避け、責務ごとに分割すること

## やってはいけないこと

* YaneuraOu本体やDLLをリポジトリにコピーすること
* 対局者に評価値が見える設計にすること
* 棋桜の通信内容を無断でフック・改変・解析すること
* ブラウザや棋桜サービスの内部APIを不正に利用すること
* 画像認識結果を検証なしで評価にかけること
* 認識失敗時にもっともらしい評価値を表示すること
* グローバルPython環境に依存すること
* `pip install` 前提の手順を書くこと
* 大きなバイナリファイルをGit管理すること
* 仕様が曖昧なまま大規模な実装に進むこと

## 開発者への確認が必要なこと

以下は、必要になった場合に開発者へ確認する。

* 棋桜画面の実際のスクリーンショット
* 盤面の向きが固定かどうか
* 配信時の解像度
* OBSのシーン構成
* 評価値表示のデザイン
* 最善手を表示するか、形勢バーだけにするか
* MultiPVを表示するか
* 認識対象を棋桜だけに限定するか
* 手入力補正UIを作るか

ただし、MVP 1とMVP 2については追加確認なしで実装を進めてよい。

## 自律開発の優先順位

AI Coding Agentは、以下の順で自律的に開発を進めること。

1. プロジェクト骨格作成
2. `uv` 環境構築
3. `.gitignore` 作成
4. README初版作成
5. docs初版作成
6. YaneuraOu USIクライアント実装
7. USI parser実装
8. サンプルSFEN評価CLI実装
9. pytest追加
10. FastAPIサーバー実装
11. OBS overlay実装
12. サンプルJSON更新表示
13. 画像認識設計文書の詳細化
14. 静止画像からの盤面認識MVP実装
15. 合法手追跡の実装

## CLI仕様の初期案

まず以下のCLIを作ること。

### サンプルSFENを評価

```bash
uv run python -m kiou_eval analyze-sfen "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
```

### サーバー起動

```bash
uv run python -m kiou_eval serve
```

### YaneuraOu接続確認

```bash
uv run python -m kiou_eval check-engine
```

### サンプル評価値をOBS overlayに流す

```bash
uv run python -m kiou_eval demo-overlay
```

## JSON API初期案

評価結果JSONは以下の形を基本とする。

```json
{
  "status": "ok",
  "sfen": "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
  "turn": "black",
  "eval_cp_sente": 235,
  "score_type": "cp",
  "bestmove": "2g2f",
  "pv": ["2g2f", "8c8d", "2f2e"],
  "depth": 14,
  "nodes": 123456,
  "multipv": 1,
  "confidence": 1.0,
  "message": "評価完了"
}
```

認識失敗時は以下のようにする。

```json
{
  "status": "recognition_failed",
  "message": "局面を認識できませんでした",
  "confidence": 0.42
}
```

YaneuraOu未接続時は以下のようにする。

```json
{
  "status": "engine_error",
  "message": "YaneuraOuを起動できませんでした"
}
```

## 進捗報告

大きな実装を行った場合、必ず `docs/06-progress.md` に以下を書くこと。

* 日付
* 実装した内容
* 変更したファイル
* 動作確認方法
* テスト結果
* 未解決の問題
* 次にやること

## 完了条件

最初の完了条件は以下。

* `uv run python -m kiou_eval check-engine` でYaneuraOu接続確認ができる
* `uv run python -m kiou_eval analyze-sfen <SFEN>` で評価値が取得できる
* `uv run python -m kiou_eval serve` でローカルサーバーが起動する
* OBS Browser Sourceで評価値オーバーレイが表示できる
* READMEにセットアップ手順が書かれている
* pytestが通る
* ruff checkが通る

画像認識はその後の段階でよい。まずは、YaneuraOu連携とOBS表示を安定させることを最優先にする。

