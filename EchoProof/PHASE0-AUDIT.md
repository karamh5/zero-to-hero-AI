# EchoProof - Phase 0 Foundation Audit

Date: 2026-08-12. SPEC sections read: §1, §4, §5, §7.
Scope per PHASES.md Phase 0: status table only, no code changes.

EchoProof is greenfield. Nothing in this audit is a surprise, and that is the
point. The value here is converting eight nouns into eight testable definitions
of done, and naming the inputs that do not exist yet before Phase 1 starts
depending on them.

## 1. Status table

| # | Item | SPEC | Status | Evidence | Definition of done |
|---|---|---|---|---|---|
| 1 | Policy pack (12 CFR 1006) | §1 | missing | No `packs/` directory, no `.json`/`.yaml` anywhere under `EchoProof/` | One record per section carrying `section_id`, `parent_section`, `verbatim_text`, `obligation_type`, `cross_references`, `defined_terms`, plus a corpus-level document hash |
| 2 | Structure-aware chunking | §5 | missing | No `.py` files exist | Chunks split on section boundaries, each chunk retains its parent heading, and no chunk silently spans two sections |
| 3 | Retrieval index (FAISS + BM25) | §5 | missing | No index artifacts, no `requirements.txt`, neither library installed | Both indexes build from the policy pack behind one `Retriever` interface, fused, with rerank of top 50 down to a single governing section |
| 4 | Gate-check number (precision@1) | §5 §11 | missing | No retrieval pairs file, and item 3 does not exist to measure | precision@1 measured against roughly 40 hand-written query/section pairs, plus the two separate confidence thresholds (floor and ceiling) calibrated as distinct values |
| 5 | Normalization + unit tests | §4 | missing | No `tests/`, no `conftest.py` | Spoken and written numbers and relative dates canonicalize deterministically, anchored to call date, with an independent pytest suite that does not import the judge |
| 6 | 50-fixture file + held-out split | §11 | missing | No `fixtures/` directory | 50 seeded-violation items with `ground_truth {verdict, section_id}`, hard negatives labelled separately from greetings, and a held-out split sealed at creation |
| 7 | Span schema + evidence log | §7 | missing | No `.py` files exist | All seven span types emit, the chain hash of entry N includes the hash of entry N-1, and a stored run replays to a byte-identical recomputed chain hash |
| 8 | Model interface | CLAUDE.md #8 | **partial** | Credential verified live and real model IDs confirmed (section 2 below), but no client code exists | One OpenAI-SDK client with configurable `base_url`, `temperature=0`, a pinned dated model string, and tool-calling wired for §3 claim extraction |

Item 8 is the one row that is not `missing`. The credential and the model
identity are established facts as of today, verified against the live API rather
than assumed. Zero lines of client code exist. Calling that `partial` rather
than `built` is deliberate.

## 2. Verified environment facts

Carried forward so Phase 1 does not re-derive them.

| Fact | Value | How verified |
|---|---|---|
| Python | 3.13.3 | `python --version` |
| ffmpeg | 9.0-full_build (Gyan.FFmpeg) | `ffmpeg -version`, installed this session via winget |
| Mistral credential | valid | `GET /v1/models` returned HTTP 200, 55 models |
| eCFR API | reachable, Title 12 `latest_issue_date` 2026-08-06 | `GET /api/versioner/v1/titles.json` |

Model IDs confirmed from the live API, all three with `function_calling=True`
and 262,144 context:

```
mistral-small-2603
mistral-medium-2604
mistral-large-2512
```

**Pin a dated ID, never a `-latest` alias.** `mistral-small-latest` currently
also aliases `magistral-small-latest`, which is a reasoning model. A `-latest`
string can therefore change model *class* underneath a scored run without any
change on our side, which would breach CLAUDE.md decision #9 (whichever backend
produced a scored run's numbers stays the backend for that run). The specific
pin is a Phase 1 decision and is not made here.

## 3. Missing inputs and how they get filled

**Policy corpus.** Decided: pull 12 CFR 1006 from the eCFR API in Phase 1,
storing `verbatim_text` per section together with a document hash. The hash is
what §7 pins as `policy_pack_version` on every finding, and it is what makes the
§9 report seal breakable when the corpus changes.

**Fixtures and retrieval pairs.** Decided: authored by the agent, ground truth
reviewed by the project owner before anything is scored. This is recorded here
as a **named limitation**, not a footnote: the same agent authoring both the
fixtures and the judge is a self-grading bias, and a detection rate measured
that way is weaker evidence than one measured against independently authored
ground truth. Per CLAUDE.md decision #12 this gets a one-line disclosure in the
final Deployment Readiness Report rather than being quietly dropped.

**Held-out split.** Proposed at 15 of the 50 items, leaving 35 for Phase 1
scoring. Sealed at creation in Phase 1 and not read, logged, or optimized
against until Phase 4, per CLAUDE.md decision #10. Phase 0 does not create it.

**Deepgram credential.** Deliberately not requested. It is a Phase 2 gate and
asking early would invite it being used early.

**Supabase.** URL and key are in `.env`. No schema exists. Per CLAUDE.md
decision #11 Supabase holds run and findings metadata only, never evidence
content, so the schema is a Phase 3 concern at the earliest.

## 4. Proposed package layout

Proposal only. Nothing below was created in Phase 0. It follows the conventions
already set by `wildsense/` in this repo: project-local top-level packages, a
root `conftest.py` that puts the project on `sys.path`, a `requirements.txt`,
and a `tests/` directory.

```
EchoProof/
  core/        contracts.py, config.py, hashing.py
  packs/       policy/  scenario/  persona/  criteria/     <- data only
  engine/      adapter.py extract.py deterministic.py judge.py
               evidence.py audio.py report.py runner.py
               retrieval/ base.py chunking.py local_faiss_bm25.py
  models/      client.py            <- the single OpenAI-SDK seam
  scripts/     build_policy_pack.py  build_index.py  score_fixtures.py
  fixtures/    retrieval_pairs.jsonl  fixtures.jsonl  heldout.jsonl
  tests/
  conftest.py  requirements.txt
```

The `engine/` versus `packs/` split is the physical enforcement of CLAUDE.md's
fixed-engine rule: adding a vertical must touch only `packs/`. If a Phase 6 pack
swap requires editing anything under `engine/`, that is a defect in the boundary
and gets reported as one. `wildsense/core/registry.py` already demonstrates this
pattern in this repo, where config names a pack and core never imports it.
`engine/retrieval/base.py` is the seam where the Production OpenSearch swap
lands without touching callers.

## 5. Risks carried into Phase 1

1. **Self-graded ground truth.** Stated above. Highest-severity limitation in
   the project so far, because it discounts the headline number in §11.
2. **Two thresholds, one temptation.** §5 requires the floor and the ceiling to
   stay separate. Collapsing them is the single easiest way to turn a retrieval
   miss into a confident and false "no rule governs this" claim.
3. **Corpus scope.** 12 CFR 1006 is large. If Phase 1 indexes only the sections
   the fixtures touch, precision@1 is inflated by an unrealistically small
   candidate pool. The full part should be indexed even though the fixtures
   exercise a fraction of it.
4. **`-latest` drift.** Covered in §2. Mitigated by pinning a dated ID.

## 6. Verification run

Real console output from this session.

```
=== git ls-files EchoProof/ ===
(empty)

=== recursive listing of EchoProof/ ===
EchoProof\.env
EchoProof\.gitignore
EchoProof\CLAUDE.md
EchoProof\PHASES.md
EchoProof\SPEC.md

=== .py / .jsonl / .faiss / .index / .json / .yaml under EchoProof/ ===
NONE

=== toolchain ===
Python 3.13.3
ffmpeg version 9.0-full_build-www.gyan.dev

=== Mistral /v1/models ===
models returned: 55
mistral-small-2603     function_calling=True  ctx=262144
mistral-large-2512     function_calling=True  ctx=262144
mistral-medium-2604    function_calling=True  ctx=262144
```

`git ls-files EchoProof/` returning empty means nothing under `EchoProof/` has
been committed yet, not that the documents are absent. The recursive listing is
the authoritative view of what exists on disk. `.env` appears there and is
correctly excluded from git by `EchoProof/.gitignore:1`.
