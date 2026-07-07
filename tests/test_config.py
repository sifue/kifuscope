from pathlib import Path

from kiou_eval.config import Settings


def _clean_env(monkeypatch) -> None:
    for name in (
        "YANEAURAOU_ENGINE_PATH",
        "YANEAURAOU_HASH_MB",
        "YANEAURAOU_THREADS",
        "YANEAURAOU_MULTIPV",
        "YANEAURAOU_MOVETIME_MS",
        "YANEAURAOU_COMMAND_TIMEOUT_SEC",
        "YANEAURAOU_EXTRA_OPTIONS",
        "SERVER_HOST",
        "SERVER_PORT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_settings_environment_priority(monkeypatch) -> None:
    monkeypatch.setenv("YANEAURAOU_ENGINE_PATH", "/tmp/from-env")
    settings = Settings()
    assert settings.engine_path == Path("/tmp/from-env")


def test_threads_can_be_disabled() -> None:
    settings = Settings(threads=0)
    assert settings.threads == 0


def test_threads_default_is_disabled_for_deep_engines(monkeypatch, tmp_path: Path) -> None:
    _clean_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    settings = Settings()
    assert settings.threads == 0


def test_command_timeout_can_be_extended() -> None:
    settings = Settings(command_timeout_sec=180)
    assert settings.command_timeout_sec == 180


def test_cli_override_copy() -> None:
    settings = Settings(server_port=8765)
    overridden = settings.with_overrides(server_port=9000, server_host=None)
    assert overridden.server_port == 9000
    assert overridden.server_host == "127.0.0.1"
