"""Cloud sync tests -- the point is that missing credentials are harmless."""

from __future__ import annotations

import json
import time

from cloud.s3_sync import S3EventSync
from core.contracts import Event, EventType


def sample_event(timestamp: float = 1_767_225_600.0) -> Event:
    return Event(
        timestamp=timestamp,
        event_type=EventType.SPIKE,
        confidence=0.91,
        temperature_c=41.2,
        humidity_pct=17.5,
        z_temperature=6.4,
        z_humidity=-3.1,
        node_id="wildsense-test",
        detector="env_anomaly",
        detail="spike via model",
    )


def drain(sync: S3EventSync, timeout: float = 3.0) -> None:
    """Wait for the worker thread to finish the queue."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if sync.status()["queued"] == 0:
            time.sleep(0.1)  # let the in-flight item finish writing
            return
        time.sleep(0.02)


class TestAvailability:
    def test_no_bucket_means_unavailable_with_a_clear_reason(self, monkeypatch, tmp_path):
        monkeypatch.delenv("WILDSENSE_S3_BUCKET", raising=False)
        sync = S3EventSync(enabled=True, bucket=None, local_fallback_dir=str(tmp_path))

        assert sync.available is False
        assert "no bucket configured" in sync.status()["reason"]
        assert "Detection continues normally" in sync.describe()

    def test_disabled_sync_says_so(self, tmp_path):
        sync = S3EventSync(enabled=False, local_fallback_dir=str(tmp_path))
        assert sync.available is False
        assert sync.describe() == "Cloud sync disabled in config."

    def test_bucket_can_come_from_the_environment(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WILDSENSE_S3_BUCKET", "from-env-bucket")
        sync = S3EventSync(enabled=True, bucket=None, local_fallback_dir=str(tmp_path))
        assert sync.bucket == "from-env-bucket"

    def test_missing_credentials_do_not_raise(self, monkeypatch, tmp_path):
        """The whole contract: no creds, no crash."""
        for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
                     "AWS_PROFILE", "AWS_SHARED_CREDENTIALS_FILE"):
            monkeypatch.delenv(name, raising=False)
        # Point boto3 at an empty config dir so no ambient profile is found.
        monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "nope"))
        monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "nope-either"))

        sync = S3EventSync(enabled=True, bucket="some-bucket", local_fallback_dir=str(tmp_path))
        sync.start()
        assert sync.publish(sample_event()) is True
        drain(sync)
        sync.stop()
        # Either it found no credentials, or the environment genuinely has some.
        assert isinstance(sync.available, bool)


class TestLocalFallback:
    def test_events_are_written_locally_when_s3_is_unavailable(self, monkeypatch, tmp_path):
        monkeypatch.delenv("WILDSENSE_S3_BUCKET", raising=False)
        sync = S3EventSync(enabled=True, bucket=None, local_fallback_dir=str(tmp_path))
        sync.start()
        sync.publish(sample_event())
        drain(sync)
        sync.stop()

        written = list(tmp_path.rglob("*.json"))
        assert len(written) == 1

        payload = json.loads(written[0].read_text(encoding="utf-8"))
        assert payload["event_type"] == "spike"
        assert payload["node_id"] == "wildsense-test"
        assert payload["temperature_c"] == 41.2
        assert "iso_time" in payload

    def test_the_key_path_is_date_partitioned(self, monkeypatch, tmp_path):
        monkeypatch.delenv("WILDSENSE_S3_BUCKET", raising=False)
        sync = S3EventSync(
            enabled=True, bucket=None, prefix="events", local_fallback_dir=str(tmp_path)
        )
        sync.start()
        sync.publish(sample_event())
        drain(sync)
        sync.stop()

        written = list(tmp_path.rglob("*.json"))[0]
        relative = written.relative_to(tmp_path).as_posix()
        assert relative.startswith("events/")
        assert relative.count("/") == 4, f"expected events/YYYY/MM/DD/file.json, got {relative}"

    def test_fallback_can_be_switched_off(self, monkeypatch, tmp_path):
        monkeypatch.delenv("WILDSENSE_S3_BUCKET", raising=False)
        sync = S3EventSync(enabled=True, bucket=None, local_fallback_dir=None)
        sync.start()
        sync.publish(sample_event())
        drain(sync)
        sync.stop()
        assert list(tmp_path.rglob("*.json")) == []


class TestQueueing:
    def test_publish_on_a_disabled_sync_is_a_no_op(self, tmp_path):
        sync = S3EventSync(enabled=False, local_fallback_dir=str(tmp_path))
        assert sync.publish(sample_event()) is False

    def test_publishing_never_blocks_even_when_the_queue_overflows(self, monkeypatch, tmp_path):
        monkeypatch.delenv("WILDSENSE_S3_BUCKET", raising=False)
        # Never started, so nothing drains the queue.
        sync = S3EventSync(
            enabled=True, bucket=None, queue_size=3, local_fallback_dir=str(tmp_path)
        )

        started = time.monotonic()
        results = [sync.publish(sample_event(1_767_225_600.0 + i)) for i in range(50)]
        elapsed = time.monotonic() - started

        assert all(results), "a full queue must drop, not refuse"
        assert elapsed < 1.0, "publish must never block the sensor loop"
        assert sync.status()["queued"] <= 3

    def test_status_is_json_serialisable(self, monkeypatch, tmp_path):
        monkeypatch.delenv("WILDSENSE_S3_BUCKET", raising=False)
        sync = S3EventSync(enabled=True, bucket=None, local_fallback_dir=str(tmp_path))
        json.dumps(sync.status())  # must not raise
