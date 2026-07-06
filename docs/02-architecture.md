# アーキテクチャ

```text
SFEN入力 → SFEN構文検証 → USIクライアント → YaneuraOu
                                      ↓
                              EvalResult（先手視点）
                                      ↓
                  REST API / WebSocket → OBSオーバーレイ
```

## モジュール責務

- `config`: `.env`、環境変数、CLI値の統合
- `shogi.sfen`: SFENの構文検証と手番取得
- `engine.usi_parser`: `info` 行の値抽出と符号正規化
- `engine.yaneuraou_client`: プロセス寿命とUSIシーケンス
- `server`: 最新評価状態、REST API、WebSocket配信
- `overlay`: OBS Browser Source向け表示
- `runtime.realtime`: キャプチャ、認識、合法手追跡、評価要求のリアルタイム運用

MVP 1はSFEN入力からJSON出力まで、MVP 2は最新状態API、評価API、WebSocket、オーバーレイまでを対象とする。MVP 3は設定可能な画面領域とテンプレートで静止画像を観測へ変換する。MVP 4は前局面と全合法手後の局面を観測に照合し、連続安定後だけSFENを評価層へ渡す。
MVP 5は `RealtimeEvaluator` がWindowsの `KIOU` ウィンドウ、モニター、または検証用画像列をキャプチャし、確定した最新局面だけを評価・配信する。

```text
KIOUウィンドウ / モニター / 検証画像列
  → RealtimeEvaluator
  → Calibrationによる領域切り出し
  → ScreenRecognizer（81マス・持ち駒・手番）
  → BoardObservation（UNKNOWNを許容）
  → LegalMoveMatcher（現在局面＋全合法手後）
  → StableLegalTracker（連続フレーム確認）
  → BoardState / SFEN
  → YaneuraOu（評価中に新局面が来た場合はstop要求）
  → EvaluationHub
  → REST API / WebSocket / OBSオーバーレイ
```

`BoardObservation` は不完全な画像認識結果であり、評価層へ直接渡せない。`BoardState` は王、二歩、駒数、cshogi内部整合性を検証する。これにより認識器とUSI制御の責務を分離する。

初期運用では、棋桜の持ち駒欄を直接OCRしない。盤面81マスを主入力とし、初期局面からの合法手追跡によって手番と持ち駒を内部状態として復元する。これにより、持ち駒欄の可変レイアウトに依存しない構成にする。
