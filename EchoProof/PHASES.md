# EchoProof — PHASES.md

Everything in this file happens today, in this session, in order. Phases are
sequenced by dependency, not by date. A phase starts when the phase before it is
verified, not when a calendar says so. There are no target dates and none should
be reintroduced.

## Setup — before Phase 0
Confirm git is initialized and the remote points at the zero-to-hero-AI repo.
Create EchoProof/requirements.txt (or pyproject.toml) with pinned versions for
every dependency used so far. Both of these happen before any phase work begins
and before the credential prompts.

Then: confirm Python 3.11+ and ffmpeg, create EchoProof/.gitignore covering
.env, collect MISTRAL_API_KEY, SUPABASE_URL and SUPABASE_KEY into EchoProof/.env
without echoing them back, and verify the real model ID against the provider's
/v1/models rather than guessing it. DEEPGRAM_API_KEY is requested at Phase 2,
not earlier.

## Phase 0 — Foundation audit
SPEC: §1 §4 §5 §7. Built/partial/missing table for: policy pack, chunking,
retrieval index, gate-check number, normalization+tests, 50-fixture file, span
schema+evidence log, model interface. No code changes.

Before producing the table, check build history rather than assuming a blank
slate. Look for existing scored results already on disk: fixture scores,
evaluation output, calibrated thresholds, prior run artifacts, evidence logs. If
Phase 1's fixture scoring already has real output on disk, treat it as done and
report it in the audit table rather than re-running it. Only rebuild what is
actually missing or broken.

## Phase 1 — Wire retrieval into judge, score fixtures
SPEC: §5 §6 §11. Headline detection/false-positive numbers from all 50
fixtures excluding held-out.

## Phase 2 — Automatic proxy capture + audio path
SPEC: §2 §8. Live exchange flows proxy->claim->verdict with a playable clip,
zero manual feed.

## Phase 3 — Report generator
SPEC: §7 §9. One complete, hash-sealed Deployment Readiness Report end to end.

## Phase 4 — Campaign runner, six scenarios x three runs
SPEC: §1 §10. Per-scenario pass@3/pass^3. Held-out set scored now, once.

## Phase 5 — Human baseline + fix-and-rerun
SPEC: §11 §12. 25-item blind agreement number. One fix+rerun with a delta.

## Phase 6 — Pack swap, limitations, polish
SPEC: §1 §9. Synthetic-corpus swap, zero engine changes. Limitations named.

## Phase 7 — Demo prep
SPEC: §9 §10. Select and lock the demo-safe scenario (the one guaranteed to
produce a clean live finding under time pressure). Time the live
retrieval+judge path end to end and record actual latency, not an estimate.
Decide and document whether the fix-and-rerun clip played during dead time is
pre-recorded or generated live, and build whichever is chosen. Produce a run
sheet: exact sequence of what happens on stage, what can go wrong, and the
fallback if the live call fails (e.g. a pre-recorded backup take).
Verification: run the full four-minute demo sequence live at least once, start
to finish, without manual intervention.

## Phase 8 — Regression + failure-drill support
SPEC: all. Green test suite. Deliberately broken input -> abstain, not crash.

## Phase 9 — Ship
Add an EchoProof entry to the repo root README. Create EchoProof/README.md
documenting the package layout.
