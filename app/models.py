from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field


@dataclass(slots=True)
class HostConfig:
    name: str
    address: str
    snmp_community: str
    snmp_port: int
    interface_index: int = 1


class HostStatus(BaseModel):
    name: str
    address: str
    latency_ms: Optional[float] = None
    latency_min_ms: Optional[float] = None
    latency_max_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None
    packet_success_pct: Optional[float] = None
    packets_sent: Optional[int] = None
    packets_received: Optional[int] = None
    cpu_usage_pct: Optional[float] = None
    memory_used_pct: Optional[float] = None
    interface_temp_c: Optional[float] = None
    system_temp_c: Optional[float] = None
    interface_in_bps: Optional[float] = None
    interface_out_bps: Optional[float] = None
    psu_status: Optional[str] = None
    psu_statuses: list[str] = Field(default_factory=list)
    reachable: bool = False
    last_checked: Optional[datetime] = None
    snmp_sysname: Optional[str] = None
    last_alert: Optional[datetime] = None
    notes: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[misc]
    @property
    def state(self) -> str:
        if not self.last_checked:
            return "pending"
        return "ok" if self.reachable else "alert"

    class Config:
        arbitrary_types_allowed = True


class HostSample(BaseModel):
    """Historical snapshot of a host's health and interface data."""

    timestamp: datetime
    latency_ms: Optional[float] = None
    latency_min_ms: Optional[float] = None
    latency_max_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None
    packet_success_pct: Optional[float] = None
    packets_sent: Optional[int] = None
    packets_received: Optional[int] = None
    cpu_usage_pct: Optional[float] = None
    memory_used_pct: Optional[float] = None
    interface_temp_c: Optional[float] = None
    system_temp_c: Optional[float] = None
    interface_in_bps: Optional[float] = None
    interface_out_bps: Optional[float] = None
    psu_status: Optional[str] = None
    psu_statuses: list[str] = Field(default_factory=list)
    reachable: bool


class HostRangeRequest(BaseModel):
    """Payload for adding a range of hosts from the dashboard."""

    range: str = Field(..., description="CIDR block, start-end pair, or single IP")
    community: Optional[str] = Field(
        None, description="SNMP community string to use for the new hosts"
    )
    snmp_port: Optional[int] = Field(None, description="SNMP port override")


class HostRangeResponse(BaseModel):
    added: int
    skipped: int
    hosts: list[str]


class SettingsPayload(BaseModel):
    monitor_interval_seconds: int
    latency_threshold_ms: float
    packet_loss_threshold_pct: float
    smtp_host: Optional[str]
    smtp_port: int
    smtp_username: Optional[str]
    smtp_password: Optional[str]
    smtp_sender: Optional[str]
    smtp_recipients: list[str]
    slack_webhook_url: Optional[str]
    snmp_community: str
    snmp_port: int


class SettingsUpdate(BaseModel):
    monitor_interval_seconds: Optional[int] = Field(None, ge=5)
    latency_threshold_ms: Optional[float] = Field(None, ge=1)
    packet_loss_threshold_pct: Optional[float] = Field(None, ge=0, le=100)
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_sender: Optional[str] = None
    smtp_recipients: Optional[list[str] | str] = None
    slack_webhook_url: Optional[str] = None
    snmp_community: Optional[str] = None
    snmp_port: Optional[int] = Field(None, ge=1, le=65535)
