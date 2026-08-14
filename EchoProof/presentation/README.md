# Presentation kit

Everything needed to present EchoProof, at any length, to any audience.
Built against the running system rather than against documentation: every UI
instruction in every script was verified by walking the interface at
`http://127.0.0.1:8077`, and every figure is traced to the artifact that
produced it in the table below.

Nothing in this directory changes the product. Nothing outside this directory
was created or edited, with one exception recorded in section 5.

---

## 1. What is here

| File | What it is | Use it when |
|---|---|---|
| [tomorrow/deck.html](tomorrow/deck.html) | 7 slide internal deck, offline, arrow keys, `N` for presenter notes | Tomorrow, AI Launchpad |
| [tomorrow/SCRIPT-5MIN-TOMORROW.md](tomorrow/SCRIPT-5MIN-TOMORROW.md) | Word for word 5 minute script on a 15 second clock | Tomorrow. **Rehearse this one.** |
| [demo-day/deck.html](demo-day/deck.html) | 12 slide deck with 7 original inline SVG diagrams | Demo day, and any 10 to 15 minute slot |
| [scripts/SCRIPT-2MIN-ELEVATOR.md](scripts/SCRIPT-2MIN-ELEVATOR.md) | 2 minutes, no live run, one screen | Corridor, lift, quick intro |
| [scripts/SCRIPT-5MIN-INTERNAL.md](scripts/SCRIPT-5MIN-INTERNAL.md) | Pointer to tomorrow's script plus adaptation notes | A 5 minute slot that is not tomorrow |
| [scripts/SCRIPT-10MIN-STANDARD.md](scripts/SCRIPT-10MIN-STANDARD.md) | 10 minutes, one live run, optional slides cut | The default external talk |
| [scripts/SCRIPT-15MIN-DEMO-DAY.md](scripts/SCRIPT-15MIN-DEMO-DAY.md) | 15 minutes, full deck, the strongest conversation live | Demo day |
| [scripts/SCRIPT-BUSINESS-AUDIENCE.md](scripts/SCRIPT-BUSINESS-AUDIENCE.md) | 10 minutes led by cost and exposure | Buyers, executives |
| [scripts/SCRIPT-TECHNICAL-AUDIENCE.md](scripts/SCRIPT-TECHNICAL-AUDIENCE.md) | 15 minutes led by the isolation boundary and methodology | Engineers, ML people |
| [QA-BANK.md](QA-BANK.md) | 16 themed groups, every answer under 30 seconds spoken, plus 7 hostile questions | Prep, and the night before |
| [DEMO-RUNBOOK.md](DEMO-RUNBOOK.md) | Pre-flight, warm-up, what to run, failure playbook | Every single time you present |

**Start here:** read `DEMO-RUNBOOK.md` section 1, then rehearse
`tomorrow/SCRIPT-5MIN-TOMORROW.md` once end to end with a timer.

### Why tomorrow's deck has 7 slides rather than "a couple"

Patrick asked for a couple of slides. The launch-then-talk-then-return
structure requires 145 seconds of spoken content while the adjudication runs,
and 3 slides cannot carry that without the room watching one static image for
two and a half minutes. Slides 3 to 6 are the wait. Slide 5 is marked
cuttable in its presenter notes if the run returns early.

---

## 2. The source table

Every figure used anywhere in this kit, and where it came from. Verified by
reading the artifact, not by trusting a summary.

| Figure | Value used | Source | Field or location | Verified how |
|---|---|---|---|---|
| Reg F provisions | 303 | `/api/corpus` and `/corpus/reg_f` | `record_count` | Live UI and API |
| Telecom provisions | 15 | `/api/corpus` | `record_count` | Live UI and API |
| Provisions on home screen | 318 | `/` home counter | rendered counter | Live UI. Sum of both packs |
| Claim detection | 0.261 to 0.348 | `/api/measurements` | `detection.low`, `.high` | API, from `runs/fixtures-dev-v2,v3/scored.json` |
| Citation precision | 0.750 to 0.833 | `/api/measurements` | `citation_low`, `citation_high` | API |
| False positive rate at operating point | 0.020 and 0.060 | `/api/measurements` | `detection.runs[].false_positive_rate` | API |
| Retrieval ceiling | 0.548 | `/api/measurements` | `ceiling` | API |
| Retrieval floor | 0.4937 | Case file `PROOF` block | `thresholds` | Live UI |
| Conflict margin | 0.02 | Case file `PROOF` block | `thresholds` | Live UI |
| Judge to human agreement | 0.480 | `labels/agreement.json` | `raw_agreement` | File read |
| Cohen's kappa | 0.310 | `labels/agreement.json` | `cohens_kappa` | File read |
| Agreement floor | 0.85 | `labels/agreement.json` | `floor`, `meets_floor: false` | File read |
| `conflicting_sections` agreement | 0 of 3 | `labels/agreement.json` | `by_verdict.conflicting_sections` | File read |
| Campaign pass@3 | 1 of 5 graded | `runs/campaign/campaign.json` | `scenarios[].pass_at_3`, 5 non control | File read |
| Control false positives | 0 of 3 calls | `runs/campaign/campaign.json` | `sc-06-compliant.false_positive_calls` | File read |
| Campaign cost | $0.8219 for 18 calls | `runs/campaign/campaign.json` | `cost_usd` | File read |
| Cost per 100 call campaign | ~$23.49, **projected** | `PHASE1-SUMMARY.md` | "Projected per 100 call campaign" | File read. See discrepancy 5 |
| Campaign cache hit rate | 12.6 percent | `runs/campaign/campaign.json` | `cache.hit_rate` 0.126 | File read |
| Adjudication median per turn | 105.11 s | `demo/latency.json` | `median_total` | File read |
| Adjudication worst per turn | 140.33 s | `demo/latency.json` | `worst_total` | File read |
| Extract stage | 5.22 s median, 6.46 s worst | `demo/latency.json` | `samples[].extract` | File read |
| Retrieve stage | 91.11 s median, 125.07 s worst | `demo/latency.json` | `samples[].retrieve` | File read |
| Judge stage | 8.80 s median, 20.80 s worst | `demo/latency.json` | `samples[].judge` | File read |
| Documented stack startup | 20.17 s | `demo/latency.json` | `startup_seconds` | File read. See discrepancy 6 |
| **Measured cold stack load** | **~40 s** | this session | job `loading_stack` 4.0 s to 44.1 s | Timed live run |
| **`rf-04-creditreport` full run** | **120.2 s** | this session | submit to `done`, warm | Timed live run |
| **`rf-06-thirdparty` full run** | **224.3 s** | this session | submit to `done`, warm | Timed live run |
| Proxy overhead | 0.129 ms client, 0.036 ms server | `PHASE2-SUMMARY.md` | overhead table | File read |
| Proxy budget | 50 ms | `SPEC.md`, `PHASE2-SUMMARY.md` | budget | File read |
| Failure drill | 7 cases, 0 crashes | `demo/failure_drill.json` | `cases`, `crashes` | File read |
| Injection did not flip | `injection_flipped: false` | `demo/failure_drill.json` | field | File read |
| Evidence chains verifying | 41 of 41 | `/api/runs` | `chain_ok` on every run | API, all true |
| Tests passing | 223 | `.venv/Scripts/python -m pytest -q` | `223 passed in 4.50s` | Ran it |
| Lowest retrieval top-1 | 0.5009 across 71 calls | `LIMITATIONS.md` | retrieval floor section | File read |
| Off corpus control score | 0.5012 to 0.5059 | `LIMITATIONS.md` | same | File read |
| Retrieval question leakage | 41 percent of 56 pairs | `LIMITATIONS.md` | model independence section | File read |
| Authorship advantage | 0.741 against 0.429 precision@1 | `LIMITATIONS.md` | ground truth section | File read |
| Held out detection | 0.444 against dev 0.348 | `LIMITATIONS.md` | held out section | File read |
| Cache speedup on hit | 1256x | `LIMITATIONS.md` | throughput section | File read |
| Hero finding | `1006.6(d)(1)`, critical, score 0.716 | `/runs/prepared-reg_f-rf-06-thirdparty/claims/rf-06-thirdparty-t00-c02` | case file | Live UI |
| Credit bureau finding | `1006.30(a)(1)`, 2 critical | `/api/runs/prepared-reg_f-rf-04-creditreport/findings` | `section_id` | API and live run |
| Validation supported claims | 4 of 4 supported | `/api/runs/prepared-reg_f-rf-11-validation/findings` | verdicts | API |
| Delta closed | `1006.18(b)(3)` | `/delta` | `CLOSED` | Live UI |
| Model | `mistral-large-2512` | Case file `PROOF` block | `MODEL` | Live UI |
| Reranker | `BAAI/bge-reranker-base` | Case file `PROOF` block | `RETRIEVER` | Live UI |

---

## 3. Verified in the running UI

Walked at `http://127.0.0.1:8077` during this session. Every label below was
read off the live DOM, not from source.

- Nav `BENCH RIG CORPUS DELTA`; home buttons `OPEN THE BENCH`, `RUN AN ADJUDICATION`
- Home counters 318 provisions, 976 claims, 2886 spans; five states split 2 decision, 3 abstention
- Bench card anatomy: number, title, `REG-F`, kind tag, `CHAIN VERIFIED`, four counts, audio line, `OPEN CASE FILE →`
- Rig steps `01 / SELECT CORPUS`, `02 / SELECT CONVERSATION`, `03 / ASSESSMENT TITLE`, button `RUN ADJUDICATION →`
- Rig groups `SUPPORTED 4`, `CONTRADICTED 3`, `RETRIEVAL BELOW CONFIDENCE 5`, and every conversation title
- Rig state change: title placeholder is `choose a conversation first` and the run button is disabled until a conversation is selected
- `SOURCE CONVERSATION` panel labels turns `CONSUMER context only` and `AGENT`
- Run page headings, gate `BLOCK RELEASE` with its reason string, `POLICY GAP LIST` empty state, `INTEGRITY` block
- Case file headings and the eight trace step names, and that step `04 RETRIEVAL` renders **open** by default
- Corpus filters, pack counts `reg_f (303)` and `synth_telecom (15)`
- Delta categories `CLOSED PERSISTED NEW` and the `Fix verified` banner
- Report route frames `/api/runs/demo-campaign/report` with a `download the artifact` link
- Stage log labels, read from `ui/src/screens/Rig.tsx` and confirmed by a live run

## 4. Taken from documentation and artifacts

Not observable in the UI, so read from files: all detection, precision,
agreement, campaign, latency, failure drill, cost and proxy figures; every
limitation in `LIMITATIONS.md`; the stack and production table from `CLAUDE.md`.

---

## 5. Discrepancies, and which value was used

| # | Brief said | Repo says | Used |
|---|---|---|---|
| 1 | 189 tests | **223 passed** | 223. Ran the suite |
| 2 | Citation precision high 0.83 | **0.833** | 0.833 |
| 3 | 303 provisions | UI home shows **318** | Both. 303 is Reg F, 318 includes the 15 telecom provisions. Scripts say 303 and explain 318 if asked |
| 4 | Delta has four categories including improved | **Three** categories; `improved` is a boolean in `engine/rerun.py:47` rendering as `Fix verified` | Three |
| 5 | ~$23 per 100 calls | `campaign.json` measured **$0.8219 for 18 calls**; the $23.49 figure is a **projection** in `PHASE1-SUMMARY.md` at roughly 25 turns per call | Lead with the measured $0.82, label $23.49 as a projection. Per your instruction |
| 6 | 20 s warm-up | `demo/latency.json` says 20.17 s, but a timed cold start this session took **~40 s** | 40 s in the runbook, because being early costs nothing and being late costs the demo |
| 7 | 140 s worst case per adjudication | Correct **per turn**. Every prepared conversation has **two** agent turns, so full runs measured 120.2 s and 224.3 s | Per conversation measured times, in every script |

### Two corrections that would have broken a script on stage

**The retrieval candidate field is open by default.** Step `04 RETRIEVAL`
renders expanded and its toggle reads `CLOSE`. An instruction to "click to open
the retrieval step" would close it in front of the room. Every script says do
not click it.

**`Written contact by postcard` is not a usable supported example.** The rig
groups it under `SUPPORTED` by recorded outcome, but the stored run produces
**0 supported and 4 abstentions**. Its `verified.json` also disagrees with its
run directory: 5 claims with 1 supported against 4 claims with 0 supported. The
supported example used throughout is `Validation notice contents described`,
which is 4 claims, 4 supported, 0 abstentions.

### One change outside this directory, on your instruction

`runs/assessment-0003` was deleted. It was an untracked junk run titled
`test 1`, and it was the first card on `/bench`. Two further runs created while
timing the adjudications, `assessment-0003` and `assessment-0004` titled
`Timing rehearsal`, were also removed. Nothing else outside `presentation/` was
created, edited, renamed or deleted.

---

## 6. Open questions

1. **Bench clutter remains.** Seven `RIG 20260813 ...` cards and one `SMOKE`
   card are still on the bench with generated titles. They are harmless but
   untidy. Deleting those run directories is a one line change you may want
   before demo day; I left them alone.
2. **Pricing is unvalidated.** The QA bank says so explicitly rather than
   inventing a number. If you validate a price before demo day, update the
   pricing group in `QA-BANK.md`.
3. **`demo/RUN-SHEET.md` and `demo/DEMO-GUIDE.md` describe an older
   `scripts/run_demo.py` flow** with different timings and list
   `Written contact by postcard` as a supported demo. They are not wrong about
   the CLI path, but this kit supersedes them for anything UI based. I did not
   edit them.
