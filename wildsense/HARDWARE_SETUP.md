# Hardware setup: ShillehTek DHT22 on a Raspberry Pi

Wiring the temperature/humidity sensor to your Pi and proving it works, from
scratch. **About 15 minutes**, most of which is waiting for downloads.

No soldering. No breadboard. No extra components. Three wires.

This guide assumes you have never wired anything to a Raspberry Pi before, so
every term is explained the first time it appears.

---

## 1. Parts list

| # | Item | Notes |
|---|---|---|
| 1 | **Raspberry Pi** with Raspberry Pi OS already flashed to its microSD card | Any model with the standard 40-pin header. You should be able to boot it and get to a terminal. |
| 2 | **ShillehTek DHT22 module** with its attached 3-wire cable | The sensor is the white/blue plastic grid mounted on a small circuit board. |
| 3 | **3 × female-to-female jumper wires** | **Only if** your cable does not already end in connectors that push onto the Pi's pins. See below. |

**Do you need the jumper wires?** Look at the loose end of the sensor's cable:

- **Ends are small black plastic sockets with a hole** → these are *female
  connectors*. They push directly onto the Pi's pins. **You do not need
  anything else.**
- **Ends are bare wire, or stiff exposed metal pins** → you need 3
  female-to-female jumper wires to bridge across.

"Female-to-female" just means both ends are sockets, so they can join two sets
of pins together.

### What you do NOT need

This module has a **pull-up resistor built in**. A pull-up resistor is a small
component that holds the data wire at a steady voltage when the sensor isn't
actively talking. A bare 4-pin DHT22 needs you to add one yourself; **this
module already has it on the board**, so do not add a resistor between DATA
and VCC. Three wires is the whole job.

---

## 2. Wire it up

> ⚠️ **Shut the Pi down and unplug its power before touching any wires.**
> `sudo shutdown -h now`, wait for the green light to stop blinking, then pull
> the power cable. Moving wires on a powered Pi can destroy it.

### 2.1 Find pin 1

The **40-pin header** is the double row of 40 metal pins sticking up along one
long edge of the Pi.

**Pin 1 is at the corner of that header nearest the SD card slot.**

The pins are numbered in a zig-zag, not in rows:

```
   SD-card end of the board
        |
        v
        1   3   5   7   9         <- odd row, nearest the outside edge of the board
        o   o   o   o   o   . . .
        o   o   o   o   o   . . .
        2   4   6   8  10         <- even row, nearest the middle of the board
```

So **pin 1 and pin 2 sit side by side** at the SD-card end. Odd numbers run
along the outer row; even numbers run along the inner row.

The three pins you need are all within the first four positions:

| Physical pin | What it is |
|---|---|
| **1** | 3.3 volts (power) — outer row, very first pin |
| **6** | Ground — inner row, third pin along |
| **7** | GPIO4 (data) — outer row, fourth pin along |

> ⚠️ **Pin 1 is 3.3V. Pin 2, right next to it, is 5V.** Putting the sensor's
> power on pin 2 pushes 5V into the Pi's data pin, which can permanently damage
> the Pi. Count carefully: the power wire goes on the **outer** row, in the
> **corner**.

### 2.2 Identify the three wires

Look at the **printed labels on the sensor's circuit board**, next to where the
cable attaches. They will say something like `+` / `OUT` / `-`, or
`VCC` / `DATA` / `GND`.

**Go by the printed labels, not the wire colours** — colours vary between
batches, and guessing is the single most common way this goes wrong.

### 2.3 Make the three connections

Push each wire onto the pin. It should slide on snugly and stay put.

| Sensor pin (its label) | → | Raspberry Pi physical pin |
|---|---|---|
| **VCC** (or `+`) | → | **pin 1** — 3.3V |
| **GND** (or `−`) | → | **pin 6** — Ground |
| **DATA** (or `OUT`) | → | **pin 7** — GPIO4 |

```
   ShillehTek DHT22                 Raspberry Pi 40-pin header
   ----------------                 --------------------------
        VCC / +   ------------->    pin 1   (3.3V)
        GND / -   ------------->    pin 6   (GND)
       DATA / OUT ------------->    pin 7   (GPIO4)
```

**Double-check before powering up.** Count the pins with a fingernail rather
than eyeballing it — they are close together and it is easy to be off by one.

Now plug the Pi back in and let it boot.

### A note on names

You will see the data pin called three different things. They are all the same
physical pin:

- **physical pin 7** — its position on the header (what you count to)
- **GPIO4** / **BCM4** — the chip's name for it (what the software uses)
- **`board.D4`** — what Python calls it

---

## 3. No I2C setup needed

If you have followed other sensor guides, you may have seen a step about
enabling **I2C** in `raspi-config`. **Skip it — it does not apply here.**

I2C is a protocol where several devices share two wires and each has an
address. The DHT22 does not use it. The DHT22 sends its readings as timed
pulses down a **single** data wire, so there is nothing to enable, no address
to set, and nothing will show up in `i2cdetect`. That is expected, not a fault.

Go straight to the software.

---

## 4. Install the software

Open a terminal on the Pi and run these four commands, one at a time. Wait for
each to finish before starting the next.

```bash
sudo apt update
```

```bash
sudo apt install -y python3-pip libgpiod2
```

```bash
pip3 install adafruit-circuitpython-dht adafruit-blinka
```

```bash
sudo usermod -aG gpio $USER
```

What each one does:

1. `apt update` — refreshes the list of available software packages.
2. `apt install` — installs `pip` (Python's package installer) and `libgpiod2`
   (a system library for talking to GPIO pins).
3. `pip3 install` — installs the two Python libraries that read the sensor.
4. `usermod -aG gpio` — adds your user account to the `gpio` group, which is
   what grants permission to use the pins.

> ### ⚠️ You must reboot before the last command takes effect
>
> Group membership is only applied when you log in. Until you log out and back
> in — or reboot — your session still has the old permissions and the test
> below will fail with a permission error even though everything is correct.
>
> ```bash
> sudo reboot
> ```
>
> Rebooting is the reliable option. Do it now.

> **If `pip3 install` fails with "externally-managed-environment":** newer
> Raspberry Pi OS versions block installing into system Python. Either add the
> override:
>
> ```bash
> pip3 install --break-system-packages adafruit-circuitpython-dht adafruit-blinka
> ```
>
> or make a virtual environment (a private Python folder) instead:
>
> ```bash
> python3 -m venv ~/dht-test
> source ~/dht-test/bin/activate
> pip install adafruit-circuitpython-dht adafruit-blinka
> ```
>
> If you use the virtual environment, run `source ~/dht-test/bin/activate` in
> each new terminal before running the test script.

---

## 5. Run a real test

Create the test script. Copy and paste this whole block into the terminal and
press Enter — it writes the file for you, so there is nothing to type by hand:

```bash
cat > ~/dht22_test.py << 'EOF'
"""Minimal DHT22 read test. Ctrl+C to stop."""
import time

import adafruit_dht
import board

# board.D4 is GPIO4, which is physical pin 7 on the header.
# use_pulseio=False selects the software timing method, which is the
# reliable one on Raspberry Pi OS.
sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)

print("Reading the DHT22 every 2 seconds. Press Ctrl+C to stop.\n")

successes = 0
failures = 0

try:
    while True:
        try:
            temperature = sensor.temperature
            humidity = sensor.humidity

            if temperature is None or humidity is None:
                failures += 1
                print(f"  .. incomplete reading, retrying   (ok: {successes}, failed: {failures})")
            else:
                successes += 1
                print(f"Temperature: {temperature:5.1f} C    "
                      f"Humidity: {humidity:5.1f} %    "
                      f"(ok: {successes}, failed: {failures})")

        except RuntimeError as error:
            # Expected occasionally. See the notes below -- this is normal.
            failures += 1
            print(f"  .. read failed: {error}   (ok: {successes}, failed: {failures})")

        # The DHT22 physically cannot be read faster than once every 2 seconds.
        time.sleep(2.0)

except KeyboardInterrupt:
    print(f"\nStopped. {successes} good reads, {failures} failed reads.")
finally:
    sensor.exit()
EOF
```

Then run it:

```bash
python3 ~/dht22_test.py
```

### Two things this script does deliberately

**It waits 2 seconds between reads.** The DHT22 needs that long to take a fresh
measurement. Asking faster returns stale or garbage data.

**It catches `RuntimeError` and keeps going.** The DHT22 sends its data as
pulses measured in millionths of a second, and Raspberry Pi OS is not a
real-time system — it occasionally pauses your program mid-read to do something
else, which corrupts the timing and the library raises a `RuntimeError` with a
message like `Checksum did not validate. Try again.`

**Occasional failures are completely normal and are not a wiring problem.**
Losing some reads is expected behaviour for this sensor. It is only a problem
if **every** read fails.

---

## 6. What working looks like

A new line roughly every 2 seconds, with plausible numbers, mixed with the
occasional failure:

```
Temperature:  21.4 C    Humidity:  47.8 %    (ok: 1, failed: 0)
Temperature:  21.4 C    Humidity:  47.9 %    (ok: 2, failed: 0)
  .. read failed: Checksum did not validate. Try again.   (ok: 2, failed: 1)
Temperature:  21.5 C    Humidity:  47.7 %    (ok: 3, failed: 1)
Temperature:  21.5 C    Humidity:  48.1 %    (ok: 4, failed: 1)
```

**That is a pass.** A few failures mixed in is healthy.

**Confirm the sensor is really live:** breathe gently on it for a few seconds.
Humidity should jump noticeably (often 10–30 points) within a couple of
readings, then drift back down. If the numbers respond to your breath, the
sensor is genuinely reading the air and you are done.

### What a real problem looks like

| What you see | What it means |
|---|---|
| **Every single read fails**, `ok: 0` after 10+ attempts | Wiring problem. Go to troubleshooting. |
| The script **hangs** with no output at all | Wiring problem, usually DATA on the wrong pin or not connected. |
| `RuntimeError: Timed out waiting for PulseIn message` on every read | The Pi is not receiving anything on the data pin. |
| A **permission error** mentioning GPIO or `/dev/gpiochip` | You skipped the reboot after the `usermod` command (section 4). |
| `ModuleNotFoundError: No module named 'board'` | The `pip3 install` step did not complete. Re-run it. |
| Temperature is plausible but humidity is stuck at exactly 0 or 100 | Usually a loose DATA wire. Reseat it. |

---

## 7. Troubleshooting

Work through these in order. Between each one, re-run
`python3 ~/dht22_test.py` and give it at least 10 attempts (about 20 seconds)
before deciding it failed — remember, single failures mean nothing.

> Power the Pi down before moving any wire.

### 7.1 Wires swapped

By far the most common cause. The three wires are interchangeable physically
but not electrically.

- Re-read the **printed labels on the sensor board**, not the wire colours.
- `VCC`/`+` → **pin 1**, `GND`/`−` → **pin 6**, `DATA`/`OUT` → **pin 7**.
- **VCC and GND swapped** → the sensor gets power backwards. Nothing works, and
  the sensor may feel warm. Unplug immediately and re-check.
- **DATA and VCC swapped** → every read fails or the script hangs.
- **Off by one pin** → count again with a fingernail. Pin 1 is the outer-row
  corner nearest the SD card slot. Landing on pin 2 (5V) instead of pin 1
  (3.3V) can damage the Pi.

### 7.2 Reading too fast

If you wrote your own test, check there is a `time.sleep(2.0)` in the loop.
Reading a DHT22 more often than once every 2 seconds returns failures or stale
values no matter how good the wiring is. The script above already does this
correctly.

### 7.3 Forgot the gpio group or the reboot

Permission errors mean this step. Confirm you are in the group:

```bash
groups
```

If `gpio` is not in the list that prints, run the command again and reboot:

```bash
sudo usermod -aG gpio $USER
sudo reboot
```

Running `sudo usermod` without rebooting changes nothing about your *current*
session — this catches almost everyone once.

As a quick check of whether permissions are the issue, try:

```bash
sudo python3 ~/dht22_test.py
```

If it works with `sudo` but not without, it is definitely the group/reboot
step.

### 7.4 Loose connection at the header

Jumper connectors work loose easily, and a wire can *look* seated while barely
touching.

- Power down, pull each of the three connectors off, and push each firmly back
  on. You should feel it seat.
- Gently tug each wire — it should not slide off.
- Wiggle each connector while the test runs (this is safe; you are not moving
  it between pins). If readings stutter as you wiggle, that connector is loose.
- If you are using jumper wires as extensions, check the join in the middle
  too — that is a second place to come loose.
- Try a different jumper wire. They fail more often than you would expect.

### 7.5 Still nothing?

- Try the DATA wire on a different GPIO pin — for example physical **pin 11**
  (GPIO17) — and change `board.D4` to `board.D17` in the test script. If it
  works there, pin 7 on your Pi may be damaged.
- Try the sensor on a different Pi if you have one, to work out whether the
  fault is the sensor or the board.

---

## 8. Now run WildSense

Once the test script prints real numbers, the hardware is proven. Point the
project at it:

```bash
cd wildsense
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install adafruit-circuitpython-dht adafruit-blinka

python -m detectors.train
python run.py --sensor dht22
```

Open the dashboard at <http://127.0.0.1:8000>.

To view it from your laptop instead of on the Pi itself, set
`dashboard.host: 0.0.0.0` in `config.yaml`, then browse to
`http://<your-pi-address>:8000`. Find the Pi's address with `hostname -I`.

The detector needs about 40 readings to learn what "normal" looks like at your
location before it will report anything — at a 2-second poll that is roughly 80
seconds. Once it settles, breathe on the sensor and watch the event log.

See [README.md](README.md) for what the project does and how the detection
works.
