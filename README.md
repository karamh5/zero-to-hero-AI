WildSense
A modular edge-AI platform for detecting environmental events on a Raspberry Pi.

WildSense reads environmental sensors on a low-power edge node, decides on the device whether what it just measured is unusual, classifies what kind of event it is, and learns from a fleet of peer nodes without any of them ever shipping raw readings anywhere.

The hardware today is one Raspberry Pi with a DHT22 temperature/humidity sensor. The architecture assumes that is the first of several sensors, not the only one — adding a thermal camera or an air-quality pack is a config change, not a rewrite. A full synthetic mode means the entire pipeline runs, and the entire test suite passes, with zero hardware attached.

What makes it different from a threshold alarm
There is no hardcoded temperature anywhere in the detection path.

A fixed rule like if temp > 35: alert is wrong in both directions: it screams all summer in a desert and stays silent through a genuine 12 °C excursion in an alpine valley. WildSense instead keeps a rolling statistical baseline — an exponentially weighted mean and variance — for each channel, and flags a reading when it deviates significantly from its own recent history.

So "hot" means something different depending on where the node is and what the last few minutes looked like. The same code, with no per-site tuning, adapts to its own environment. Push a node's normal operating point from 20 °C to 28 °C and it fires once at the transition, then goes quiet — because 28 °C is now simply what this place is like.

A small PyTorch classifier then names what kind of event it is. The two stages have deliberately different jobs, and the statistical stage always gates the model — so a missing or broken model file degrades the event label, never the detection itself.

Architecture

Same diagram as ASCII
Modules
Module	Responsibility
core/	Data contracts (Reading, Event), config loading, the pack registry. Imports nothing from the other modules — the dependency arrow points inward only.
sensors/	BaseSensor + DHT22Sensor (GPIO4, retry-hardened) + SyntheticEnvSensor (believable series with injected anomalies).
detectors/	BaseDetector + EnvAnomalyDetector: EWMA z-score gate, then a ~6.5K-parameter MLP over a 32-reading window for event type.
federation/	LocalTrainer (fits on a node's own readings) + FederatedAverager (sample-weighted FedAvg) + a 3-node concurrent simulation.
cloud/	S3 event snapshots over a bounded queue. Degrades to local files with one clear log line if credentials are absent.
context/	Risk level → polling interval, clamped to the sensor's hardware floor.
dashboard/	FastAPI app serving one live page: temperature and humidity charts, a risk gauge, a scrolling event log.
Why it is genuinely modular
config.yaml names packs; the pipeline builds them from a registry. pipeline.py never imports a concrete sensor or detector. Adding a thermal-camera pack is:

write sensors/thermal.py with @register_sensor("thermal")
add sensors.thermal to packs.discover in config.yaml
set sensor.active: thermal
No core file changes. There is a test that does exactly this (test_a_future_sensor_pack_is_a_config_change_only) so the claim stays true.

Quick start — synthetic mode (no hardware)
Everything below runs from inside the wildsense/ directory.

cd wildsense

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. Train the event classifier on synthetic sequences (~30 seconds, CPU).
python -m detectors.train

# 2. Run the whole pipeline: sensor -> detector -> federation -> dashboard.
python run.py
Then open http://127.0.0.1:8000.

For a short recording that is guaranteed to contain every event type:

python run.py --demo --interval 2
--demo injects a spike, a drop and a drift on a timer, because real weather does not cooperate with a two-minute screen capture.

Useful flags
Flag	Effect
--sensor dht22	use the real hardware pack instead of the synthetic one
--interval 2	pin every risk level to a 2 s poll (still clamped by the sensor floor)
--duration 120	stop after two minutes
--cycles 500	stop after 500 read cycles
--no-dashboard	run headless
--no-federation	skip the simulated peer fleet
--no-cloud	skip event snapshotting
--demo	inject one of each event type on a timer
--log-level DEBUG	verbose logging
Tests
cd wildsense
pytest -q
All tests pass with no hardware attached. The DHT22 driver tests inject fake board / adafruit_dht modules, so the retry logic is exercised on a laptop — which is the only practical way to test it, since you cannot ask a real sensor to fail on demand.

Running with the real DHT22
Never wired a sensor to a Pi before? Follow HARDWARE_SETUP.md instead — it covers the same ground step by step, with physical pin numbers, a copy-paste test script, and troubleshooting. About 15 minutes. The summary below assumes you have done this sort of thing before.

Wiring
A 3-wire DHT22 module (with the pull-up resistor already on board):

   DHT22 module            Raspberry Pi
   ------------            ---------------------
   VCC  / +      -------->  3V3    (pin 1)
   DATA / OUT    -------->  GPIO4  (pin 7)   = board.D4
   GND  / -      -------->  GND    (pin 6)
This is a one-wire protocol, not I2C. There is nothing to find with i2cdetect and no address to set. A bare 4-pin DHT22 would need a 10 kΩ pull-up between VCC and DATA; the 3-wire module already has one.

Install and run on the Pi
cd wildsense
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Hardware drivers — Raspberry Pi only, these will not build on Windows/macOS.
pip install adafruit-circuitpython-dht adafruit-blinka

python -m detectors.train        # or copy artifacts/ over from your dev machine
python run.py --sensor dht22
To view the dashboard from another machine on the network, set dashboard.host: 0.0.0.0 in config.yaml, then browse to http://<pi-address>:8000.

Two DHT22 quirks the code handles for you
Reads fail routinely. The DHT22 is bit-banged with microsecond timing from a non-realtime OS, so scheduling jitter corrupts the pulse train often enough that adafruit_dht raises RuntimeError on a large fraction of reads (Checksum did not validate, A full buffer was not returned). This is normal, not a fault. DHT22Sensor retries with a configurable budget and only gives up on the cycle — never on the run.
Reads must be ≥ 2 seconds apart. The part needs that long to re-sample. BaseSensor.min_interval_s enforces the gap, retry_delay_s applies it between retries too, and PollingPolicy clamps every risk level against it — so no config value and no risk provider can out-run the hardware.
How the pieces work
Detection: adaptive statistics, then a model
Stage 1 — should we care at all? An EWMA mean and variance per channel (O(1) memory, two floats, which matters on a Pi), at two timescales. Each reading is scored against the baseline before it is absorbed, so an anomaly cannot dilute the baseline it is being judged by. A variance floor (temp_min_std, just above the DHT22's 0.1 °C resolution) stops a very flat stretch from manufacturing huge z-scores.

Two details here are not decoration — both were added after measuring the detector fail without them:

The baseline update is winsorised. An observation can move the baseline by at most clip_z standard deviations, while the reported z-score is left untouched. Without this, one 10 °C spike puts a diff² term of 100 into the variance recursion, inflating the standard deviation by an order of magnitude for a hundred-plus samples — during which the detector is blind to everything that follows. Measured: temperature std went to 4.19 on a stream whose true noise is 0.2, and three consecutive injected anomalies went undetected.
There is a slow baseline as well as a fast one. A single fast EWMA is structurally incapable of seeing a gradual drift, because it is built to follow its input — it absorbs the ramp and every individual z-score stays near zero. Measured: a 31-sample humidity ramp produced z-scores under 1.0 for its entire duration. The slow baseline (~500-sample memory vs ~39) is what makes the drift class detectable at all.
Detections are debounced. An ongoing condition is one event, not one per reading — the slow baseline stays displaced for hundreds of samples after a real drift, so without a refractory period a single episode emitted a detection, and an S3 snapshot, on every cycle (36 events for 4 real episodes in one 230-second run). A long-running condition still re-reports on a timer rather than going silent.
Stage 2 — what kind of event, and how sure? A 4-class MLP over the last 32 readings. Features are standardised within the window, so the model sees the shape of recent history rather than absolute values. That is what makes it climate-agnostic — a model trained on desert nodes transfers to alpine ones — and it is also what makes federated averaging across dissimilar nodes coherent. Two extra magnitude features keep it from being blind to amplitude.

Exported to TorchScript so edge inference needs no dependency beyond torch.

Federation: real FedAvg, simulated deployment
Only one physical node exists, so the peers are simulated. What is simulated is the deployment, not the learning. Each node has its own sensor, its own climate, its own accumulated readings, its own model copy, and trains concurrently in its own worker thread. Each round:

every node adopts the current global weights
every node pulls fresh readings from its own sensor (concurrent)
every node runs a few local epochs on its own buffer (concurrent)
every node submits (weights, sample count) to the averager
the coordinator merges by sample-weighted FedAvg and scores the result on a held-out set spanning all climates
Step 5 is the number worth watching: the shared model getting better at climates no single node ever saw is the only reason to federate at all. Readings never leave a node — only weights move.

The averaged weights are hot-swapped into the live detector, so the fleet's learning actually improves the node that is detecting, rather than training in a vacuum beside it.

Contextual adaptation
A risk provider (mocked external feed — a real deployment would call a fire-danger API or a satellite hotspot service) produces a risk level; the polling policy turns it into an interval. High risk polls at the DHT22's 2 s floor, low risk backs off to 60 s. On a solar-powered node that difference is the difference between surviving the night and not.

The event-feedback half of the provider is genuinely closed-loop: detections raise the risk, the raised risk shortens the interval, the shorter interval produces more readings. Only the ambient forecast is fake.

Cloud sync
Optional and non-fatal by design. A field node that dies because an S3 bucket was misconfigured is worse than one that quietly keeps detecting. Uploads go through a bounded queue drained by a daemon thread, so a stalled network never blocks the sensor loop. With no bucket or no credentials, WildSense logs one clear line and writes snapshots to events/ locally instead.

Credentials are never read from config.yaml — boto3 resolves them from the environment, so nothing secret can be committed by accident.

Configuration
config.yaml is the single control surface. The keys that matter most:

sensor:
  active: synthetic         # or dht22

detector:
  packs:
    env_anomaly:
      alpha: 0.05              # fast EWMA forgetting factor (~39-sample memory)
      z_threshold: 3.5         # deviations from the FAST baseline -> spike/drop
      drift_z_threshold: 3.5   # deviations from the SLOW baseline -> drift
      slow_alpha_ratio: 0.08   # slow baseline = alpha * this (~500 samples)
      clip_z: 4.0              # cap on how far one reading may move a baseline
      warmup_samples: 40       # no detections before this many readings

context:
  intervals:                # seconds per risk level; clamped by the sensor floor
    low: 60.0
    extreme: 2.0

federation:
  enabled: true
  round_interval_s: 20.0
Results
Screenshots
Placeholders — replace with captures from your own run. See docs/images/README.md for how to take each one.

WildSense dashboard

DHT22 detection

Federation rounds

Node hardware

Measured
All figures below are from actual runs on synthetic data (Python 3.13, torch 2.13, CPU). Nothing here is estimated.

Event classifier

Metric	Value
Parameters	6,500
Validation accuracy	0.999 (1,280 held-out windows across 4 climates)
Per class	none 0.997 · spike 1.000 · drop 1.000 · drift 1.000
Training time	~10 s, CPU
That accuracy is high because the task is easy: the classifier only has to name an event the statistical stage has already flagged, on synthetic data with clean shapes. Treat it as "the classifier is not the bottleneck", not as evidence the system is 99.9% accurate end-to-end. The number that actually matters is the next table.

Detector, scored against ground truth — 5 seeds, 22,538 quiet samples, 516 injected episodes, shipped config:

spike	drop	drift
Episode recall	83%	74%	25%
Event type correct, given a detection	85%	91%	63%
False positives: 0.18% of quiet samples. Raising drift_z_threshold from 3.5 to 4.0 gives 0.15% at 81/70/18% recall — the tradeoff is one config line.

Event-type accuracy is measured on the leading edge of each episode, which is the hardest sample to classify: the excursion has barely started, so its magnitude is smallest there. Scored across the whole episode instead it is 97/98/87%, but that number would be flattering — the leading edge is what the node actually alerts on.

Debouncing (refractory_samples) is worth its own line: it cut the false-positive rate from 0.52% to 0.18% — 2.8× fewer false alerts — with identical recall, because it only ever suppresses repeat reports of an episode already detected.

Federated learning — 3 nodes, 3 distinct climates, held-out set spanning all three:

Start	Round 1	Round 5	Round 8
Cold (random init)	0.250	0.837	0.908
Seeded from the trained artifact	0.958	0.931	0.942
Global accuracy is not monotonic — nodes drift toward their own climate during local epochs and averaging pulls them back — so it oscillates in the 0.90–0.95 band once converged rather than climbing smoothly.

Not yet measured	
Inference latency on Pi CPU	TBD — needs the hardware
Detection latency from onset, real DHT22	TBD — needs the hardware
Known limitations
Drift recall is the weak spot (25%). A gradual ramp is genuinely close to the diurnal cycle in both magnitude and timescale, so the slow baseline's own variance partly masks it. Pushing recall higher costs false positives roughly one-for-one. A CUSUM stage, or conditioning the baseline on time-of-day, is the obvious next step.
Federation is a simulated deployment. The learning, the gradients and the averaging are real; the peer nodes are threads on one machine, not radios.
The risk provider's ambient forecast is mocked. The event-feedback half of the loop is real and closed; the external feed is not.
torch.jit.script is deprecated as of torch 2.13. It still works and is still the lightest option here; torch.export is the migration path.
Project layout
wildsense/
├── config.yaml              # which packs are active
├── run.py                   # entrypoint
├── pipeline.py              # the loop that wires everything together
├── core/                    # contracts, config, registry, logging
├── sensors/                 # base.py, dht22.py, synthetic.py
├── detectors/               # base.py, baseline.py, model.py, train.py, env_anomaly.py
├── federation/              # local_trainer.py, averager.py, simulation.py
├── cloud/                   # s3_sync.py
├── context/                 # risk.py
├── dashboard/               # app.py, state.py, static/index.html
├── tests/                   # pytest suite, no hardware required
├── requirements.txt
└── LICENSE
Generated at runtime and gitignored: artifacts/ (trained model + TorchScript export) and events/ (local snapshot fallback).

License
MIT — see LICENSE.
