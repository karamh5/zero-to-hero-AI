"""DHT22 sensor pack -- the one real hardware implementation today.

Wiring (3-wire module with an onboard pull-up resistor, single data pin):

    DHT22 module        Raspberry Pi
    ------------        ------------
    VCC / +             3V3   (pin 1)
    DATA / OUT          GPIO4 (pin 7)   <- board.D4
    GND / -             GND   (pin 6)

This is a one-wire protocol, NOT I2C: there is nothing to detect with
`i2cdetect`, and no address to configure. The bare 4-pin sensor would need a
10k pull-up between VCC and DATA, but the 3-wire module already has one on
board, so no extra components are required.

Two quirks of this part drive the whole design of this file:

1. **Reads fail routinely.** The DHT22 is bit-banged with microsecond timing
   from a non-realtime OS. Linux scheduling jitter corrupts the pulse train
   often enough that `adafruit_dht` raises `RuntimeError` on a large fraction
   of reads ("Checksum did not validate", "A full buffer was not returned").
   This is normal, not a fault. It must be retried, never propagated.

2. **Reads must be >= 2 seconds apart.** The sensor needs that long to
   re-sample its element; polling faster returns stale or garbage data. That
   floor is enforced by `BaseSensor.min_interval_s` and is also applied
   between retries.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from core.contracts import Reading
from core.registry import register_sensor
from sensors.base import BaseSensor, SensorError, SensorReadError

log = logging.getLogger(__name__)

#: Datasheet minimum sampling period, in seconds. Do not lower this.
DHT22_MIN_INTERVAL_S = 2.0


@register_sensor("dht22")
class DHT22Sensor(BaseSensor):
    """Reads temperature and humidity from a DHT22 on a single GPIO pin.

    The CircuitPython libraries are imported lazily inside `open()` rather
    than at module import time. That is deliberate: it means this file can be
    imported, registered, and unit-tested on a laptop with no GPIO hardware
    and no Blinka installed. You only pay the import cost on the Pi.

    Args:
        pin: `board` attribute name for the data line. Default "D4" = GPIO4.
        retries: attempts per `read()` before giving up on the cycle.
        retry_delay_s: pause between attempts. Kept at the 2s sensor floor by
            default, because retrying faster than that cannot succeed.
        use_pulseio: `adafruit_dht` can use the pulseio peripheral or a pure
            bit-bang loop. On Raspberry Pi OS the bit-bang path (False) is the
            reliable one, so that is the default.
    """

    name = "dht22"

    def __init__(
        self,
        pin: str = "D4",
        retries: int = 5,
        retry_delay_s: float = DHT22_MIN_INTERVAL_S,
        use_pulseio: bool = False,
        min_interval_s: float = DHT22_MIN_INTERVAL_S,
    ) -> None:
        # Guard against a config that would violate the datasheet.
        effective_interval = max(float(min_interval_s), DHT22_MIN_INTERVAL_S)
        if float(min_interval_s) < DHT22_MIN_INTERVAL_S:
            log.warning(
                "config requested min_interval_s=%.2f for the DHT22; clamping to the "
                "datasheet minimum of %.1fs",
                float(min_interval_s),
                DHT22_MIN_INTERVAL_S,
            )
        super().__init__(min_interval_s=effective_interval)

        self.pin_name = str(pin)
        self.retries = max(1, int(retries))
        self.retry_delay_s = float(retry_delay_s)
        self.use_pulseio = bool(use_pulseio)

        self._device: Any = None

    # -- lifecycle ---------------------------------------------------------

    def open(self) -> None:
        """Import the drivers and claim the GPIO pin."""
        if self._device is not None:
            return

        try:
            import adafruit_dht  # type: ignore[import-not-found]
            import board  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001 - any import problem is fatal here
            raise SensorError(
                "DHT22 drivers unavailable. On the Raspberry Pi run:\n"
                "    pip install adafruit-circuitpython-dht adafruit-blinka\n"
                "On a machine without GPIO, set `sensor.active: synthetic` in "
                f"config.yaml instead. (underlying error: {exc})"
            ) from exc

        if not hasattr(board, self.pin_name):
            raise SensorError(
                f"`board` has no pin named {self.pin_name!r}. "
                "For GPIO4 (physical pin 7) use 'D4'."
            )

        pin = getattr(board, self.pin_name)
        self._device = adafruit_dht.DHT22(pin, use_pulseio=self.use_pulseio)
        super().open()
        log.info(
            "DHT22 initialised on board.%s (pulseio=%s, %d retries, %.1fs floor)",
            self.pin_name,
            self.use_pulseio,
            self.retries,
            self.min_interval_s,
        )

    def close(self) -> None:
        """Release the GPIO pin. Must never raise -- this runs in cleanup paths."""
        device, self._device = self._device, None
        if device is not None:
            try:
                device.exit()
            except Exception as exc:  # noqa: BLE001 - best-effort teardown
                log.debug("Ignoring error while releasing DHT22: %s", exc)
        super().close()

    # -- reading -----------------------------------------------------------

    def _read_once(self) -> Reading:
        """Read with retries, tolerating the DHT22's routine transient failures."""
        last_error: Exception | None = None

        for attempt in range(1, self.retries + 1):
            if attempt > 1:
                # A retry cannot succeed until the sensor has re-sampled, so
                # always wait out the datasheet interval first.
                time.sleep(self.retry_delay_s)

            try:
                temperature = self._device.temperature
                humidity = self._device.humidity
            except RuntimeError as exc:
                # THE expected failure mode: checksum/timing glitch. Common
                # enough that logging it at INFO would flood the console.
                last_error = exc
                log.debug("DHT22 transient read failure %d/%d: %s", attempt, self.retries, exc)
                continue
            except Exception as exc:  # noqa: BLE001
                # Anything else (pin conflict, driver crash) is not transient.
                raise SensorReadError(f"DHT22 read failed unrecoverably: {exc}") from exc

            # The library can hand back None instead of raising when a read
            # produced no usable data. Treat that identically to a RuntimeError.
            if temperature is None or humidity is None:
                last_error = SensorReadError("DHT22 returned an incomplete sample")
                log.debug("DHT22 incomplete sample %d/%d", attempt, self.retries)
                continue

            if attempt > 1:
                log.info("DHT22 read succeeded after %d attempts", attempt)

            return Reading.now(
                temperature_c=round(float(temperature), 2),
                humidity_pct=round(float(humidity), 2),
                source=self.name,
                metadata={"pin": self.pin_name, "attempts": attempt},
            )

        raise SensorReadError(
            f"DHT22 failed {self.retries} consecutive reads on board.{self.pin_name} "
            f"(last error: {last_error}). Check wiring: VCC->3V3, DATA->GPIO4, GND->GND."
        )
