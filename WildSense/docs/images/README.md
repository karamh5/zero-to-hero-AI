# Screenshots

Drop the captures referenced by the root `README.md` here:

| File | How to capture it |
|---|---|
| `dashboard.png` | `python run.py --demo --interval 2`, wait until the event log has a few rows, screenshot <http://127.0.0.1:8000> |
| `dht22-detection.png` | On the Pi: `python run.py --sensor dht22`, let the baseline warm up, then breathe on the sensor or hold it near something warm |
| `federation-rounds.png` | Let `run.py` sit for ~4 minutes (`round_interval_s: 20`), then screenshot the federated learning panel |
| `node-hardware.png` | Photo of the Pi and DHT22 as actually wired |

The dashboard follows the OS light/dark setting and has a toggle in the header —
capture whichever suits the page it will appear on.
