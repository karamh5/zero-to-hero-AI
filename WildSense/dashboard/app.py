"""FastAPI dashboard: one live page plus the JSON endpoint that feeds it.

The page polls `/api/state` on an interval rather than holding a websocket.
That is a deliberate simplification: there is one client (whoever is watching
or recording), the payload is a few kilobytes, and polling has no reconnect
logic to get wrong halfway through a screen recording.

Run it as part of the pipeline:

    python run.py

Or standalone, against whatever state exists:

    uvicorn dashboard.app:app --port 8000
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from dashboard.state import STATE, DashboardState

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


def create_app(state: DashboardState | None = None) -> FastAPI:
    """Build the FastAPI app around a `DashboardState`."""
    state = state or STATE
    application = FastAPI(title="WildSense", docs_url=None, redoc_url=None)

    @application.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(INDEX_HTML)

    @application.get("/api/state")
    def api_state() -> JSONResponse:
        """Everything the live page renders. Polled once a second."""
        return JSONResponse(state.snapshot())

    @application.get("/api/health")
    def api_health() -> dict:
        snapshot = state.snapshot(reading_limit=1, event_limit=1)
        return {
            "status": "ok",
            "uptime_s": snapshot["uptime_s"],
            "readings": snapshot["counters"]["readings"],
            "events": snapshot["counters"]["events"],
        }

    return application


#: Module-level app so `uvicorn dashboard.app:app` works.
app = create_app()


class DashboardServer:
    """Runs uvicorn on a background thread alongside the sensor loop."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, log_level: str = "warning"):
        self.host = host
        self.port = int(port)
        self.log_level = log_level
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        # 0.0.0.0 is a bind address, not something you can click.
        display_host = "127.0.0.1" if self.host in ("0.0.0.0", "::") else self.host
        return f"http://{display_host}:{self.port}"

    def start(self, wait_timeout: float = 10.0) -> bool:
        """Start uvicorn and wait until it has actually bound the port.

        Returns True only once the server is genuinely serving. Reporting
        "live" the instant the thread is spawned is worse than useless: if the
        port is already taken, uvicorn logs a bind error on its own thread and
        gives up, while the node cheerfully prints a URL that answers nothing.
        A dashboard that fails to start is not fatal -- detection carries on --
        but it has to be *said*.
        """
        if self._thread is not None and self._thread.is_alive():
            return True

        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level=self.log_level,
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run, name="wildsense-dashboard", daemon=True
        )
        self._thread.start()

        deadline = time.monotonic() + wait_timeout
        while time.monotonic() < deadline:
            if self._server.started:
                log.info("Dashboard live at %s", self.url)
                return True
            if not self._thread.is_alive():
                break  # uvicorn gave up (almost always: port in use)
            time.sleep(0.05)

        log.error(
            "Dashboard failed to start on %s:%d -- is that port already in use? "
            "Detection continues without it; use --no-dashboard to silence this, "
            "or change dashboard.port in config.yaml.",
            self.host,
            self.port,
        )
        self.stop()
        return False

    def stop(self, timeout: float = 5.0) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        self._server = None
