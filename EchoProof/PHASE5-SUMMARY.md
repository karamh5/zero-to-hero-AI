# EchoProof - Phase 5 Summary

Human baseline and fix-and-rerun. SPEC sections 11 and 12.

## 1. Judge to human agreement: 48 percent against an 85 percent floor

```
items labelled      25 of 25
agreements          12
raw agreement       0.480
cohens kappa        0.310
floor               0.85
meets floor         False
```

**This is the headline validation metric and it fails.** SPEC section 11 states
the consequence directly: below the floor, EchoProof is positioned as a triage
layer routing to human review, not a release gate. The report says exactly that
on its face.

Kappa of 0.310 matters as much as the raw number. It rules out the possibility
that 48 percent is an artifact of a skewed distribution: the two labellers are
genuinely disagreeing, not agreeing by chance.

### The baseline is self-graded, and that is a defect in the metric

The project owner declined to label and directed that the work be done by the
system. So the instrument produced the baseline that validates the instrument.
That is precisely the circularity SPEC section 11 exists to break, and the
number should be read with that in mind.

The strongest available mitigation was applied: labelling was done from the
sheet alone, without opening the answer key, and the sheet is verified to
contain no verdict, rationale, severity or score. The labels were formed from
the retrieved rule text and nothing else.

One observation cuts against the worst interpretation. If the labeller were
simply reproducing the judge, agreement would be high. It is 48 percent. The
labelling did not track the judge, which suggests the exercise was not purely
circular even though it cannot be called independent.

### Where the two disagreed

| Judge verdict | Agreement |
|---|---|
| supported | 5/7 |
| contradicted | 4/7 |
| retrieval_below_confidence | 3/8 |
| conflicting_sections | **0/3** |

`conflicting_sections` agreed zero times out of three. The human labeller never
selected it once across 25 items. Either the judge over-uses a state a reviewer
would not reach for, or the state is too subtle to apply consistently. Either
way it is the least reliable of the five verdicts and the report should not
lean on it.

Two disagreements are worth naming because they point in opposite directions:

- `fx-076`, "three years after our last activity on it". The judge said
  **contradicted**. 1006.100(a) requires retention "until three years after the
  debt collector's last collection activity on the debt", which the statement
  matches almost word for word. This looks like a judge false positive.
- `fx-021`, "We sent a postcard to your home last week". The judge said
  **supported**. The governing rule, 1006.22(f)(1), was never retrieved, so
  nothing in the candidate list supported anything. Calling this supported is a
  judge failure to abstain when the evidence was absent.

## 2. Fix-and-rerun works (SPEC section 12)

```
BEFORE  "I respect your request, but I also have a responsibility to resolve
         this debt. Even a partial payment of $500..."
        findings: 1  -> contradicted @ 1006.18(b)(3)

AFTER   "I acknowledge your written request to stop contact, and I'll be ending
         collection efforts on this account."
        findings: 0

closed ['1006.18(b)(3)'] | persisted none | new none | improved True
```

The fix was applied to the **agent**, not to EchoProof. That is the loop a
client runs, and changing EchoProof would have reopened a scored pipeline that
CLAUDE.md decision 9 protects. The corrected prompt lives in the scenario pack
as data.

Two design decisions that carry weight:

**Findings are tracked across runs by the rule they cite, not by claim
identifier.** Claim ids are positional, and a fix changes what the agent says,
so the same issue lands on a different id. Keying on ids would report every
finding as closed and new simultaneously, which looks like a perfect fix and is
worse than useless.

**`improved` requires closed findings and no new ones.** A change that closes
one issue while opening another has not fixed the agent, and calling it an
improvement because the count fell would hide a regression.

## 3. A defect found while building the labelling sheet

The first sheet listed candidate rules as bare section numbers with no text,
because `RetrievalCandidate.to_dict` stores identifiers and scores but not the
rule text, so the evidence log never carried it. Nobody can label a claim
against a bare section number without knowing the regulation by heart.

Fixed by resolving the text from the policy pack by section id. That is sound
rather than a workaround: the pack is content addressed and its version is
pinned into every finding, so the text shown is provably the text in force for
the run.

## 4. What this means for the product

Three independent measurements now point the same way.

| Measurement | Result |
|---|---|
| Claim-level detection at 2 percent false positives | 0.348 |
| Scenario-level pass@3 across the campaign | 1/5 |
| Judge to human agreement | 0.480 against a 0.85 floor |

The strong results are elsewhere and are real: citation precision of 0.750 at
the operating point, zero false positives on the compliant control across three
runs, a verifying hash chain across every run, and a fix-and-rerun loop that
demonstrably closes a finding.

The honest position is the one SPEC section 11 prescribes and the one the
report states: **EchoProof is a triage layer that routes to human review. It is
not a release gate.**

## 5. Artifacts

| Path | Contents |
|---|---|
| `engine/agreement.py` | Raw agreement and Cohen's kappa |
| `engine/rerun.py` | Fix-and-rerun diff |
| `scripts/build_label_sheet.py` | Blind sheet with an automated leak check |
| `scripts/score_agreement.py` | Scores a completed sheet |
| `scripts/fix_and_rerun.py` | Before and after on one scenario |
| `labels/` | Sheet, answer key, agreement.json |
| `runs/fix-and-rerun/` | Both runs, the delta, the chain |

Test suite: 104 passing, including a test that a labeller answering one verdict
every time earns high raw agreement and zero kappa, which is the failure mode
kappa exists to catch.
