# EchoProof, handover

A pre-deployment compliance assurance layer for enterprise voice AI agents.
This is the complete PoC as delivered in August 2026.

Start with `POC-BRIEF.md` for what it is and why. Read `ARCHITECTURE.md` for the
settled design decisions, and `LIMITATIONS.md` for an honest account of what was
measured and where the system is weakest.

---

## Running it

Requires Python 3.11 or newer.

```
python -m venv .venv
.venv/Scripts/activate          # Windows
source .venv/bin/activate       # macOS and Linux
pip install -r requirements.txt

cp .env.example .env            # then add the keys
```

Start the interface:

```
.venv/Scripts/python scripts/run_ui.py
```

It serves on http://127.0.0.1:8077.

**Use the interpreter inside `.venv`, not a bare `python`.** The system
interpreter has no `openai` module, and the failure is misleading: every page
loads, the availability endpoint reports healthy, and the run fails a few
seconds after it starts. `presentation/DEMO-RUNBOOK.md` records this and the
other failure modes worth knowing before presenting.

The frontend is prebuilt and served by the Python process. To work on it:

```
cd ui && npm install && npm run dev
```

Run the tests with `.venv/Scripts/python -m pytest -q`. All 223 pass with or
without an API key present.

---

## What is in here

| Path | Contents |
|---|---|
| `engine/` | The pipeline: extraction, deterministic checks, retrieval, judge, evidence log, report |
| `adapter/` | The HTTP surface. Chat completions passthrough and the transcript ingest path |
| `api/`, `core/`, `models/`, `store/` | Service layer, config, contracts, persistence |
| `packs/` | The four data packs: policy, scenario, persona, criteria. All client specific input lives here |
| `runs/` | Stored assessments, hash chained. `assessment-0001` is the demo baseline |
| `sample-report/` | A self contained Deployment Readiness Report. Opens in a browser with no server |
| `ui/` | React frontend |
| `tests/` | Test suite |
| `presentation/` | Deck, demo script, runbook and question bank |
| `PHASE*-SUMMARY.md` | What each build phase produced and measured |

---

## The one boundary to preserve

The engine contains no field, constant or branch that knows which industry it is
running in. Everything client specific is one of four data packs. Adding a new
vertical means writing new pack files, not changing engine code.

If a Regulation F rule or an industry assumption ends up inside `engine/` or
`core/`, that is a defect in the boundary rather than a feature.

---

## Regenerated rather than committed

Virtual environments, `node_modules`, build output, and the retrieval cache
under `packs/policy/*/retrieval_cache/`. The cache rebuilds on first run and is
roughly 18 MB across 900 files, which is why it is excluded.

`.env` is excluded. Use `.env.example` as the template.
