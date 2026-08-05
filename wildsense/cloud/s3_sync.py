"""S3 event snapshot sync -- optional, non-blocking, and never fatal.

Design rules, in priority order:

1. **Never crash the node.** A field node that dies because an S3 bucket was
   misconfigured is worse than one that quietly keeps detecting. Every failure
   path here logs and continues.
2. **Never block the sensor loop.** Uploads go through a bounded queue drained
   by a daemon thread. If the network stalls, readings keep flowing; the queue
   fills and drops the oldest pending snapshot rather than backing up.
3. **Say clearly what happened at startup.** One log line stating whether sync
   is on, and if not, exactly why.

Credentials come from the standard boto3 chain (env vars, ~/.aws/credentials,
instance role). Nothing is ever read from `config.yaml`, so no secret can be
committed by accident.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT
from core.contracts import Event

log = logging.getLogger(__name__)


class S3EventSync:
    """Uploads event snapshots to S3 as JSON, degrading to local files.

    Args:
        enabled: master switch from config.
        bucket: target bucket. Falls back to `$WILDSENSE_S3_BUCKET`.
        prefix: key prefix; a `YYYY/MM/DD/` path is appended automatically.
        region: AWS region name; falls back to the boto3 default chain.
        local_fallback_dir: when S3 is unavailable, write snapshots here
            instead so a demo still produces artifacts. Set to None to disable.
        queue_size: bounded upload backlog.
    """

    def __init__(
        self,
        enabled: bool = True,
        bucket: str | None = None,
        prefix: str = "events",
        region: str | None = None,
        local_fallback_dir: str | None = "events",
        queue_size: int = 200,
    ) -> None:
        self.enabled = bool(enabled)
        self.bucket = bucket or os.environ.get("WILDSENSE_S3_BUCKET") or None
        self.prefix = prefix.strip("/")
        self.region = region or os.environ.get("AWS_DEFAULT_REGION")

        self.local_fallback_dir = (
            (PROJECT_ROOT / local_fallback_dir) if local_fallback_dir else None
        )

        self._client: Any = None
        self._reason = "disabled in config"
        self._queue: queue.Queue[Event] = queue.Queue(maxsize=queue_size)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._uploaded = 0
        self._failed = 0
        self._saved_locally = 0

        if self.enabled:
            self._probe()

    # -- availability ------------------------------------------------------

    def _probe(self) -> None:
        """Work out whether real uploads are possible, and record why not."""
        if not self.bucket:
            self._reason = (
                "no bucket configured (set cloud.bucket in config.yaml or the "
                "WILDSENSE_S3_BUCKET environment variable)"
            )
            return

        try:
            import boto3  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            self._reason = f"boto3 is not installed ({exc})"
            return

        try:
            session = boto3.session.Session(region_name=self.region)
            if session.get_credentials() is None:
                self._reason = (
                    "no AWS credentials found (set AWS_ACCESS_KEY_ID and "
                    "AWS_SECRET_ACCESS_KEY, or configure a profile)"
                )
                return
            self._client = session.client("s3")
            self._reason = ""
        except Exception as exc:  # noqa: BLE001
            self._reason = f"could not create an S3 client ({exc})"

    @property
    def available(self) -> bool:
        """True when snapshots will actually reach S3."""
        return self.enabled and self._client is not None

    def describe(self) -> str:
        """The one line printed at startup."""
        if not self.enabled:
            return "Cloud sync disabled in config."
        if self.available:
            return f"Cloud sync enabled -> s3://{self.bucket}/{self.prefix}/"
        target = (
            f" Snapshots will be written to {self.local_fallback_dir} instead."
            if self.local_fallback_dir
            else ""
        )
        return f"Cloud sync unavailable: {self._reason}.{target} Detection continues normally."

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Begin draining the upload queue. Safe to call when unavailable."""
        log.info(self.describe())
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, name="wildsense-s3", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    # -- publishing --------------------------------------------------------

    def publish(self, event: Event) -> bool:
        """Queue an event snapshot. Returns False if it was dropped.

        Never raises, never blocks.
        """
        if not self.enabled:
            return False
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            # Drop the oldest so the newest (most relevant) snapshot survives.
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(event)
                log.warning("Upload queue full; discarded the oldest pending snapshot.")
                return True
            except (queue.Empty, queue.Full):
                log.warning("Upload queue full; dropped an event snapshot.")
                return False

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                event = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._deliver(event)
            except Exception as exc:  # noqa: BLE001 - the worker must never die
                self._failed += 1
                log.warning("Event snapshot delivery failed: %s", exc)
            finally:
                self._queue.task_done()

    def _deliver(self, event: Event) -> None:
        payload = json.dumps(event.to_dict(), indent=2).encode("utf-8")
        key = self._key_for(event)

        if not self.available:
            self._write_local(key, payload)
            return

        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=payload,
                ContentType="application/json",
            )
            self._uploaded += 1
            log.info("Uploaded event snapshot -> s3://%s/%s", self.bucket, key)
        except Exception as exc:  # noqa: BLE001
            # A transient S3 failure should not lose the snapshot entirely.
            self._failed += 1
            log.warning("S3 upload failed (%s); falling back to local storage.", exc)
            self._write_local(key, payload)

    def _key_for(self, event: Event) -> str:
        stamp = datetime.fromtimestamp(event.timestamp, tz=timezone.utc)
        return (
            f"{self.prefix}/{stamp:%Y/%m/%d}/"
            f"{event.node_id}-{stamp:%H%M%S}-{event.event_type.value}.json"
        )

    def _write_local(self, key: str, payload: bytes) -> None:
        if self.local_fallback_dir is None:
            return
        destination = Path(self.local_fallback_dir) / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        self._saved_locally += 1
        log.debug("Wrote event snapshot -> %s", destination)

    # -- introspection -----------------------------------------------------

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "available": self.available,
            "bucket": self.bucket,
            "prefix": self.prefix,
            "reason": self._reason,
            "uploaded": self._uploaded,
            "saved_locally": self._saved_locally,
            "failed": self._failed,
            "queued": self._queue.qsize(),
        }
