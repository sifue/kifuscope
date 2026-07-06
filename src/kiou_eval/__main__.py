"""Kifuscopeコマンドラインインターフェース。"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import cv2
import uvicorn

from kiou_eval.config import Settings
from kiou_eval.engine import EngineError, YaneuraOuClient
from kiou_eval.recognizer import (
    Calibration,
    ScreenRecognizer,
    TemplateLibrary,
    build_templates,
    capture_window,
    load_image,
)
from kiou_eval.runtime import RealtimeConfig
from kiou_eval.server import create_app
from kiou_eval.shogi import INITIAL_SFEN, BoardState, SfenError, StableLegalTracker


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将棋評価値をOBSへ配信します")
    parser.add_argument("--engine-path", type=Path, help="YaneuraOu実行ファイルのパス")
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze-sfen", help="SFEN局面を評価する")
    analyze.add_argument("sfen", help="評価対象のSFEN")
    analyze.add_argument("--movetime", type=int, dest="movetime_ms", help="探索時間（ミリ秒）")

    subparsers.add_parser("check-engine", help="YaneuraOuとの接続を確認する")

    serve = subparsers.add_parser("serve", help="ローカルサーバーを起動する")
    serve.add_argument("--host", dest="server_host")
    serve.add_argument("--port", type=int, dest="server_port")

    realtime = subparsers.add_parser(
        "serve-realtime", help="棋桜画面を認識しながらローカルサーバーを起動する"
    )
    realtime.add_argument("--host", dest="server_host")
    realtime.add_argument("--port", type=int, dest="server_port")
    realtime.add_argument("--calibration", type=Path, required=True, help="領域設定JSON")
    realtime.add_argument("--templates", type=Path, required=True, help="テンプレートディレクトリ")
    realtime.add_argument("--initial-sfen", default=INITIAL_SFEN, help="追跡開始局面")
    realtime.add_argument(
        "--source",
        choices=["window", "monitor", "images"],
        default="window",
        help="キャプチャ元",
    )
    realtime.add_argument("--window-title", default="KIOU", help="対象ウィンドウタイトル")
    realtime.add_argument(
        "--window-contains",
        action="store_true",
        help="ウィンドウタイトルを完全一致ではなく部分一致で検索する",
    )
    realtime.add_argument("--monitor", type=int, default=1, help="mssのモニター番号")
    realtime.add_argument("--images", type=Path, nargs="*", help="検証用の時系列画像")
    realtime.add_argument(
        "--interval",
        type=float,
        default=0.25,
        help="キャプチャ間隔（秒）",
    )
    realtime.add_argument(
        "--no-evaluate",
        action="store_true",
        help="局面追跡のみ行い、YaneuraOu評価は行わない",
    )

    demo = subparsers.add_parser("demo-overlay", help="デモ評価値を表示するサーバーを起動する")
    demo.add_argument("--host", dest="server_host")
    demo.add_argument("--port", type=int, dest="server_port")

    recognize = subparsers.add_parser("recognize-image", help="静止画像から局面を認識する")
    recognize.add_argument("image", type=Path, help="認識するスクリーンショット")
    recognize.add_argument("--calibration", type=Path, required=True, help="領域設定JSON")
    recognize.add_argument("--templates", type=Path, required=True, help="テンプレートディレクトリ")
    recognize.add_argument("--move-number", type=int, default=1, help="SFENへ設定する手数")

    capture = subparsers.add_parser(
        "capture-window", help="Windowsのウィンドウタイトルから1フレーム保存する"
    )
    capture.add_argument("--title", default="KIOU", help="対象ウィンドウタイトル")
    capture.add_argument(
        "--contains", action="store_true", help="タイトルを完全一致ではなく部分一致で検索する"
    )
    capture.add_argument("--output", type=Path, required=True, help="保存先PNG")

    track = subparsers.add_parser("track-images", help="連続画像を合法手で追跡する")
    track.add_argument("images", type=Path, nargs="+", help="時系列順のスクリーンショット")
    track.add_argument("--calibration", type=Path, required=True, help="領域設定JSON")
    track.add_argument("--templates", type=Path, required=True, help="テンプレートディレクトリ")
    track.add_argument("--initial-sfen", default=INITIAL_SFEN, help="追跡開始局面")
    track.add_argument("--evaluate", action="store_true", help="確定局面をYaneuraOuで評価する")
    track.add_argument("--movetime", type=int, dest="movetime_ms", help="探索時間（ミリ秒）")

    build = subparsers.add_parser(
        "build-templates", help="既知局面の画像からテンプレートを生成する"
    )
    build.add_argument("image", type=Path, help="既知局面のスクリーンショット")
    build.add_argument("--sfen", required=True, help="画像に対応するSFEN")
    build.add_argument("--calibration", type=Path, required=True, help="領域設定JSON")
    build.add_argument("--output", type=Path, required=True, help="テンプレート出力先")
    return parser


def _settings(args: argparse.Namespace) -> Settings:
    return Settings().with_overrides(
        engine_path=args.engine_path,
        movetime_ms=getattr(args, "movetime_ms", None),
        server_host=getattr(args, "server_host", None),
        server_port=getattr(args, "server_port", None),
    )


def main(argv: list[str] | None = None) -> int:
    """CLIのエントリーポイント。"""
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = _settings(args)
    try:
        if args.command == "check-engine":
            with YaneuraOuClient(settings) as engine:
                engine.check_connection()
            print("YaneuraOuへの接続に成功しました")
            return 0
        if args.command == "analyze-sfen":
            with YaneuraOuClient(settings) as engine:
                result = engine.analyze(args.sfen, movetime_ms=args.movetime_ms)
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            return 0
        if args.command in {"serve", "demo-overlay"}:
            uvicorn.run(
                create_app(settings, demo=args.command == "demo-overlay"),
                host=settings.server_host,
                port=settings.server_port,
                log_level=args.log_level.lower(),
            )
            return 0
        if args.command == "serve-realtime":
            realtime_config = RealtimeConfig(
                calibration_path=args.calibration,
                templates_path=args.templates,
                initial_sfen=args.initial_sfen,
                source=args.source,
                window_title=args.window_title,
                window_contains=args.window_contains,
                monitor=args.monitor,
                images=tuple(args.images or ()),
                interval_sec=args.interval,
                evaluate=not args.no_evaluate,
            )
            uvicorn.run(
                create_app(settings, realtime=realtime_config),
                host=settings.server_host,
                port=settings.server_port,
                log_level=args.log_level.lower(),
            )
            return 0
        if args.command == "recognize-image":
            calibration = Calibration.from_file(args.calibration)
            recognizer = ScreenRecognizer(calibration, TemplateLibrary(args.templates))
            result = recognizer.recognize(load_image(args.image), move_number=args.move_number)
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            return 0 if result.status in {"ok", "board_observed"} else 2
        if args.command == "capture-window":
            result = capture_window(args.title, exact=not args.contains)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(args.output), result.image):
                raise ValueError(f"画像を書き込めません: {args.output}")
            print(
                "ウィンドウをキャプチャしました: "
                f"title={result.title}, rect={result.left},{result.top},"
                f"{result.width}x{result.height}, output={args.output}"
            )
            return 0
        if args.command == "track-images":
            calibration = Calibration.from_file(args.calibration)
            recognizer = ScreenRecognizer(calibration, TemplateLibrary(args.templates))
            tracker = StableLegalTracker(
                BoardState.from_sfen(args.initial_sfen),
                stable_frames=calibration.stable_frames,
                threshold=calibration.legal_match_threshold,
                margin=calibration.legal_margin,
            )
            outputs: list[dict[str, object]] = []
            last_evaluated_sfen: str | None = None
            engine = YaneuraOuClient(settings) if args.evaluate else None
            try:
                for image_path in args.images:
                    recognized = recognizer.recognize(
                        load_image(image_path), move_number=tracker.current.move_number
                    )
                    tracked = tracker.update(recognized.observation)
                    output = {"image": str(image_path), **tracked.to_dict()}
                    current_sfen = tracked.state.to_sfen()
                    if (
                        engine is not None
                        and tracked.status == "ok"
                        and current_sfen != last_evaluated_sfen
                    ):
                        evaluation = engine.analyze(current_sfen, movetime_ms=args.movetime_ms)
                        output["evaluation"] = evaluation.to_dict()
                        last_evaluated_sfen = current_sfen
                    outputs.append(output)
            finally:
                if engine is not None:
                    engine.close()
            print(json.dumps(outputs, ensure_ascii=False, indent=2))
            return 0
        if args.command == "build-templates":
            calibration = Calibration.from_file(args.calibration)
            count = build_templates(
                load_image(args.image),
                BoardState.from_sfen(args.sfen),
                calibration,
                args.output,
            )
            print(f"テンプレートを{count}枚生成しました: {args.output}")
            return 0
    except (EngineError, SfenError, ValueError) as exc:
        logging.error("処理に失敗しました: %s", exc)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
