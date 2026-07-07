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

## Windows Deep系エンジンの設定

Deep ORT CPU版とふかうら王TensorRT版は、通常のYaneuraOuと同じくUSIエンジンとして扱う。ただし、Deep系エンジンは `Threads` など一部のUSIオプションを持たない場合がある。Windowsでは `YANEAURAOU_THREADS=0` を基本にし、Kifuscopeから `Threads` を送らない。

Kifuscopeは `usi` 応答中の `option name ...` を収集し、エンジンが宣言したオプションだけ送る。`USI_Hash`、`MultiPV`、追加オプションも未対応ならスキップする。

### 1. まずCPU版で切り分ける

最初にDeep ORT CPU版で `check-engine` と `analyze-sfen` を通す。CPU版で成功すれば、Kifuscope本体、USI通信、ONNXモデル配置の基本経路は正常と判断できる。

`.env.local` 例。

```dotenv
YANEAURAOU_ENGINE_PATH=C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\YaneuraOu-Deep-ORT-CPU.exe
YANEAURAOU_THREADS=0
YANEAURAOU_HASH_MB=1024
YANEAURAOU_MULTIPV=3
YANEAURAOU_MOVETIME_MS=500
YANEAURAOU_COMMAND_TIMEOUT_SEC=60
YANEAURAOU_EXTRA_OPTIONS=
```

配置例。

```text
C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\
  YaneuraOu-Deep-ORT-CPU.exe
  onnxruntime.dll
  onnxruntime_providers_shared.dll
  eval\
    model.onnx
    model.onnx.ini
```

`model.onnx` はdlshogiの公開モデルを取得して配置する。例として、DeepLearningShogiの `dr2_exhi` Releaseから `model-dr2_exhi.zip` を取得し、展開後のファイルをリネームする。ライセンスは配布元で確認する。

```text
model-dr2_exhi.onnx      -> eval\model.onnx
model-dr2_exhi.onnx.ini  -> eval\model.onnx.ini
```

確認。

```powershell
Test-Path C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\eval\model.onnx
Test-Path C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\onnxruntime.dll
uv run python -m kiou_eval check-engine
```

### 2. GPU/TensorRT版へ切り替える

CPU版で成功した後、ふかうら王TensorRT版へ切り替える。TensorRT版だけ失敗する場合は、Kifuscope本体ではなくGPU、NVIDIAドライバー、CUDA/TensorRT/cuDNN DLL、TensorRTエンジン生成、モデル形式の問題に絞り込める。

`.env.local` 例。

```dotenv
YANEAURAOU_ENGINE_PATH=C:\Apps\YaneuraOu-Deep-TensorRT_V940\YaneuraOu-Deep-TensorRT.exe
YANEAURAOU_THREADS=0
YANEAURAOU_HASH_MB=1024
YANEAURAOU_MULTIPV=3
YANEAURAOU_MOVETIME_MS=300
YANEAURAOU_COMMAND_TIMEOUT_SEC=180
YANEAURAOU_EXTRA_OPTIONS=
```

TensorRT版は初回起動時やモデル最適化時に `isready` 応答まで時間がかかる場合があるため、タイムアウトはCPU版より長めにする。公式配布物のフォルダ構成を崩さず、エンジン本体、同梱DLL、`eval/` を同じ配布フォルダ内に置く。

TensorRT版固有のUSIオプションを指定する場合。

```dotenv
YANEAURAOU_EXTRA_OPTIONS=SomeOption=Value;AnotherOption=123
```

参考:

- [DeepLearningShogi dr2_exhi Release](https://github.com/TadaoYamaoka/DeepLearningShogi/releases/tag/dr2_exhi)
- [dlshogi Windows版ビルド済みファイル公開 - TadaoYamaokaの日記](https://tadaoyamaoka.hatenablog.com/entry/2021/08/17/000710)
- [ふかうら王のインストール手順 - yaneurao/YaneuraOu Wiki](https://github.com/yaneurao/YaneuraOu/wiki/%E3%81%B5%E3%81%8B%E3%81%86%E3%82%89%E7%8E%8B%E3%81%AE%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB%E6%89%8B%E9%A0%86)
- [YaneuraOu Releases - GitHub](https://github.com/yaneurao/YaneuraOu/releases)

## 評価値

`score cp` は手番側から見た評価値として扱い、後手番なら符号を反転して先手視点へ統一する。`score mate` も同じ規則で正規化し、cpとは別フィールドに保存する。正は先手有利、負は後手有利を表す。

ファイル不在、起動失敗、切断、タイムアウト、評価値欠落は日本語の `EngineError` とし、APIでは `engine_error` とHTTP 503へ変換する。
