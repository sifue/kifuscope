from __future__ import annotations

import stat
from pathlib import Path

import pytest

from kiou_eval.config import Settings
from kiou_eval.engine import EngineError, YaneuraOuClient
from kiou_eval.shogi import INITIAL_SFEN


def _fake_engine(
    tmp_path: Path,
    *,
    options: bool = False,
    record_commands: Path | None = None,
) -> Path:
    path = tmp_path / "fake_engine.py"
    record_line = (
        f"open({str(record_commands)!r}, 'a', encoding='utf-8').write(command + '\\n')"
        if record_commands is not None
        else ""
    )
    option_lines = (
        """        print("option name USI_Hash type spin default 16 min 1 max 1048576", flush=True)
        print("option name MultiPV type spin default 1 min 1 max 10", flush=True)
        print("option name TensorRT_Batch_Size type spin default 1 min 1 max 1024", flush=True)
"""
        if options
        else ""
    )
    path.write_text(
        f"""#!/usr/bin/env python3
import sys
for raw in sys.stdin:
    command = raw.strip()
    {record_line}
    if command == "usi":
        print("id name FakeEngine", flush=True)
{option_lines}        print("usiok", flush=True)
    elif command == "isready":
        print("readyok", flush=True)
    elif command.startswith("go "):
        print("info depth 12 multipv 2 score cp 30 nodes 80 pv 7g7f", flush=True)
        print("info depth 14 seldepth 20 multipv 1 score cp 235 "
              "nodes 100 nps 5000 pv 2g2f 8c8d", flush=True)
        print("bestmove 2g2f ponder 8c8d", flush=True)
    elif command == "quit":
        break
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_engine_path_error(tmp_path: Path) -> None:
    settings = Settings(engine_path=tmp_path / "missing-engine")
    with pytest.raises(EngineError, match="YANEAURAOU_ENGINE_PATH"):
        YaneuraOuClient(settings).start()


def test_engine_start_error_is_clear(tmp_path: Path) -> None:
    path = tmp_path / "broken-engine"
    path.write_text("実行できないファイル", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    settings = Settings(engine_path=path)
    with pytest.raises(EngineError, match="YaneuraOuを起動できませんでした"):
        YaneuraOuClient(settings).start()


def test_analyze_with_fake_engine(tmp_path: Path) -> None:
    settings = Settings(engine_path=_fake_engine(tmp_path), multipv=2, movetime_ms=10)
    with YaneuraOuClient(settings, command_timeout=2) as client:
        result = client.analyze(INITIAL_SFEN)
    assert result.eval_cp_sente == 235
    assert result.bestmove == "2g2f"
    assert result.depth == 14
    assert result.pv == ["2g2f", "8c8d"]
    assert len(result.lines) == 2


def test_white_turn_score_is_normalized(tmp_path: Path) -> None:
    settings = Settings(engine_path=_fake_engine(tmp_path), movetime_ms=10)
    sfen = INITIAL_SFEN.replace(" b - 1", " w - 1")
    with YaneuraOuClient(settings, command_timeout=2) as client:
        result = client.analyze(sfen)
    assert result.eval_cp_sente == -235


def test_only_supported_usi_options_are_sent(tmp_path: Path) -> None:
    commands = tmp_path / "commands.txt"
    settings = Settings(
        engine_path=_fake_engine(tmp_path, options=True, record_commands=commands),
        threads=4,
        extra_options="TensorRT_Batch_Size=8;UnknownOption=1",
    )
    with YaneuraOuClient(settings, command_timeout=2) as client:
        client.check_connection()
    sent = commands.read_text(encoding="utf-8")
    assert "setoption name USI_Hash value 1024" in sent
    assert "setoption name MultiPV value 3" in sent
    assert "setoption name TensorRT_Batch_Size value 8" in sent
    assert "setoption name Threads value 4" not in sent
    assert "UnknownOption" not in sent
