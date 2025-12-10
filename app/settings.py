from __future__ import annotations

from pathlib import Path
import json

from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).parent.parent
SETTINGS_PATH = BASE_DIR / "config" / "settings.json"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or defaults."""

    monitor_interval_seconds: int = 30
    latency_threshold_ms: float = 150.0
    packet_loss_threshold_pct: float = 30.0

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str | None = None
    smtp_recipients: list[str] = []

    slack_webhook_url: str | None = None

    snmp_community: str = "public"
    snmp_port: int = 161

    class Config:
        env_prefix = "MONITOR_"
        case_sensitive = False

    def apply_overrides(self, overrides: dict) -> None:
        """Update settings attributes from a dict of overrides."""

        for field in self.model_fields:
            if field not in overrides:
                continue
            value = overrides[field]
            setattr(self, field, value)

    def to_storage(self) -> dict:
        """Return a dict safe for writing to disk."""

        return self.model_dump()


def load_settings() -> Settings:
    settings = Settings()
    if SETTINGS_PATH.exists():
        with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
            overrides = json.load(handle)
        settings.apply_overrides(overrides)
    return settings


def persist_settings(settings: Settings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(settings.to_storage(), handle, indent=2)


settings = load_settings()
