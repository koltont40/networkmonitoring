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


class HostStatus(BaseModel):
    name: str
    address: str
    latency_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None
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
