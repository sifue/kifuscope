from pathlib import Path

from kiou_eval.config import Settings


def test_settings_environment_priority(monkeypatch) -> None:
    monkeypatch.setenv("YANEAURAOU_ENGINE_PATH", "/tmp/from-env")
    settings = Settings()
    assert settings.engine_path == Path("/tmp/from-env")


def test_threads_can_be_disabled() -> None:
    settings = Settings(threads=0)
    assert settings.threads == 0


def test_cli_override_copy() -> None:
    settings = Settings(server_port=8765)
    overridden = settings.with_overrides(server_port=9000, server_host=None)
    assert overridden.server_port == 9000
    assert overridden.server_host == "127.0.0.1"
