# EchoProof UI

A frontend over the evidence EchoProof already writes. Nothing in it re-judges,
re-retrieves or recomputes a verdict: every number on screen was either read
from a span recorded when the decision was made or computed by the same rule
the scoring scripts print, against the same artifacts, with a test pinning the
result to the published figures.

## The agent-only guarantee

**Only agent turns are ever adjudicated.** Consumer turns are context: they are
never extracted from, never given a verdict, never counted.

An audit found this held by convention at the proxy and the campaign runner,
was unenforceable in the engine, and did not hold at all for the rig, which
accepted any pasted text with no speaker labels. Two things changed.

`engine/conversation.py` now owns conversation adjudication. Turns carry an
explicit role, an unrecognised role is refused rather than defaulted (guessing
either way is worse: to consumer drops agent turns from adjudication, to agent
scores the consumer), and only agent turns reach the extractor. Consumer turns
travel to the judge as labelled context, which is what lets it tell whether an
agent responded correctly to a dispute, a cease-contact request or a
wrong-party statement. Context is opt-in and defaults to off, so runs scored
before it existed remain comparable.

The rig submits prepared conversations by id. `POST /api/adjudicate` refuses
free text outright. Eight tests in `api/tests/test_conversation.py` pin the
rule, including one that asserts no consumer utterance ever reaches the
pipeline as a transcript while both of them do arrive as context.

## The prepared library

`packs/conversation/<pack>/conversations.jsonl` holds role-labelled
conversations for each corpus, grouped by the verdict they demonstrate.
`scripts/verify_conversations.py` runs each one through the real pipeline and
writes the observed outcome to `verified.json` beside it.

The UI groups conversations by the outcome that was **recorded**, not the one
they were authored to demonstrate, and marks anything not yet verified as
such. A library that promises outcomes it does not produce would be worse than
no library, because the one place it failed would be in front of an audience.

## What was built

Eight screens on two grounds.

| Screen | Route | What it is |
|---|---|---|
| Home | `/` | The front door. A Compliance Core built from the product's own parts, editorial statements at scale, the pipeline in five moves, the five verdict states, and four ways in. |
| Bench | `/bench` | Completed assessments as objects: a large assessment number, the title whoever ran it chose, corpus, verdict summary, and audio stated present or absent explicitly. |
| Rig | `/rig` | A configurator: corpus, then a prepared conversation grouped by recorded outcome, then a title, then run. The full source conversation is shown before it runs, with consumer turns marked context only. |
| Run | `/runs/{id}` | Gate decision (computed, never stored), verdict table, campaign flags, findings, policy gap list, integrity block. |
| Case file | `/runs/{id}/claims/{claim_id}` | What was said (offset-sliced), the governing rule verbatim in serif, why, proof, and an eight-step evidence trace whose retrieval step opens the candidate field. |
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
  conversations.py the prepared library and its recorded outcomes
  tests/          25 tests (tests/ itself was not touched)
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

## The visual language, and where it came from

Eight reference sites were studied by reading their live computed styles
rather than by looking at screenshots, which is how the numbers below are
specific. Nothing was copied: each row is a technique, extracted and then
rebuilt in EchoProof's own terms.

| Studied | Measured there | Expressed here |
|---|---|---|
| racing.porsche.com | 1001 px display type at line-height 0.91, near-black ground, one accent | Colossal display at line-height 0.86 and negative tracking; the wordmark sets at 272 px on a desktop viewport |
| rioproperty.co.za | `clip-path` and transform reveals on `cubic-bezier(0.9, 0, 0.1, 1)` | Headings wipe in line by line from a masked block; `--ease-reveal` is that curve |
| leoparpeix.com | A label element tracking the cursor; expo-out `cubic-bezier(0.16, 1, 0.3, 1)`; staged intro delays | The reticle cursor with its coordinate readout and contextual label; `--ease-settle` is that curve; the hero object settles once on entry |
| dich-fashion.webflow.io | 11.6 px technical labels at 2 px tracking beside large numerals | The system ticker, built from real span names, verdict strings, run ids and chain hashes |
| faers.tech | Negative tracking throughout, counters that animate on arrival, 0.15 s micro-hovers | `Counter` on real figures, `--dur-small` hovers, tracking tightened across the display scale |
| zalak-patel.com, lxlcreative.co.uk | Work presented as objects with weight rather than tiled cards | Bench entries and the landing's four doors |

The Compliance Core is one object in many meaningful states, which is the
Orb principle rather than the orb itself. It is built from EchoProof's own
parts: a ring of policy sections, a cluster of claim fragments, retrieval
links that appear only while retrieval is running, and a chain of evidence
segments that closes when a run is sealed. It is not a microphone, a waveform
or a reactor, because none of those is what this product does.

The rule that keeps it honest: **the core changes state only when a real
backend event arrives.** Idle rotation is an object being looked at, not work
being done, and it slows further the longer a section is read. Its one
continuous input, `amplitude`, is measured from decoded audio while a clip is
genuinely playing, which is why the core beside a clip moves with the
evidence rather than on a timer.

The cursor hides the native pointer and replaces it, rather than drawing a
second mark alongside it. `cursor: none` is applied by the component once it
has decided it is taking over, never by a stylesheet, so a coarse pointer, a
reduced-motion preference or a failed mount leaves the system cursor intact.

## The design system, briefly

Three kinds of authority, three faces: verbatim regulatory text in Source
Serif 4 and nothing else; identifiers, hashes, scores, offsets and verdict
strings in IBM Plex Mono; headings and navigation in Archivo. One ground,
deep graphite, so the instrument reads as an instrument and verbatim rule
text sits on it like paper under a lamp. The only paper surface left is the
filed report artifact, which is a document and is rendered as one. Every
text token was checked against every surface it lands on: a sweep of the
rendered pages across five routes found one failure, a marquee separator
glyph at 1.7:1, now fixed. Signal color
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
information. Transport motion covers reveals, route transitions and hovers.
`prefers-reduced-motion` renders end states immediately and never arms the
reveal system at all.

**Reveals fail open.** Content is visible by default; the hidden-then-revealed
state is armed only once a `js-motion` class is set at startup, and each
reveal carries a 2.5 second dead man's switch that shows it regardless of
whether the intersection observer ever reported. A failed bundle, a disabled
script or a document that was backgrounded at load therefore yields a page
with no animation rather than a page with no text. The same principle governs
the hero: its settled state is the CSS default and the entrance is expressed
as a departure from it.

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
- Proxy overhead is parsed from `demo/RUN-SHEET.md` at request time rather
  than written into code, so the figure traces to the repository or is absent.
- The landing page has no hardcoded fallback figures. If the API cannot be
  reached its numbers are absent and it says so, because a front page quoting
  a number the system cannot currently produce is the exact failure this
  product exists to catch.
- The rig's conversation groups come from recorded outcomes, so a conversation
  that stops producing what it was written to demonstrate moves group rather
  than lying in place.
- The ticker's strings are the real vocabulary: span type names, the five
  verdict states, run ids and chain hash prefixes read from disk. A ticker of
  invented technical-looking strings would be set dressing.

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

- 223 tests pass: the 198 existing (including `tests/test_proxy.py`) plus 25
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
  0.135 ms against the 16.7 ms 60 fps budget on this machine. The landing's
  corpus object, projecting and depth-sorting all 303 provisions every frame,
  measures 0.68 ms, which is 25 times inside the same budget.
- No screen produces horizontal scroll at desktop width; every interactive
  element is keyboard reachable; verdicts always carry string plus glyph
  shape plus position, never color alone.
- Every text colour token was checked arithmetically against every ground it
  is used on. One genuine failure was found and fixed: the trace accent
  measured 4.31:1 on the sunken ground the rig's stage log sits on, so it was
  darkened to `#166c78`, which holds 4.88:1 there and better elsewhere.
- Split display headings carry a spaced `aria-label`, so a heading that reads
  as two visual lines is not announced as "Thebench".

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

- The measurement screen was removed from the product at the owner's
  direction. `api/measurements.py` and its fidelity test remain, so the
  figures are still computed and still pinned to the artifacts; they are
  simply not part of the customer-facing narrative. `LIMITATIONS.md` remains
  the honest internal record.
- Some prepared conversations do not yet produce the outcome they were
  written to demonstrate. Those are grouped by what they actually produce and
  marked accordingly rather than being quietly relabelled; the ones that
  match are the ones to demonstrate.
- Runs are cached against the evidence file's mtime and size per process, so
  an externally modified run appears on next read, not instantly.
- SSE reconnection replays all events from the start of the job (server keeps
  the full event list per job in memory). Job state does not survive a server
  restart; the evidence log on disk does.
- The rig's stage log quotes claim text from the live events, which the
  pipeline truncates at 90 characters. Full offsets and untruncated text are
  on the case file once the log is written.
- Visual review during the build was programmatic: DOM text, computed styles,
  contrast arithmetic, layout overflow checks, canvas pixel sampling and frame
  timing. The browser pane in the build environment reports
  `document.hidden` and produces no animation frames, so transitions could
  not be watched running. End states were verified instead by forcing every
  animation to completion through the Web Animations API and re-measuring,
  and the canvas by sampling its painted pixels. Timing and easing were
  therefore chosen from the measured reference values rather than judged by
  eye, and are the most likely thing to want adjusting on a real screen.
- The custom cursor is disabled for coarse pointers and for reduced-motion
  users, so on touch devices the interface is the native one throughout.
