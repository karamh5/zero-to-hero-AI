"""DHT22 via the Linux kernel driver -- the pack that works on a Raspberry Pi 5.

`sensors/dht22.py` bit-bangs the one-wire protocol from userspace through
`adafruit_dht` + Blinka. That works on the Pi 3, Pi 4 and Pi Zero 2 W, and it
does NOT work on the Pi 5: the RP1 south bridge replaced the GPIO block those
libraries drive, so Blinka does not recognise the BCM2712 and the pulse-timing
path fails with "Timed out waiting for PulseIn message" no matter how the
wiring is done.

The fix is to stop bit-banging in Python and let the kernel do it. Linux ships
an IIO driver for this sensor family; Raspberry Pi OS exposes it through the
`dht11` device-tree overlay, which despite its name covers DHT11/DHT21/DHT22
and the AM230x parts.

Enable it once, in `/boot/firmware/config.txt`:

    dtoverlay=dht11,gpiopin=4

...then reboot. GPIO4 is the overlay's own default and is the pin
HARDWARE_SETUP.md already has you wire, so **nothing on the breadboard
changes** -- this is a software swap, not a rewiring.

After the reboot the sensor appears as an IIO device:

    /sys/bus/iio/devices/iio:device0/
        name                        -> "dht11"
        in_temp_input               -> millidegrees Celsius   (23400 = 23.4 C)
        in_humidityrelative_input   -> milli-percent RH       (41200 = 41.2 %)

Reading those two files is the whole driver. Two properties of that interface
shape this file:

1. **Reads still fail routinely, just in a different dialect.** The kernel is
   doing the same microsecond-timing job the Python library was, so it hits
   the same checksum and framing failures -- it reports them as `OSError`
   with `errno = EIO` when you `read()` the file, rather than as a
   `RuntimeError`. Same problem, same answer: retry, never propagate.

2. **The 2-second floor is unchanged.** It is a property of the sensor
   element, not of the software talking to it. The driver enforces its own
   sampling interval internally and will hand back a cached value or EIO if
   polled faster, so `BaseSensor.min_interval_s` still has to hold the line.

There is no import of `board` or `adafruit_dht` anywhere in this file. It
needs nothing but `open()`, which means -- unlike the Blinka pack -- it can be
exercised end to end on a laptop against a directory of fake sysfs files.
That is exactly what `tests/test_sensors.py` does.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from core.contracts import Reading
from core.registry import register_sensor
from sensors.base import BaseSensor, SensorError, SensorReadError

log = logging.getLogger(__name__)

#: Datasheet minimum sampling period, in seconds. A property of the part.
DHT22_MIN_INTERVAL_S = 2.0

#: Where the kernel publishes IIO devices.
IIO_ROOT = "/sys/bus/iio/devices"

#: The two files the `dht11` overlay's driver exposes, and their scale factor.
#: IIO reports processed `_input` values in milli-units, so both are /1000.
TEMP_FILE = "in_temp_input"
HUMIDITY_FILE = "in_humidityrelative_input"
MILLI = 1000.0


@register_sensor("dht22_kernel")
class DHT22KernelSensor(BaseSensor):
    """Reads a DHT22 through the kernel's IIO sysfs interface.

    Args:
        device_path: Full path to the `iio:deviceN` directory. Leave as None
            to auto-discover it, which is the sane default -- the number the
            kernel assigns is not stable across boots if other IIO devices
            are present.
        iio_root: Where to search during auto-discovery. Overridable so the
            tests can point it at a temporary directory.
        retries: attempts per `read()` before giving up on the cycle.
        retry_delay_s: pause between attempts. Held at the sensor floor,
            because a retry sooner than that cannot succeed.
    """

    name = "dht22_kernel"

    def __init__(
        self,
        device_path: str | None = None,
        iio_root: str = IIO_ROOT,
        retries: int = 5,
        retry_delay_s: float = DHT22_MIN_INTERVAL_S,
        min_interval_s: float = DHT22_MIN_INTERVAL_S,
    ) -> None:
        # Same guard as the Blinka pack: config must not be able to violate
        # the datasheet.
        effective_interval = max(float(min_interval_s), DHT22_MIN_INTERVAL_S)
        if float(min_interval_s) < DHT22_MIN_INTERVAL_S:
            log.warning(
                "config requested min_interval_s=%.2f for the DHT22; clamping to the "
                "datasheet minimum of %.1fs",
                float(min_interval_s),
                DHT22_MIN_INTERVAL_S,
            )
        super().__init__(min_interval_s=effective_interval)

        self._configured_path = device_path
        self._iio_root = Path(iio_root)
        self.retries = max(1, int(retries))
        self.retry_delay_s = float(retry_delay_s)

        self._temp_path: Path | None = None
        self._humidity_path: Path | None = None

    # -- discovery ---------------------------------------------------------

    def _discover_device(self) -> Path:
        """Find the IIO directory belonging to the DHT sensor.

        Identification is by capability, not by name: the directory we want is
        the one that publishes a relative-humidity channel. That is more robust
        than matching `name` against "dht11", because the string the driver
        reports has varied across kernel versions while the channel layout has
        not.
        """
        if not self._iio_root.is_dir():
            raise SensorError(
                f"{self._iio_root} does not exist, so no IIO devices are registered. "
                "The kernel driver is probably not enabled. Add this line to "
                "/boot/firmware/config.txt and reboot:\n"
                "    dtoverlay=dht11,gpiopin=4"
            )

        candidates = sorted(
            path
            for path in self._iio_root.iterdir()
            if (path / HUMIDITY_FILE).exists() and (path / TEMP_FILE).exists()
        )

        if not candidates:
            present = ", ".join(sorted(p.name for p in self._iio_root.iterdir())) or "<none>"
            raise SensorError(
                f"No IIO device under {self._iio_root} exposes both {TEMP_FILE} and "
                f"{HUMIDITY_FILE} (found: {present}). Check that "
                "`dtoverlay=dht11,gpiopin=4` is in /boot/firmware/config.txt, that you "
                "have rebooted since adding it, and that DATA is wired to GPIO4 "
                "(physical pin 7)."
            )

        if len(candidates) > 1:
            log.warning(
                "Several IIO devices expose humidity (%s); using %s. Set "
                "`device_path` in config.yaml to pick a specific one.",
                ", ".join(p.name for p in candidates),
                candidates[0].name,
            )

        return candidates[0]

    # -- lifecycle ---------------------------------------------------------

    def open(self) -> None:
        """Locate the sysfs files. There is no device handle to acquire."""
        if self._temp_path is not None:
            return

        if self._configured_path is not None:
            device = Path(self._configured_path)
            if not (device / TEMP_FILE).exists():
                raise SensorError(
                    f"{device} does not look like a DHT IIO device: no {TEMP_FILE}. "
                    "Leave `device_path` unset in config.yaml to auto-discover it."
                )
        else:
            device = self._discover_device()

        self._temp_path = device / TEMP_FILE
        self._humidity_path = device / HUMIDITY_FILE
        super().open()
        log.info(
            "DHT22 (kernel driver) initialised on %s (%d retries, %.1fs floor)",
            device,
            self.retries,
            self.min_interval_s,
        )

    def close(self) -> None:
        """Nothing is held open, so this only clears the resolved paths."""
        self._temp_path = None
        self._humidity_path = None
        super().close()

    # -- reading -----------------------------------------------------------

    def _read_channel(self, path: Path) -> float:
        """Read one milli-unit sysfs file and scale it.

        Every `read()` of these files triggers a fresh acquisition in the
        driver, so this is where the transient failures surface.
        """
        return int(path.read_text().strip()) / MILLI

    def _read_once(self) -> Reading:
        """Read with retries, tolerating the sensor's routine transient failures."""
        assert self._temp_path is not None and self._humidity_path is not None

        last_error: Exception | None = None

        for attempt in range(1, self.retries + 1):
            if attempt > 1:
                # The element has to re-sample before a retry can possibly
                # differ from the one that just failed.
                time.sleep(self.retry_delay_s)

            try:
                temperature = self._read_channel(self._temp_path)
                humidity = self._read_channel(self._humidity_path)
            except OSError as exc:
                # THE expected failure mode. The driver returns EIO when the
                # checksum or the pulse framing did not come out. Common
                # enough that INFO-level logging would flood the console.
                last_error = exc
                log.debug(
                    "DHT22 kernel transient read failure %d/%d: %s", attempt, self.retries, exc
                )
                continue
            except ValueError as exc:
                # A partially-written or empty sysfs read. Same class of
                # problem as EIO from this caller's point of view.
                last_error = exc
                log.debug("DHT22 kernel unparsable sample %d/%d: %s", attempt, self.retries, exc)
                continue

            if attempt > 1:
                log.info("DHT22 kernel read succeeded after %d attempts", attempt)

            return Reading.now(
                temperature_c=round(temperature, 2),
                humidity_pct=round(humidity, 2),
                source=self.name,
                metadata={"device": str(self._temp_path.parent), "attempts": attempt},
            )

        raise SensorReadError(
            f"DHT22 kernel driver failed {self.retries} consecutive reads at "
            f"{self._temp_path.parent} (last error: {last_error}). Check wiring: "
            "VCC->3V3, DATA->GPIO4, GND->GND."
        )
