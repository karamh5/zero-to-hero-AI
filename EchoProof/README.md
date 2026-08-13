# EchoProof

A pre-deployment compliance assurance layer for enterprise voice AI agents.

An OpenAI-compatible proxy sits in front of a voice agent's LLM call. It
extracts the factual claims the agent makes, retrieves the governing rule from a
client-supplied policy corpus, and issues a five-state verdict carrying an exact
section citation, the verbatim rule text, an audio clip of the sentence, and a
hash-chained evidence entry. The output is a self-contained Deployment Readiness
Report that opens in a browser and can be filed.

The PoC corpus is Regulation F, 12 CFR 1006, pulled live from the eCFR API:
**303 paragraph-level provisions with real section identifiers**.

## What the measurements say

Read this before anything else.

| Measure | Result |
|---|---|
| Claim detection at 2 percent false positives | **0.348** |
| Citation precision at that operating point | **0.750** |
| Campaign pass@3 across five graded scenarios | **1/5** |
| Judge to human agreement | **0.480** against an 0.85 floor |
| False positives on the compliant control scenario | **0 of 3 calls** |
| Cost per 100 call campaign | ~$23 |
| Proxy overhead added to a live call | 0.13 ms median, 50 ms budget |
| Adjudication latency, worst case per turn | 140 s |
| Failure drill | 7 cases, 0 crashes |

**EchoProof is a triage layer that routes to human review. It is not a release
gate.** That is what SPEC section 11 prescribes when judge-human agreement falls
below its floor, and three independent measurements point the same way.

What is genuinely strong is narrower and real: three findings in four cite the
correct governing paragraph, the compliant control produced no false positives
across three runs, every run's evidence chain verifies, and a fix applied to an
agent demonstrably closes the finding it caused.

The full accounting, including how each number was produced and what biases it
carries, is in [LIMITATIONS.md](LIMITATIONS.md). It is not a footnote section;
it is the honest half of the result.

## Quickstart

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
```

Create `.env` in this directory. It is git-ignored and must stay that way.

```
MISTRAL_API_KEY=...
MISTRAL_BASE_URL=https://api.mistral.ai/v1
DEEPGRAM_API_KEY=...          # audio path only
SUPABASE_URL=...              # optional, metadata index only
SUPABASE_KEY=...
```

Build the policy pack from the live eCFR API, then adjudicate a turn:

```bash
python scripts/build_policy_pack_ecfr.py
python scripts/adjudicate_turn.py --text "Pay today and I can remove this from your credit report."
```

The rest of the entry points:

| Command | What it does |
|---|---|
| `scripts/eval_retrieval.py` | Retrieval precision@1 and threshold calibration |
| `scripts/score_fixtures.py` | Score the fixture split, with a PR curve |
| `scripts/run_proxy.py` | Start the capture proxy |
| `scripts/drive_proxy.py` | Drive it as a client agent would, measure overhead |
| `scripts/audio_demo.py` | Speech in, cited clip out |
| `scripts/run_campaign.py` | Six scenarios, three runs, pass@3 and pass^3 |
| `scripts/build_report.py` | Render a run to a Deployment Readiness Report |
| `scripts/fix_and_rerun.py` | Before and after a fix, with the delta |
| `scripts/swap_demo.py` | Adjudicate against a different policy pack |
| `scripts/failure_drill.py` | Broken input must abstain, not crash |
| `scripts/run_demo.py` | The full live demo segment, one command |

## Layout

```
core/          contracts, config, hashing, pack loading
engine/        adapter -> extract -> deterministic -> retrieve -> judge -> evidence -> report
  retrieval/     chunking, hybrid BM25 + dense, cross-encoder rerank, cache
adapter/       OpenAI-compatible capture proxy and transcript ingest
models/        the single model seam, one OpenAI SDK client
store/         optional Supabase metadata index
packs/         ALL client-specific data
  policy/        reg_f (303 sections), synth_telecom (15, control corpus)
  criteria/      severity map, gate thresholds, abstain routing
  scenario/      six scenarios, five seeded plus one control
  persona/       four personas on the four statutory triggers
fixtures/      77 development items, 15 sealed held-out, retrieval pairs
scripts/       every entry point above
tests/         189 tests
runs/          evidence chains, clips, reports (git-ignored)
demo/          run sheet, shortlist, latency, failure drill
```

### The engine and pack split

`engine/` contains no field, constant or branch that knows which industry it is
running in. Everything client-specific is a pack file. Adding a vertical means
adding pack files, not editing code.

This is tested rather than asserted. Phase 6 swapped in a synthetic telecom
corpus using a different numbering convention (`CC-3.1` rather than
`1006.14(b)(1)`) and it adjudicated correctly. The swap found two genuine
boundary defects, both places where engine code assumed CFR-style identifiers;
both now read the convention from the pack manifest. Scanning every executable
line in `engine/` and `core/` for corpus-specific constants returns zero hits.

The swap's own numbers, 5 of 5 detected and cited, are **not** evidence that
EchoProof is more accurate than the Regulation F results say. The synthetic
corpus has 15 sections against 303 and plainer prose, so retrieval on it is a
far easier problem. It proves portability, not accuracy.

## Where the evidence is

Every run writes an append-only, hash-chained evidence log. Entry N's hash covers
entry N-1's, so editing anything in the middle invalidates every hash after it,
and `EvidenceLog.read` verifies the chain on load rather than on request.

| Directory | What it holds |
|---|---|
| `runs/fixtures-dev-v2/` | The scored development split, 77 items |
| `runs/heldout-final/` | The held-out split, scored exactly once |
| `runs/campaign/` | 18 calls, 172 claims, the campaign report |
| `runs/demo-campaign/` | Five turns with audio and playable clips |
| `runs/fix-and-rerun/` | Before and after a fix, with the delta |
| `runs/swap-synth_telecom/` | The pack swap |
| `runs/failure-drill-*/` | Deliberately broken input |

## Documentation

| File | What it covers |
|---|---|
| [CLAUDE.md](CLAUDE.md) | The project constitution and its non-negotiable decisions |
| [SPEC.md](SPEC.md) | Component-level engineering detail |
| [PHASES.md](PHASES.md) | The build sequence |
| [LIMITATIONS.md](LIMITATIONS.md) | Every measured limitation, consolidated |
| [PHASE0-AUDIT.md](PHASE0-AUDIT.md) | Foundation audit |
| [PHASE1-SUMMARY.md](PHASE1-SUMMARY.md) | Retrieval, judge, fixture scoring |
| [PHASE2-SUMMARY.md](PHASE2-SUMMARY.md) | Proxy capture and the audio path |
| [PHASE3-SUMMARY.md](PHASE3-SUMMARY.md) | The report generator |
| [PHASE4-SUMMARY.md](PHASE4-SUMMARY.md) | Campaign, and the held-out split |
| [PHASE5-SUMMARY.md](PHASE5-SUMMARY.md) | Human baseline and fix-and-rerun |
| [PHASE6-7-SUMMARY.md](PHASE6-7-SUMMARY.md) | Pack swap and demo prep |
| [PHASE8-SUMMARY.md](PHASE8-SUMMARY.md) | Regression suite and failure drill |
| [demo/RUN-SHEET.md](demo/RUN-SHEET.md) | Stage sequence, timings, failure table |
| [demo/FAILURE-DRILL.md](demo/FAILURE-DRILL.md) | Broken-input results, injection test |

## Two design decisions worth knowing up front

**The judge only ever sees the retrieved rule text.** Never the full corpus,
never its own knowledge of the regulation. That is what makes a verdict
falsifiable: anyone can read the rule printed on the finding card and check the
reasoning against it. A judge drawing on training knowledge produces verdicts
that sound authoritative and cannot be audited.

**Claims are stored as character offsets, never as restated text.** The
extractor returns a verbatim quote and the offsets are computed in code by
locating it, so a paraphrasing model loses its claim rather than corrupting one.
Those offsets map deterministically onto speech-to-text word tokens, which is
what lets a finding cite the exact sentence in the audio rather than the whole
call.
