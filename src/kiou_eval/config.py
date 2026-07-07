"""アプリケーション設定。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENGINE_PATH = Path(
    r"C:\Apps\YaneuraOu-Deep-ORT-CPU_V940\YaneuraOu-Deep-ORT-CPU.exe"
)


class Settings(BaseSettings):
    """環境変数と.envから読み込む設定。

    CLI値は ``with_overrides`` で最後に適用する。
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    engine_path: Path = Field(DEFAULT_ENGINE_PATH, validation_alias="YANEAURAOU_ENGINE_PATH")
    hash_mb: int = Field(1024, ge=1, validation_alias="YANEAURAOU_HASH_MB")
    threads: int = Field(4, ge=0, validation_alias="YANEAURAOU_THREADS")
    multipv: int = Field(3, ge=1, validation_alias="YANEAURAOU_MULTIPV")
    movetime_ms: int = Field(500, ge=1, validation_alias="YANEAURAOU_MOVETIME_MS")
    command_timeout_sec: float = Field(
        15.0, ge=1.0, validation_alias="YANEAURAOU_COMMAND_TIMEOUT_SEC"
    )
    extra_options: str = Field("", validation_alias="YANEAURAOU_EXTRA_OPTIONS")
    server_host: str = Field("127.0.0.1", validation_alias="SERVER_HOST")
    server_port: int = Field(8765, ge=1, le=65535, validation_alias="SERVER_PORT")

    def with_overrides(self, **values: Any) -> Settings:
        """None以外のCLI設定を上書きしたコピーを返す。"""
        overrides = {key: value for key, value in values.items() if value is not None}
        return self.model_copy(update=overrides)
