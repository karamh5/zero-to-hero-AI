# EchoProof UI

A frontend over the evidence EchoProof already writes. Nothing in it re-judges,
re-retrieves or recomputes a verdict: every number on screen was either read
from a span recorded when the decision was made or computed by the same rule
the scoring scripts print, against the same artifacts, with a test pinning the
result to the published figures.

## What was built

Eight screens on two grounds.

| Screen | Route | What it is |
|---|---|---|
| Bench | `/` | Every run on disk, editorially listed with chain state, seal state, corpus and counts. Violations and abstentions are separate columns everywhere. |
| Run | `/runs/{id}` | Gate decision (computed, never stored), verdict table, campaign flags, findings, policy gap list, integrity block. |
| Case file | `/runs/{id}/claims/{claim_id}` | What was said (offset-sliced), the governing rule verbatim in serif, why, proof, and the expandable forensic trace with every stored candidate, the recorded thresholds, and the judge's selection against rank 1. |
| Rig | `/rig` | Live adjudication as a job: submit a turn, follow the pipeline's own progress events over SSE, watch the sift work. Median 105 s per turn, measured; the screen is built around that number instead of hiding it. |
| Reading | `/reading` | The measurement panel. Detection as a range, agreement shown failing its floor, the triage statement unavoidable at the top. |
| Corpus | `/corpus/{pack}` | Browsable provisions with per-run retrieval coverage and the policy gap list, which contains only `no_governing_rule`. |
| Delta | `/delta` | Fix-and-rerun, read from `rerun.json`. Closed, persisted, new and improved come from `engine/rerun.py`; the UI computes none of them. |
| Report | `/runs/{id}/report` | The filed HTML artifact, served and framed, never rebuilt. |

## Architecture

```
api/            read-only FastAPI router + the adjudication job manager
  runsvc.py       run discovery, chain-verified loading, span joins via
                  engine.report.extract_report_data, clip digest index
  measurements.py the reading's figures, computed from artifacts with a
                  fidelity test pinning them to the published numbers
  jobs.py         submit/stream: one worker thread, lazy stack load,
                  SSE bridging engine.pipeline's on_progress untouched
  router.py       the /api surface plus SPA static serving
  tests/          15 tests (tests/ itself was not touched)
ui/             Vite + React + TypeScript, no CSS framework
scripts/run_ui.py  the server, credentials optional
```

The router is mounted by `adapter/proxy.py` inside `create_app`, wrapped so an
attach failure can never break the proxy, for the same reason a capture
failure never becomes a request failure. The two proxy invariants are covered
by the existing `tests/test_proxy.py`, which still passes unmodified.

Why no Tailwind: the design system is three typefaces, two grounds and a
handful of signal colors with strict salience rules. A utility framework's
defaults are exactly the look section 14 of the build brief bans, and a plain
CSS custom-property token layer (`ui/src/styles/tokens.css`) is smaller and
holds the rules in one file.

Live adjudication writes a new run directory through the engine's public
pipeline, the same way `scripts/run_proxy.py` does, so a rig turn lands on the
bench beside the recorded runs with a verifiable chain of its own.

## The design system, briefly

Three kinds of authority, three faces: verbatim regulatory text in Source
Serif 4 and nothing else; identifiers, hashes, scores, offsets and verdict
strings in IBM Plex Mono; headings and navigation in Archivo. Two grounds:
warm paper for evidence and reading, graphite for the rig. Signal color
encodes state only, and area is inversely proportional to salience: a
contradicted finding earns a 4 px rule under the flagged words and a mono
label, never a red card. The three abstention tints are quiet grey-blues;
`conflicting_sections` additionally carries a dashed glyph and an explicit
"least reliable state" note, because it agreed 0 of 3 in blind labelling. All
text tokens hold WCAG AA on their grounds (checked arithmetically; the
abstention tints were darkened for it). Fonts are bundled locally; the UI
makes no external network request.

Motion is two families. Instrument motion happens only when a real event
arrives: the query ripple, candidates lifting to the ranked pool, the settling
when a verdict lands. Between events the screen is still, and stillness is
information. Transport motion is the settling transition on claim rows and
transcript highlights. `prefers-reduced-motion` renders end states
immediately.

## Honesty mechanics worth knowing

- There is no percentage anywhere on the adjudication path and no
  indeterminate spinner. The only moving number is an elapsed clock set
  against the measured median from `demo/latency.json`.
- The live sift never invents a score. `retrieve.done` carries a candidate
  count and the top score, so lifted candidates land in a neutral ranked pool
  and only the top candidate sits on the axis. The full recorded distribution
  is drawn only after the evidence log exists to supply it.
- Transcript highlights slice by stored offsets. Nothing searches for claim
  text, trims, or re-normalises whitespace.
- The rule text on a case file is `judge.rule`'s `rule_text_in`, which is the
  judge's selected section. The Phase 3 defect (citing one section while
  quoting another) cannot be reintroduced by this UI because it never touches
  the top candidate's text.
- Threshold dragging on the trace is labelled inspection only, and one click
  restores the recorded values. The recorded verdict never changes.
- Detection renders as a range with per-run ticks on a 0 to 1 rail. The two
  endpoints come from `runs/fixtures-dev-v2` and `-v3` `scored.json`, computed
  at the operating ceiling read from the campaign run's own recorded
  thresholds. `api/tests/test_measurements.py` fails if the computation stops
  reproducing the published 0.348/0.261 and 0.750/0.833.
- Proxy overhead is parsed from `demo/RUN-SHEET.md` at request time rather
  than written into code, so the figure traces to the repository or is absent.

## Running it

```
python scripts/run_ui.py                # serves API + built UI on :8077
cd ui && npm install && npm run build   # build the frontend once
cd ui && npm run dev                    # or: Vite dev server, proxies /api
python -m pytest api/tests -q           # the UI API tests
```

`scripts/run_proxy.py` serves the same UI surface alongside the capture proxy.
The UI is fully explorable against `runs/` with no API keys present; the rig
checks for `MISTRAL_API_KEY` itself and shows a labelled disabled state
without one. First live adjudication loads roughly 1.5 GB of embedding and
reranker weights (about 20 seconds warm), reported to the client as a
`job.stack` event rather than silence.

## Verified

- 213 tests pass: the 198 existing (including `tests/test_proxy.py`) plus 15
  new under `api/tests`. Nothing under `engine/`, `core/`, `packs/`,
  `fixtures/`, `models/`, `store/`, `labels/` or `tests/` was modified;
  `adapter/proxy.py` changed only to mount the router.
- A live rig run was executed end to end during the build: 49 SSE events over
  252 s, two findings both citing 1006.26(b) for a threatened suit on a
  time-barred debt, four abstentions counted separately, evidence chain
  verifying on the bench afterwards.
- The deterministic short path was exercised live: a $940.00 claim against a
  known-true amount decided in code at 4.8 s with `decided_by:
  deterministic`, while the unrelated $35 fee fell through to the judge
  rather than being manufactured into a violation.
- The sift's worst frame (field, pool, tween, axis at rig size) measures
  0.135 ms against the 16.7 ms 60 fps budget on this machine.
- No screen produces horizontal scroll at desktop width; every interactive
  element is keyboard reachable; verdicts always carry string plus glyph
  shape plus position, never color alone.

## Deliberately not built

- No microphone, no live-voice visualizer, no listening or speaking states.
  None of that exists in this system, and building it would be a lie in
  pixels.
- No re-parsing of the evidence log in the UI. Joins go through
  `extract_report_data`, the same path the filed report uses.
- No editing of anything: the UI is read-only except for submitting a turn to
  the rig, which appends a new run.
- No job cancellation. Adjudication is a blocking pipeline stage sequence;
  a submitted turn runs to completion and its evidence is written.
- The report artifact is framed, not rebuilt.

## Limitations this UI carries

- The build brief's readiness panel lists "cost per 100 calls ~$23". That
  figure is a projection at 25 turns per call printed by
  `scripts/score_fixtures.py` and stored nowhere machine-readable, so the
  reading shows the measured campaign cost instead: $0.82 for 18 calls at 3
  turns per call, from `campaign.json`. A projection would have had to be
  hardcoded, and the rule that every number traces to a file won.
- The brief says 189 tests; the suite on disk holds 198. All 198 pass.
- Runs are cached against the evidence file's mtime and size per process, so
  an externally modified run appears on next read, not instantly.
- SSE reconnection replays all events from the start of the job (server keeps
  the full event list per job in memory). Job state does not survive a server
  restart; the evidence log on disk does.
- The rig's stage log quotes claim text from the live events, which the
  pipeline truncates at 90 characters. Full offsets and untruncated text are
  on the case file once the log is written.
- Visual review during the build was programmatic (DOM text, computed styles,
  contrast arithmetic, layout overflow checks, canvas frame timing). The
  browser pane could not composite screenshots in this environment, so pixel
  judgment relied on the token system rather than on rendered captures.
