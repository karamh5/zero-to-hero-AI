# EchoProof demo run sheet

Every timing here is measured, not estimated. Sources are
`demo/latency.json` and a full timed rehearsal of `scripts/run_demo.py`.

| Measure | Value |
|---|---|
| Full live segment, rehearsed | **158 s (2.6 min)** |
| Adjudication alone, worst case measured | **140 s** |
| Adjudication alone, median | 105 s |
| Stack startup, one time before the demo | 20 s |
| Fix-and-rerun clip duration | 35 s |
| Proxy overhead | 0.13 ms median |

The adjudication wait is the whole shape of this demo. Plan around 140 seconds
of silence, not 105.

## Before the room fills

1. `python scripts/run_demo.py --list` to confirm the shortlist loads.
2. Run one full rehearsal, `python scripts/run_demo.py --rule "1006.18(b)(3)"`.
   This warms the embedding and reranker model load, which is the 20 seconds of
   startup, so the live run does not pay it.
3. Confirm `demo/backup/rerun_clip.txt` and the backup recording exist.
4. Open `runs/campaign/deployment-readiness-report.html` in a second tab, ready.
5. Check the provider is not rate limiting: rate limiting has interrupted runs
   twice during this build.

**Do not clear `packs/policy/reg_f/retrieval_cache/`.** It does not help the
live claim, which is generated fresh, but clearing it makes rehearsal slow and
tempts a rushed setup.

## The four minutes

| Time | What happens | Notes |
|---|---|---|
| 0:00 | **The problem.** One slide. An agent says a balance and offers to remove the debt from a credit report. One clause may breach federal law and nothing catches it before go live. | Do not run long. The demo is the argument. |
| 0:30 | **The architecture.** One diagram, one sentence: the judge only ever sees the retrieved rule text, which is why every verdict is auditable rather than an opinion. | |
| 1:00 | **Observer picks a rule.** Show `run_demo.py --list`. Four rules, each with the number of recorded runs it was caught in. Say plainly that the shortlist comes from measured results and that detection is 34.8 percent, so this is a shortlist rather than an open field. | Honesty here buys credibility for the numbers slide later. |
| 1:15 | **Run it.** `python scripts/run_demo.py --rule "<their pick>"`. The agent prompt is edited by the script, in view. | |
| 1:20 | **The call runs.** Agent turn appears on screen within about 2 seconds. | |
| 1:25 | **Dead time begins.** Start the fix-and-rerun clip: `python scripts/record_rerun_clip.py --play`. It runs 35 seconds. | This is the brief's own design: a finding is only useful if the fix can be verified. |
| 2:00 | Clip ends. Adjudication is still running. Talk through the trace: claim extraction returns offsets, retrieval pulls candidates, the judge selects among them. | Roughly 60 to 100 seconds of talking is needed here. Prepare it. |
| 3:00 | **The finding appears.** Verdict, the exact section, the rule text, the rationale, the integrity hash. | Rehearsed run produced this at 2:37. |
| 3:15 | **The numbers.** Detection 34.8 percent at 2 percent false positives. Citation precision 0.750. Judge to human agreement 0.480 against an 0.85 floor. Say the conclusion out loud: this is a triage layer, not a release gate. | **Not skippable.** See below. |
| 3:45 | **The ask.** An introduction to a real buyer to validate willingness to pay. | |

## The numbers slide is mandatory

The measured position is that EchoProof is a triage layer that routes to human
review. A room that leaves believing it is a release gate is a worse outcome
than a demo that visibly fails, because the first produces a pilot that
collapses on contact with real calls and the second produces a conversation.

State: detection 34.8 percent, judge to human agreement 48 percent against an 85
percent floor, and the fact that the human baseline was self-graded.

## What can go wrong, and what to do

| Failure | Likelihood | Fallback |
|---|---|---|
| **No finding emitted.** Detection is 34.8 percent. Even on a shortlisted rule this can happen. | Moderate | Say so immediately: "that is what a 34.8 percent detection rate looks like, and it is why this is a triage layer." Then play the backup recording. Do not re-run live. |
| **Provider rate limiting.** Hit twice during this build. | Moderate | `models/client.py` retries with backoff automatically. If it exhausts, switch to the backup recording. |
| **Adjudication runs past 3 minutes.** Worst measured is 140 s but the cache is cold for live claims. | Low | Keep talking through the trace. If it passes 200 s, cut to the backup. |
| **Wrong section cited.** Citation precision is 0.750, so one in four is wrong. | Low to moderate | Show it and explain: the trace expands to show the candidates and scores, which is exactly how a contested finding gets root caused. A wrong citation with a visible trace is a better demo than a right one without. |
| **Network drop.** | Low | Everything except the model calls is local. The backup recording needs no network. |
| **Report will not open.** | Very low | It is a single self contained HTML file with zero external references. Copy it to the desktop beforehand. |

## Recorded assets

| Path | What it is |
|---|---|
| `demo/backup/rerun_clip.json` | Timed frames of the fix-and-rerun, replayed from a real run |
| `demo/backup/rerun_clip.txt` | Plain text of the same, if playback fails |
| `demo/shortlist.json` | The four rules, with the runs they were caught in |
| `demo/latency.json` | Stage by stage timings behind the table above |
| `runs/campaign/deployment-readiness-report.html` | The artifact to hand over |
| `runs/demo-live/evidence.jsonl` | The rehearsal's evidence chain |

## The one sentence

If only one thing lands: **the judge only ever sees the retrieved rule text, so
every verdict can be checked against the rule printed next to it.** That is what
makes a finding auditable rather than an AI opinion, and it is the thing no
generic scoring rubric can offer.
