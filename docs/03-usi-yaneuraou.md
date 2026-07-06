# YaneuraOu・USI連携

## 起動と初期化

エンジンは外部プロセスとして実行し、作業ディレクトリを実行ファイルの親にする。これにより同梱DLLや評価関数の相対パスを維持する。

```text
usi → usiok
setoption name USI_Hash value <MB>
setoption name Threads value <数>
setoption name MultiPV value <数>
setoption name <追加オプション> value <値>
isready → readyok
usinewgame
```

実際には、`usi` 応答中の `option name ...` 行を収集し、エンジンが宣言したオプションだけ送る。Windowsの `YaneuraOu-Deep-ORT-CPU` やふかうら王TensorRT版など、Deep系エンジンは `Threads` など一部オプションを持たない場合があるためである。

`YANEAURAOU_THREADS=0` の場合は `Threads` オプションを送らない。TensorRT版などの固有オプションは `.env.local` の `YANEAURAOU_EXTRA_OPTIONS` に `Name=Value;Name2=Value2` 形式で指定する。指定したオプションがエンジン側に存在しない場合は送信しない。

評価時は `position sfen ...` と `go movetime ...` を送り、`bestmove` までの最新 `info` をMultiPV番号ごとに保持する。各応答にはタイムアウトを設ける。終了時は `quit` を送り、応答しなければプロセスを終了する。

## Windows Deep ORT CPU版の配置確認

`YaneuraOu-Deep-ORT-CPU` 版は、実行ファイルと同じディレクトリにONNX Runtime DLL群、配下の `eval/` にONNX評価モデルが必要である。

```text
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\YaneuraOu-Deep-ORT-CPU.exe
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\onnxruntime.dll
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\onnxruntime_providers_shared.dll
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\eval\model.onnx
```

次のエラーが出る場合は、評価モデルが不足している。

```text
Error! : C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\eval/model.onnx file not found
```

PowerShellで確認する。

```powershell
Test-Path C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\eval\model.onnx
```

`No such option: Threads` が出る場合は `.env.local` に次を設定する。

```dotenv
YANEAURAOU_THREADS=0
```

## Windows ふかうら王TensorRT版

ふかうら王TensorRT版もUSIエンジンとして起動する。Kifuscope側は通常のYaneuraOuと同じく、外部プロセスとして起動し、標準入力・標準出力でUSI通信する。

`.env.local` の例。

```dotenv
YANEAURAOU_ENGINE_PATH=C:\Apps\YaneuraOu-Deep-TensorRT_V940\YaneuraOu-Deep-TensorRT.exe
YANEAURAOU_THREADS=0
YANEAURAOU_HASH_MB=1024
YANEAURAOU_MULTIPV=3
YANEAURAOU_MOVETIME_MS=300
YANEAURAOU_EXTRA_OPTIONS=
```

TensorRT版固有のUSIオプションを指定する場合。

```dotenv
YANEAURAOU_EXTRA_OPTIONS=SomeOption=Value;AnotherOption=123
```

ふかうら王TensorRT版はNVIDIA GPU向けである。公式ReleaseではTensorRT版にNVIDIA GPUが必要とされ、配布版にはCUDA、TensorRT、cuDNNのランタイムが同梱される。DLLのバージョン競合を避けるため、公式Wikiの説明どおり、エンジン本体、同梱DLL、評価モデルを同じ配布フォルダ構成で置く。Kifuscopeは実行ファイルの親ディレクトリを作業ディレクトリにして起動するため、相対パスで配置されたDLLや `eval/` を読みやすい。

参考:

- [ふかうら王のインストール手順 - yaneurao/YaneuraOu Wiki](https://github.com/yaneurao/YaneuraOu/wiki/%E3%81%B5%E3%81%8B%E3%81%86%E3%82%89%E7%8E%8B%E3%81%AE%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB%E6%89%8B%E9%A0%86)
- [YaneuraOu Releases - GitHub](https://github.com/yaneurao/YaneuraOu/releases)
- [ふかうら王のビルド手順 - yaneurao/YaneuraOu Wiki](https://github.com/yaneurao/YaneuraOu/wiki/%E3%81%B5%E3%81%8B%E3%81%86%E3%82%89%E7%8E%8B%E3%81%AE%E3%83%93%E3%83%AB%E3%83%89%E6%89%8B%E9%A0%86)

## 評価値

`score cp` は手番側から見た評価値として扱い、後手番なら符号を反転して先手視点へ統一する。`score mate` も同じ規則で正規化し、cpとは別フィールドに保存する。正は先手有利、負は後手有利を表す。

ファイル不在、起動失敗、切断、タイムアウト、評価値欠落は日本語の `EngineError` とし、APIでは `engine_error` とHTTP 503へ変換する。
