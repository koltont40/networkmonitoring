from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from .models import HostRangeRequest, HostRangeResponse, HostStatus
from .monitor import MonitorService, load_hosts
from .settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SNMP Network Monitor", version="0.1.0")
BASE_DIR = Path(__file__).parent.parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


async def get_monitor() -> MonitorService:
    return app.state.monitor  # type: ignore[attr-defined]


@app.on_event("startup")
async def startup_event() -> None:
    config_path = BASE_DIR / "config" / "hosts.yaml"
    hosts = load_hosts(config_path) if config_path.exists() else []
    if not hosts:
        logger.warning("No hosts configured; using demo defaults")
        hosts = load_hosts(Path(__file__).parent / "demo_hosts.yaml")
    monitor = MonitorService(hosts)
    app.state.monitor = monitor
    asyncio.create_task(monitor.start())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    monitor: MonitorService = app.state.monitor  # type: ignore[attr-defined]
    await monitor.stop()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, monitor: Annotated[MonitorService, Depends(get_monitor)]):
    statuses = monitor.get_statuses()
    return TEMPLATES.TemplateResponse(
        "index.html", {"request": request, "statuses": statuses, "settings": settings}
    )


@app.get("/api/hosts", response_model=list[HostStatus])
async def hosts(monitor: Annotated[MonitorService, Depends(get_monitor)]):
    return monitor.get_statuses()


@app.post("/api/rescan")
async def rescan(monitor: Annotated[MonitorService, Depends(get_monitor)]):
    await monitor._check_all_hosts()  # noqa: SLF001
    return {"status": "ok"}


@app.post("/api/hosts", response_model=HostRangeResponse)
async def add_hosts(
    payload: HostRangeRequest, monitor: Annotated[MonitorService, Depends(get_monitor)]
):
    try:
        hosts = monitor.hosts_from_range(
            payload.range,
            community=payload.community,
            snmp_port=payload.snmp_port,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    added = monitor.add_hosts(hosts)
    for host in added:
        await monitor._check_host(host)

    skipped = len(hosts) - len(added)
    return HostRangeResponse(
        added=len(added), skipped=skipped, hosts=[host.address for host in added]
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
