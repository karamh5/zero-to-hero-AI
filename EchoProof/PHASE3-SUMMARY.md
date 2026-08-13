# EchoProof - Phase 3 Summary

Deployment Readiness Report. SPEC sections 7 and 9.
Completion condition from PHASES.md: one complete, hash-sealed report end to
end. Met.

## 1. The deliverable

`runs/demo-campaign/deployment-readiness-report.html`, 1.44 MB, **zero external
references**. No server, no login, nothing to deploy. It opens in a browser and
can be emailed to a compliance officer or attached to a risk review.

| Measure | Value |
|---|---|
| Turns | 5 |
| Claims adjudicated | 15 |
| Violations | 3 |
| Abstentions | 6 |
| Audio clips embedded and playable | 15 |
| Gate decision | BLOCK RELEASE, 3 critical findings against a threshold of 1 |
| Chain verifies | true |

The gate decision is computed from the criteria pack's own `gate_thresholds`,
not from anything in engine code, so a client with different thresholds gets a
different decision without a code change.

## 2. Citation accuracy on the demo run

All three findings cite the section the fixture set expects, and each quotes the
text of the section it cites.

| Turn | Claim | Cited | Expected |
|---|---|---|---|
| t02 | Threatening suit on a time-barred debt | 1006.26(b) | 1006.26(b) |
| t03 | Furnishing to a credit bureau before contact | 1006.30(a)(1) | 1006.30(a)(1) |
| t04 | Repeated calls without disclosing identity | 1006.14(g) | 1006.14(g) |

The compliant turn, the required initial disclosure, returned `supported`
against 1006.18(e)(1) and produced no finding. That is the case that matters
most for reviewer trust, because a false positive on a correctly handled
disclosure is the fastest way to lose it.

Run to run variance is real and worth stating: an earlier execution of the same
five turns produced four findings with one citing 1006.18(c)(1) instead of
1006.26(b). Temperature is zero, but speech-to-text of synthesized audio and
provider-side nondeterminism still move results between runs.

## 3. A defect the report caught that nothing else did

The first rendered report showed a finding citing 1006.22(f)(1), correctly, for
a postcard violation, and displayed beside it the text of the email-address
provision 1006.22(f)(3).

`rule_text_in` was captured from the top-ranked retrieval candidate before the
judge made its selection. The judge routinely selects something other than rank
1, because rank 1 is unreliable, which is the entire reason the shortlist exists.
Whenever it did, the card cited one section and quoted another.

This is exactly the failure the product exists to prevent. A reviewer checking
the citation against the quote would conclude the tool was wrong and would be
right to. Nothing in the scoring pipeline surfaced it, because scoring compares
section identifiers and never looks at the rule text. It took rendering the
artifact a human would actually read.

Fixed by overwriting the rule text with the text of the section the judge
selected, verified in the evidence log for all three findings, and covered by a
regression test.

## 4. Also delivered

**`agent.turn` is now emitted by `adjudicate_turn`.** It had been emitted only
by the proxy and audio paths, so a fixture run stored claim offsets with no
transcript for them to index into and SPEC section 9's highlighted excerpt could
not be rendered from it. Every entry point now produces a complete log.

**Hash seal, verified working in both directions.**

```
unmodified run          SEAL INTACT
policy version altered  SEAL BROKEN
```

The seal covers agent version, policy pack version and evidence chain head.
Every finding also carries the hash of the log entry recording its decision.

**Tamper rejection.** `EvidenceLog.read` verifies the chain on load, so a
modified log raises rather than rendering into an authoritative looking
document. Covered by a test that edits a transcript in a written log and asserts
the read fails.

**Limitations are in the report, not just in this file.** The report carries a
Known limitations section listing the 34.8 percent detection rate at 2 percent
false positives, the below-70-percent SPEC band, the single-authored ground
truth, the model-dependence of retrieval, the deferred deterministic
comparison, the narrow numeric confidence coverage, and the synthesized audio.
A buyer reads them in the artifact.

## 5. Not done

**Supabase run and findings metadata**, brief audit gap 2, is still open. The
report does not depend on it and nothing else in the pipeline does either. It
belongs with the campaign runner in Phase 4, where there are runs worth indexing.

**Fix-and-rerun view**, SPEC section 9's before-and-after delta, is deferred to
Phase 5 where the fix-and-rerun loop is actually built. The report has no
placeholder for it, because an empty section implying a missing feature is worse
than its absence.

## 6. Known risk carried forward

Audio inlined as base64 put 15 clips into a 1.44 MB file. A 100 call campaign
would be roughly 25 MB and unusable as an email attachment. Acceptable at PoC
scale and stated in the report itself. Production references clips in object
storage by digest, which is already the Production row of CLAUDE.md's stack
table.

## 7. Artifacts

| Path | Contents |
|---|---|
| `engine/report.py` | Report data extraction, gate decision, HTML rendering |
| `scripts/demo_run.py` | Five turns end to end with audio |
| `scripts/build_report.py` | Render a run, or verify its seal |
| `runs/demo-campaign/` | Evidence log, 15 clips, the report, the seal |

Test suite: 75 passing, including 9 new report tests covering seal behaviour in
both directions, self-containment, tamper rejection, and the citation-versus-
quote regression.
