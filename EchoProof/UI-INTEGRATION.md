# Building a UI on EchoProof

What a front end can attach to, what it must design around, and what will bite
you. Written after the system was measured, so the constraints below are the
real ones rather than the intended ones.

## The one constraint that shapes everything

**A single turn takes up to 140 seconds to adjudicate.** Median 105 s. Measured,
not estimated, in `demo/latency.json`:

| Stage | Median | Worst |
|---|---|---|
| Claim extraction | 5.2 s | 6.5 s |
| Retrieval | 91.1 s | 125.1 s |
| Judge | 8.8 s | 20.8 s |

Retrieval dominates because each claim issues two or three queries and each one
reranks 50 candidates on CPU.

**Do not design a request-response UI around this.** Anything that waits
synchronously for a verdict will look broken. Build it as a job: submit, stream
progress, render when done. The pipeline already emits the events for that.

A retrieval cache exists and is 1256x on a hit, but the measured hit rate in a
live campaign was 12.6 percent, because agent replies diverge and produce
different claims. Do not plan around warm-cache timings.

## What to attach to

### 1. Progress events, already emitted

`engine.pipeline.adjudicate_turn(..., on_progress=callable)` calls back with
`(stage: str, detail: dict)` at every stage boundary. `engine/progress.py` has a
terminal printer; a web UI wants the same events over SSE or a websocket.

Stages, in order: `extract.start`, `extract.done`, then per claim
`claim.start`, either `deterministic.decided` or
`retrieve.query` (once per question) then `retrieve.done`, `judge.start`,
`judge.done`, and finally `evidence.written`.

`retrieve.query` carries `number` and `of`, which is the only honest basis for a
progress indicator. **Do not synthesise a percentage from elapsed time.** The
product's whole argument is that its outputs are checkable, and a bar that
advances while nothing happens is the one dishonest pixel in the room.

### 2. The HTTP surface, already running

`adapter/proxy.py` is a FastAPI app. Start it with `scripts/run_proxy.py`.

| Route | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible passthrough, captures the turn |
| `POST /v1/transcripts` | Submit a turn directly, for speech to speech stacks |
| `GET /healthz` | Liveness plus capture queue stats |
| `GET /metrics` | Proxy overhead distribution and queue counters |

Adding UI routes to this app is the shortest path. It already has the capture
queue, and `CaptureQueue` runs adjudication on a worker thread, so a UI can
submit and poll rather than block.

Two invariants not to break: the proxy returns upstream responses **unmodified**
and never delays them for adjudication, and a capture failure never becomes a
request failure. Both are covered by tests in `tests/test_proxy.py`.

### 3. The evidence log, which is the real data model

Every run writes `runs/<run_id>/evidence.jsonl`: append-only, hash-chained,
verified on read. A UI should read this rather than inventing its own store.

Span types and what each carries:

| Span | Useful fields |
|---|---|
| `agent.turn` | `transcript`, `transcript_hash`, `audio_ref` |
| `extract.claims` | `claims` with `char_start`, `char_end`, `claim_type` |
| `check.deterministic` | `value_parsed`, `expected_value`, `result` |
| `retrieve.rule` | `candidates` with scores, `retriever_config`, `thresholds` |
| `judge.rule` | `verdict`, `rationale`, `severity`, `rule_text_in`, `offered_section_ids`, `judge_selected_score` |
| `finding.emit` | `audio_clip_ref`, `clip_start_s`, `clip_end_s` |

`engine/report.extract_report_data()` already joins these into `Finding` objects.
Reuse it rather than re-parsing; it is what the HTML report is built from and it
handles the joins.

### 4. The report renderer

`engine/report.render_html()` produces the whole self-contained artifact.
`scripts/build_report.py` wraps it. If the UI needs a downloadable deliverable,
call this rather than rebuilding the layout.

## Things that will bite you

**Claim offsets are into a specific transcript string.** `char_start` and
`char_end` index the transcript in the `agent.turn` span for that turn, not any
other version of the text. Re-normalising whitespace or trimming before
highlighting will silently misalign every highlight. Slice by offset; never
search for the claim text.

**Audio clips are content-addressed files under `runs/<id>/clips/`.** The
evidence log references them by digest. Serving them means mapping digest to
path. Inlining as base64 works at PoC scale and does not scale: 15 clips made a
1.4 MB report, so a 100 call campaign would be roughly 25 MB.

**Verdicts are exactly five strings** and there is no sixth:
`supported`, `contradicted`, `no_governing_rule`,
`retrieval_below_confidence`, `conflicting_sections`.

Three of those are abstentions. **Count them separately from findings
everywhere.** An abstention is a refusal to decide, and a UI that totals them
into a findings count overstates what the system detected. `Verdict.is_abstention`
exists for this.

**Only `no_governing_rule` belongs in a policy gap list.** A judge rejecting the
sections it was shown is a retrieval failure and goes to human review. Getting
this wrong tells a client their rulebook has a hole when it does not, which is
the most damaging output this product can produce.

**Severity comes from the criteria pack**, not from engine code. Read
`packs/criteria/criteria.json`. A client with three labels and a client with
five both work without a code change; hardcoding a severity scale in the UI
breaks that.

**The gate decision is computed, not stored.** `engine/report.gate_decision()`
reads the client's own `gate_thresholds`.

## Running it

```bash
python scripts/run_proxy.py                 # the API, port 8077
python scripts/run_demo.py --list           # the demo shortlist
python scripts/run_demo.py --rule "1006.18(b)(3)"
python scripts/build_report.py --run-id demo-campaign
```

Needs `MISTRAL_API_KEY` always, `DEEPGRAM_API_KEY` for audio. First run
downloads roughly 1.5 GB of embedding and reranker weights.

## What the UI should say out loud

Detection is 26 to 35 percent and judge to human agreement is 48 percent against
an 85 percent floor. **EchoProof is a triage layer routing to human review, not
a release gate**, and the HTML report states that on its face. A UI that presents
findings as authoritative without that framing would be making a claim the
measurements do not support.

The strong parts are worth surfacing prominently: the cited rule text sits next
to every finding so a reviewer can check it in seconds, the expandable trace
shows the candidates and scores behind a verdict, and the integrity hash makes
the record tamper evident. Those are the reasons to trust a finding, and they
are what a generic scoring rubric cannot offer.
