"""WildSense entrypoint.

    python run.py                         # everything, per config.yaml
    python run.py --sensor dht22          # force the real DHT22
    python run.py --duration 60           # stop after a minute
    python run.py --no-dashboard          # headless
    python run.py --demo                  # inject one of each event type

Run this from inside the `wildsense/` directory -- the packages (core,
sensors, detectors, ...) are top-level there, which is what keeps the project
self-contained alongside unrelated projects in the same repository.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from types import FrameType

from core.config import Config, load_config
from core.contracts import EventType
from core.logging_setup import configure_logging
from dashboard.app import DashboardServer
from dashboard.state import STATE
from pipeline import WildSensePipeline

log = logging.getLogger("wildsense")

BANNER = r"""
 __        __ _  _      _ ____
 \ \      / /(_)| |  __| / ___|  ___  _ __   ___  ___
  \ \ /\ / / | || | / _` \___ \ / _ \| '_ \ / __|/ _ \
   \ V  V /  | || || (_| |___) |  __/| | | |\__ \  __/
    \_/\_/   |_||_| \__,_|____/ \___||_| |_||___/\___|
   modular edge-AI environmental event detection
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a WildSense node.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument(
        "--sensor", default=None, help="override sensor.active (e.g. synthetic, dht22)"
    )
    parser.add_argument("--duration", type=float, default=None, help="stop after N seconds")
    parser.add_argument("--cycles", type=int, default=None, help="stop after N read cycles")
    parser.add_argument("--interval", type=float, default=None,
                        help="pin every risk level to this polling interval (seconds)")
    parser.add_argument("--no-dashboard", action="store_true", help="run headless")
    parser.add_argument("--no-federation", action="store_true", help="skip federated learning")
    parser.add_argument("--no-cloud", action="store_true", help="skip cloud snapshot sync")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="inject one spike, one drop and one drift on a timer, so a short "
             "recording is guaranteed to contain every event type",
    )
    parser.add_argument("--log-level", default=None, help="DEBUG, INFO, WARNING, ...")
    return parser.parse_args(argv)


def apply_overrides(config_data: dict, args: argparse.Namespace) -> dict:
    """Fold command-line flags into the parsed config tree."""
    if args.sensor:
        config_data.setdefault("sensor", {})["active"] = args.sensor
    if args.no_federation:
        config_data.setdefault("federation", {})["enabled"] = False
    if args.no_dashboard:
        config_data.setdefault("dashboard", {})["enabled"] = False
    if args.no_cloud:
        config_data.setdefault("cloud", {})["enabled"] = False
    if args.interval is not None:
        intervals = config_data.setdefault("context", {}).setdefault("intervals", {})
        for level in ("low", "moderate", "high", "extreme"):
            intervals[level] = args.interval
    if args.log_level:
        config_data.setdefault("logging", {})["level"] = args.log_level
    return config_data


def start_demo_injector(pipeline: WildSensePipeline, stop: threading.Event) -> threading.Thread:
    """Force one of each event type through the synthetic sensor, on a timer.

    Only meaningful in synthetic mode -- there is no way to make real weather
    cooperate with a screen recording.
    """
    sensor = pipeline.sensor
    if not hasattr(sensor, "force_episode"):
        log.warning("--demo needs the synthetic sensor; ignoring it for '%s'.", sensor.name)
        return threading.Thread(target=lambda: None)

    def loop() -> None:
        schedule = [EventType.SPIKE, EventType.DROP, EventType.DRIFT]

        # Wait for the detector to actually be warm, not for a guessed number
        # of seconds. Warmup takes `warmup_samples` cycles, and at a 60s
        # low-risk interval that is over half an hour -- any fixed delay here
        # would inject every episode into a detector that is still refusing to
        # fire, and the demo would record nothing at all.
        while not pipeline.detector.is_warm:
            if stop.wait(1.0):
                return
        log.info("[demo] detector is warm; starting episode injection")

        for index, kind in enumerate(schedule * 4):
            if stop.is_set():
                return
            log.info("[demo] injecting a %s episode", kind.value)
            sensor.force_episode(kind)
            if stop.wait(30.0 if index % 3 != 2 else 45.0):
                return

    thread = threading.Thread(target=loop, name="wildsense-demo", daemon=True)
    thread.start()
    return thread


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    config = load_config(args.config)
    config = Config(apply_overrides(config.as_dict(), args), config.path)
    configure_logging(config.get("logging.level", "INFO"))

    print(BANNER)
    log.info("Config: %s", config.path)

    pipeline = WildSensePipeline(config, state=STATE)

    server: DashboardServer | None = None
    if config.get("dashboard.enabled", True):
        server = DashboardServer(
            host=config.get("dashboard.host", "127.0.0.1"),
            port=int(config.get("dashboard.port", 8000)),
            log_level=config.get("dashboard.log_level", "warning"),
        )
        # start() blocks until the port is genuinely bound, so the URL we print
        # is one that actually answers.
        if server.start():
            log.info("=" * 62)
            log.info("  Dashboard: %s", server.url)
            log.info("=" * 62)
        else:
            server = None  # it already logged why; carry on headless

    stop_demo = threading.Event()
    if args.demo:
        start_demo_injector(pipeline, stop_demo)

    def handle_signal(signum: int, frame: FrameType | None) -> None:
        log.info("Received signal %s, shutting down...", signum)
        stop_demo.set()
        pipeline.stop()

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)

    cycles = 0
    try:
        pipeline.start()
        cycles = pipeline.run(duration_s=args.duration, max_cycles=args.cycles)
    except KeyboardInterrupt:
        log.info("Interrupted.")
    finally:
        stop_demo.set()
        pipeline.stop()
        if server is not None:
            server.stop()

    snapshot = STATE.snapshot(reading_limit=1, event_limit=1)
    log.info(
        "Stopped after %d cycles: %d readings, %d events.",
        cycles,
        snapshot["counters"]["readings"],
        snapshot["counters"]["events"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
