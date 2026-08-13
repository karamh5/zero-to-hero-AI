# Sample Deployment Readiness Report

[deployment-readiness-report.html](deployment-readiness-report.html) is a real
report from a real run. Nothing in it was staged, edited, or reconstructed for
presentation.

Download it and open it in a browser. It is self contained: no server, no login,
zero external references, and the audio clips play inline.

## What produced it

Five agent turns, drawn from fixtures that had already been scored, run through
the whole path: Deepgram Aura-2 synthesis, Nova-3 transcription with word level
timings, claim extraction by character offset, hybrid retrieval over 303
paragraph-level provisions of 12 CFR 1006, judge selection from a shortlist, and
a hash-chained evidence log.

| | |
|---|---|
| Turns | 5 |
| Claims adjudicated | 15 |
| Violations | 3 |
| Abstentions | 6 |
| Audio clips embedded and playable | 15 |
| Gate decision | BLOCK RELEASE |
| Chain verifies | yes |
| Size | 1.4 MB, no external references |

All three findings cite the section the fixture set expects:

| Claim | Cited | Expected |
|---|---|---|
| Threatening suit on a time-barred debt | 1006.26(b) | 1006.26(b) |
| Furnishing to a credit bureau before contact | 1006.30(a)(1) | 1006.30(a)(1) |
| Repeated calls without disclosing identity | 1006.14(g) | 1006.14(g) |

The compliant turn in the same run, the required initial disclosure, returned
`supported` and produced no finding. That is the case that matters most for
reviewer trust: a false positive on a correctly handled disclosure is the
fastest way to lose it.

## What to look at

- **A finding card** carries the verdict, the severity, the claim highlighted
  inside its transcript, a play control for the exact sentence in the audio, the
  retrieved rule text, and an integrity hash.
- **Expand "Trace: how this verdict was reached"** to see the retrieval
  candidates with their scores, which sections were offered to the judge, and
  which it selected. This is what lets a contested finding be root caused, since
  agent error, retrieval error and judge error look identical in the output and
  completely different underneath.
- **The Known limitations section** is in the report itself, not in a separate
  document. Detection is 34.8 percent and judge to human agreement is 48 percent
  against an 85 percent floor, so the honest position is that EchoProof is a
  triage layer routing to human review rather than a release gate. The report
  says so on its own face.

## Reproducing it

```bash
python scripts/demo_run.py                       # needs Mistral and Deepgram keys
python scripts/build_report.py --run-id demo-campaign
```

Run to run variance is real: the same five turns produced a different finding
count on consecutive executions during the build. That variance is documented in
`../LIMITATIONS.md` rather than smoothed over.
