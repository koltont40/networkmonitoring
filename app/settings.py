from __future__ import annotations

from pydantic_settings import BaseSettings


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


settings = Settings()
