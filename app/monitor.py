from __future__ import annotations

import asyncio
import ipaddress
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from pythonping import ping
from pysnmp.hlapi import (  # type: ignore
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    getCmd,
)

from .models import HostConfig, HostSample, HostStatus
from .notifications import NotificationManager
from .settings import settings

logger = logging.getLogger(__name__)


def load_hosts(config_path: Path) -> list[HostConfig]:
    """Load hosts from a YAML file with keys name, address and optional SNMP settings."""
    import yaml

    with config_path.open("r", encoding="utf-8") as handle:
        raw_hosts = yaml.safe_load(handle) or []
    hosts: list[HostConfig] = []
    for entry in raw_hosts:
        hosts.append(
            HostConfig(
                name=entry.get("name"),
                address=entry.get("address"),
                snmp_community=entry.get("snmp_community", settings.snmp_community),
                snmp_port=int(entry.get("snmp_port", settings.snmp_port)),
                interface_index=int(entry.get("interface_index", 1)),
            )
        )
    return hosts


class MonitorService:
    def __init__(self, hosts: Iterable[HostConfig]):
        self.hosts = list(hosts)
        self.statuses: dict[str, HostStatus] = {
            host.address: HostStatus(name=host.name, address=host.address) for host in self.hosts
        }
        self.history: dict[str, list[HostSample]] = {host.address: [] for host in self.hosts}
        self._task: asyncio.Task | None = None
        self.notifications = NotificationManager()
        self._previous_counters: dict[str, tuple[int, int, datetime, int]] = {}

    def get_statuses(self, reachable_only: bool = False) -> list[HostStatus]:
        statuses = list(self.statuses.values())
        if reachable_only:
            return [status for status in statuses if status.reachable]
        return statuses

    def get_status(self, address: str) -> HostStatus | None:
        return self.statuses.get(address)

    def get_history(self, address: str) -> list[HostSample]:
        return self.history.get(address, [])

    async def start(self) -> None:
        if self._task:
            return
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
            self._task = None

    async def _run_loop(self) -> None:
        logger.info("Starting monitoring loop for %d hosts", len(self.hosts))
        while True:
            await self._check_all_hosts()
            await asyncio.sleep(settings.monitor_interval_seconds)

    async def _check_all_hosts(self) -> None:
        for host in self.hosts:
            await self._check_host(host)

    def expand_range(self, range_text: str) -> list[str]:
        """Expand CIDR, start-end pairs, or single IPs into a list of addresses."""

        cleaned = range_text.strip()
        if "-" in cleaned:
            start_raw, end_raw = [part.strip() for part in cleaned.split("-", 1)]
            start_ip = ipaddress.ip_address(start_raw)
            end_ip = ipaddress.ip_address(end_raw)
            if start_ip.version != end_ip.version or int(end_ip) < int(start_ip):
                raise ValueError("Invalid IP range ordering")
            distance = int(end_ip) - int(start_ip)
            return [str(ipaddress.ip_address(int(start_ip) + offset)) for offset in range(distance + 1)]

        try:
            network = ipaddress.ip_network(cleaned, strict=False)
            return [str(host) for host in network.hosts()] or [str(network.network_address)]
        except ValueError:
            # fall back to single IP
            ipaddress.ip_address(cleaned)
            return [cleaned]

    def add_hosts(self, hosts: Iterable[HostConfig]) -> list[HostConfig]:
        """Add hosts to the monitor, skipping duplicates."""

        added: list[HostConfig] = []
        for host in hosts:
            if host.address in self.statuses:
                continue
            self.hosts.append(host)
            self.statuses[host.address] = HostStatus(name=host.name, address=host.address)
            self.history.setdefault(host.address, [])
            added.append(host)
        return added

    def remove_host(self, address: str) -> bool:
        """Remove a host from monitoring. Returns True if it existed."""

        removed = self.statuses.pop(address, None)
        if not removed:
            return False
        self.hosts = [host for host in self.hosts if host.address != address]
        self.history.pop(address, None)
        self._previous_counters.pop(address, None)
        return True

    def hosts_from_range(
        self,
        range_text: str,
        community: str | None = None,
        snmp_port: int | None = None,
        interface_index: int | None = None,
    ) -> list[HostConfig]:
        addresses = self.expand_range(range_text)
        community_value = community or settings.snmp_community
        snmp_port_value = snmp_port or settings.snmp_port
        interface_index_value = interface_index or 1
        return [
            HostConfig(
                name=address,
                address=address,
                snmp_community=community_value,
                snmp_port=snmp_port_value,
                interface_index=interface_index_value,
            )
            for address in addresses
        ]

    async def _check_host(self, host: HostConfig) -> None:
        status = self.statuses[host.address]
        now = datetime.utcnow()
        try:
            result = await asyncio.to_thread(ping, host.address, count=3, timeout=2)
            status.latency_ms = result.rtt_avg_ms
            status.latency_min_ms = getattr(result, "rtt_min_ms", None)
            status.latency_max_ms = getattr(result, "rtt_max_ms", None)
            status.packet_loss_pct = result.packet_loss * 100
            status.packets_sent = getattr(result, "stats_packets_sent", None)
            status.packets_received = getattr(result, "stats_packets_returned", None)
            if status.packet_loss_pct is not None:
                status.packet_success_pct = max(0.0, 100.0 - status.packet_loss_pct)
            elif status.packets_sent:
                status.packet_success_pct = (
                    100.0 * status.packets_received / status.packets_sent
                    if status.packets_received is not None
                    else None
                )
            status.reachable = result.success()
            status.notes = []

            if status.packet_loss_pct and status.packet_loss_pct > settings.packet_loss_threshold_pct:
                status.notes.append(f"High packet loss: {status.packet_loss_pct:.1f}%")
            if status.latency_ms and status.latency_ms > settings.latency_threshold_ms:
                status.notes.append(f"High latency: {status.latency_ms:.1f} ms")

            status.snmp_sysname = await asyncio.to_thread(self._fetch_sysname, host)
            status.cpu_usage_pct, status.memory_used_pct = await asyncio.to_thread(
                self._fetch_health_metrics, host
            )
            (
                status.interface_temp_c,
                status.system_temp_c,
                status.psu_statuses,
            ) = await asyncio.to_thread(self._fetch_environment_metrics, host)
            status.psu_status = ", ".join(status.psu_statuses) if status.psu_statuses else None
            (
                status.interface_in_bps,
                status.interface_out_bps,
            ) = await asyncio.to_thread(self._fetch_interface_throughput, host, now)
        except Exception as exc:  # pragma: no cover - network dependent
            status.reachable = False
            status.latency_ms = None
            status.latency_min_ms = None
            status.latency_max_ms = None
            status.packet_loss_pct = None
            status.packet_success_pct = None
            status.packets_sent = None
            status.packets_received = None
            status.cpu_usage_pct = None
            status.memory_used_pct = None
            status.interface_temp_c = None
            status.system_temp_c = None
            status.interface_in_bps = None
            status.interface_out_bps = None
            status.psu_status = None
            status.psu_statuses = []
            status.notes = [f"Error checking host: {exc}"]
        status.last_checked = now

        self._record_sample(status, now)
        await self._maybe_notify(status)

    def _record_sample(self, status: HostStatus, timestamp: datetime) -> None:
        samples = self.history.setdefault(status.address, [])
        samples.append(
            HostSample(
                timestamp=timestamp,
                latency_ms=status.latency_ms,
                latency_min_ms=status.latency_min_ms,
                latency_max_ms=status.latency_max_ms,
                packet_loss_pct=status.packet_loss_pct,
                packet_success_pct=status.packet_success_pct,
                packets_sent=status.packets_sent,
                packets_received=status.packets_received,
                cpu_usage_pct=status.cpu_usage_pct,
                memory_used_pct=status.memory_used_pct,
                interface_temp_c=status.interface_temp_c,
                system_temp_c=status.system_temp_c,
                interface_in_bps=status.interface_in_bps,
                interface_out_bps=status.interface_out_bps,
                psu_status=status.psu_status,
                psu_statuses=status.psu_statuses,
                reachable=status.reachable,
            )
        )
        max_samples = 200
        if len(samples) > max_samples:
            del samples[:-max_samples]


    def _community(self, host: HostConfig) -> CommunityData:
        """Return SNMP v2c community settings for a host."""

        return CommunityData(host.snmp_community, mpModel=1)

    def _fetch_sysname(self, host: HostConfig) -> str | None:
        try:
            iterator = getCmd(
                SnmpEngine(),
                self._community(host),
                UdpTransportTarget((host.address, host.snmp_port), timeout=2, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity("SNMPv2-MIB", "sysName", 0)),
            )
            error_indication, error_status, error_index, var_binds = next(iterator)
            if error_indication or error_status:
                return None
            for _, value in var_binds:
                return str(value)
        except Exception:
            return None
        return None

    def _fetch_health_metrics(self, host: HostConfig) -> tuple[float | None, float | None]:
        """Fetch CPU idle, total, and available memory to derive health stats."""

        cpu_idle_oid = ObjectIdentity("1.3.6.1.4.1.2021.11.9.0")  # ssCpuIdle
        mem_total_oid = ObjectIdentity("1.3.6.1.4.1.2021.4.5.0")  # memTotalReal
        mem_avail_oid = ObjectIdentity("1.3.6.1.4.1.2021.4.6.0")  # memAvailReal

        try:
            iterator = getCmd(
                SnmpEngine(),
                self._community(host),
                UdpTransportTarget((host.address, host.snmp_port), timeout=2, retries=0),
                ContextData(),
                ObjectType(cpu_idle_oid),
                ObjectType(mem_total_oid),
                ObjectType(mem_avail_oid),
            )
            error_indication, error_status, error_index, var_binds = next(iterator)
            if error_indication or error_status:
                return None, None

            values: dict[str, float] = {}
            for var_bind in var_binds:
                oid, value = var_bind
                values[str(oid)] = float(value)

            cpu_idle = values.get(str(cpu_idle_oid.getOid()))
            mem_total = values.get(str(mem_total_oid.getOid()))
            mem_avail = values.get(str(mem_avail_oid.getOid()))

            cpu_usage = 100.0 - cpu_idle if cpu_idle is not None else None
            memory_used_pct = (
                ((mem_total - mem_avail) / mem_total) * 100 if mem_total else None
            )
            return cpu_usage, memory_used_pct
        except Exception:
            return None, None

    def _fetch_environment_metrics(
        self, host: HostConfig
    ) -> tuple[float | None, float | None, list[str]]:
        """Fetch interface + system temperatures and PSU status via best-effort SNMP."""

        interface_temp_oids = [
            ObjectIdentity(
                f"1.3.6.1.4.1.2021.13.16.2.1.3.{host.interface_index}"
            ),  # lmTempSensorsValue.{idx}
            ObjectIdentity(
                f"1.3.6.1.2.1.99.1.1.1.4.{host.interface_index}"
            ),  # entPhySensorValue.{idx}
        ]
        system_temp_oids = [
            ObjectIdentity("1.3.6.1.4.1.2021.13.16.2.1.3.2"),  # lmTempSensorsValue.2
            ObjectIdentity("1.3.6.1.2.1.99.1.1.1.4.2"),  # entPhySensorValue.2
        ]
        psu_oid_templates = [
            "1.3.6.1.2.1.25.3.2.1.5.{index}",  # hrDeviceStatus.{index}
            "1.3.6.1.2.1.33.1.2.2.1.4.{index}",  # upsOutputSource.{index}
        ]

        def _first_value(identities: list[ObjectIdentity]) -> float | int | str | None:
            for oid in identities:
                try:
                    iterator = getCmd(
                        SnmpEngine(),
                        self._community(host),
                        UdpTransportTarget((host.address, host.snmp_port), timeout=2, retries=0),
                        ContextData(),
                        ObjectType(oid),
                    )
                    error_indication, error_status, _error_index, var_binds = next(iterator)
                    if error_indication or error_status:
                        continue
                    for _, value in var_binds:
                        return value  # type: ignore[return-value]
                except Exception:
                    continue
            return None

        raw_interface_temp = _first_value(interface_temp_oids)
        interface_temp_c = None
        if raw_interface_temp is not None:
            try:
                interface_temp_c = float(raw_interface_temp)
            except (TypeError, ValueError):
                interface_temp_c = None

        raw_system_temp = _first_value(system_temp_oids)
        system_temp_c = None
        if raw_system_temp is not None:
            try:
                system_temp_c = float(raw_system_temp)
            except (TypeError, ValueError):
                system_temp_c = None

        psu_statuses: list[str] = []

        def _decode_psu(value: float | int | str | None) -> str | None:
            if value is None:
                return None
            try:
                psu_state = int(value)
                psu_status_map = {
                    1: "unknown",
                    2: "ok",
                    3: "warning",
                    4: "testing",
                    5: "down",
                }
                return psu_status_map.get(psu_state, str(psu_state))
            except (TypeError, ValueError):
                return str(value)

        for index in (1, 2):
            psu_oids = [ObjectIdentity(oid.format(index=index)) for oid in psu_oid_templates]
            status_value = _decode_psu(_first_value(psu_oids))
            if status_value is None:
                continue

            if index == 2 and status_value == "unknown":
                continue

            psu_statuses.append(f"PSU{index}: {status_value}")

        return interface_temp_c, system_temp_c, psu_statuses

    def _fetch_interface_throughput(
        self, host: HostConfig, now: datetime
    ) -> tuple[float | None, float | None]:
        """Compute interface throughput in bits per second using counter deltas."""

        high_cap_in = ObjectIdentity(
            f"1.3.6.1.2.1.31.1.1.1.6.{host.interface_index}"
        )
        high_cap_out = ObjectIdentity(
            f"1.3.6.1.2.1.31.1.1.1.10.{host.interface_index}"
        )
        legacy_in = ObjectIdentity(f"1.3.6.1.2.1.2.2.1.10.{host.interface_index}")
        legacy_out = ObjectIdentity(f"1.3.6.1.2.1.2.2.1.16.{host.interface_index}")

        def _fetch_counters(oids: list[ObjectIdentity]) -> dict[str, int]:
            iterator = getCmd(
                SnmpEngine(),
                self._community(host),
                UdpTransportTarget((host.address, host.snmp_port), timeout=2, retries=0),
                ContextData(),
                *(ObjectType(oid) for oid in oids),
            )
            counters: dict[str, int] = {}
            error_indication, error_status, _error_index, var_binds = next(iterator)
            if error_indication or error_status:
                return counters
            for oid, value in var_binds:
                try:
                    counters[str(oid)] = int(value)
                except (TypeError, ValueError):
                    continue
            return counters

        try:
            values = _fetch_counters([high_cap_in, high_cap_out])
            counter_mod = 2**64

            if not values:
                values = _fetch_counters([legacy_in, legacy_out])
                counter_mod = 2**32

            in_octets = values.get(str(high_cap_in.getOid())) or values.get(
                str(legacy_in.getOid())
            )
            out_octets = values.get(str(high_cap_out.getOid())) or values.get(
                str(legacy_out.getOid())
            )
            if in_octets is None or out_octets is None:
                return None, None

            previous = self._previous_counters.get(host.address)
            self._previous_counters[host.address] = (in_octets, out_octets, now, counter_mod)
            if not previous:
                return None, None

            prev_in, prev_out, prev_time, prev_mod = previous
            elapsed = (now - prev_time).total_seconds()
            if elapsed <= 0:
                return None, None

            def _compute_rate(current: int, previous_value: int, modulus: int) -> float | None:
                if current < previous_value:
                    current += modulus
                if current < previous_value:
                    return None
                return ((current - previous_value) * 8) / elapsed

            return (
                _compute_rate(in_octets, prev_in, prev_mod),
                _compute_rate(out_octets, prev_out, prev_mod),
            )
        except Exception:
            return None, None

    async def _maybe_notify(self, status: HostStatus) -> None:
        """Send alerts when a host enters an alerting state or recovers."""
        threshold_exceeded = not status.reachable or any(status.notes)
        now = datetime.utcnow()
        should_alert = False
        if threshold_exceeded:
            if not status.last_alert or now - status.last_alert > timedelta(minutes=5):
                should_alert = True
                status.last_alert = now
        else:
            if status.last_alert:
                should_alert = True
                status.last_alert = None

        if not should_alert:
            return

        subject_prefix = "RECOVERY" if status.reachable and not threshold_exceeded else "ALERT"
        subject = f"{subject_prefix}: {status.name} ({status.address})"
        details = "; ".join(status.notes) if status.notes else "Host recovered"
        body = (
            f"Host: {status.name} ({status.address})\n"
            f"Status: {status.state}\n"
            f"Latency: {status.latency_ms or 'n/a'} ms\n"
            f"Packet loss: {status.packet_loss_pct or 'n/a'}%\n"
            f"Notes: {details}\n"
        )

        self.notifications.send_email(subject, body)
        await self.notifications.send_slack(f"{subject}\n{details}")
