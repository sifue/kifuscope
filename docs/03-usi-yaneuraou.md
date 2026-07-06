# YaneuraOu・USI連携

## 起動と初期化

エンジンは外部プロセスとして実行し、作業ディレクトリを実行ファイルの親にする。これにより同梱DLLや評価関数の相対パスを維持する。

```text
usi → usiok
setoption name USI_Hash value <MB>
setoption name Threads value <数>
setoption name MultiPV value <数>
isready → readyok
usinewgame
```

評価時は `position sfen ...` と `go movetime ...` を送り、`bestmove` までの最新 `info` をMultiPV番号ごとに保持する。各応答にはタイムアウトを設ける。終了時は `quit` を送り、応答しなければプロセスを終了する。

## 評価値

`score cp` は手番側から見た評価値として扱い、後手番なら符号を反転して先手視点へ統一する。`score mate` も同じ規則で正規化し、cpとは別フィールドに保存する。正は先手有利、負は後手有利を表す。

ファイル不在、起動失敗、切断、タイムアウト、評価値欠落は日本語の `EngineError` とし、APIでは `engine_error` とHTTP 503へ変換する。

