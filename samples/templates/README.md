# テンプレート配置規約

実際の棋桜画面と同じ解像度・拡大率から切り出したPNGを使用する。複数の見た目がある場合は、同じラベルのディレクトリへ複数枚置ける。

```text
templates/
  board/
    empty/*.png
    black_pawn/*.png
    black_lance/*.png
    ...
    white_dragon/*.png
  hand/
    0/*.png
    1/*.png
    ...
    18/*.png
  turn/
    black/*.png
    white/*.png
```

持ち駒テンプレートは、`calibration.json` の各 `hand_slots` が切り出す「枚数表示部分」に対応する。表示なしを0枚として登録する。盤面ラベルの全一覧は `src/kiou_eval/recognizer/templates.py` の `PIECE_TO_LABEL` を参照する。
