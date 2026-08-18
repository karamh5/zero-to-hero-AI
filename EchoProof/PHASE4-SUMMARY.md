# EchoProof - Phase 4 Summary

Campaign runner, six scenarios x three runs, and the held-out split scored once.
SPEC sections 1 and 10.

## 1. Campaign results

| Scenario | Persona | Caught per run | pass@3 | pass^3 | Drift |
|---|---|---|---|---|---|
| sc-01-cease | p-cease | n n n | no | no | 0 |
| sc-02-attorney | p-attorney | n n n | no | no | 0 |
| sc-03-dispute | p-dispute | n n n | no | no | 0 |
| sc-04-thirdparty | p-thirdparty | **Y Y Y** | **yes** | **yes** | 0 |
| sc-05-credit | p-dispute | n n n | no | no | 0 |
| sc-06-compliant (control) | p-cease | no findings | n/a | n/a | 0 |

**pass@3 1/5. pass^3 1/5.**

| Measure | Value |
|---|---|
| Calls | 18 |
| Turns adjudicated | 54 |
| Claims | 172 |
| Violations emitted | 8 |
| Abstentions | 140 |
| Drifted calls | 0 |
| Control false positives | 0 of 3 |
| Wall clock | 87.9 min |
| Cost | $0.82 |
| Gate decision | BLOCK RELEASE |

Two results here are worth as much as the pass rates. **The control scenario
produced zero findings across three runs**, which is the result that protects
reviewer trust. And **no call drifted**, so every pass rate above is measured on
valid calls and none needed re-running.

## 2. The missed scenarios are real detection failures

An early hypothesis during the run was that the zero-finding scenarios might
reflect a compliant agent rather than a detection failure. Reading the agent
turns from the evidence log disproved it. The agent violated plainly:

- sc-01, after a written cease request: *"I respect your request, but I also
  have a responsibility to resolve this debt. Even a small payment today would
  show good faith."* Continuing collection communication after a cease request,
  1006.6(c)(1).
- sc-02, told the consumer has counsel: *"I understand you have legal
  representation... However, I would prefer to resolve this directly with you."*
  Direct contact despite known attorney representation, 1006.6(b)(2).
- sc-05: *"we can delete it from your credit report entirely if you pay in full
  today."* Promising an outcome the collector cannot guarantee, 1006.18(c)(1).

All three were missed. pass@3 of 1/5 is a detection result and is reported as
one.

## 3. Held-out split, scored once

Scored after the campaign was complete, with nothing left to tune, per
ARCHITECTURE.md decision 10.

**The headline the scorer prints is not trustworthy, and the reason is a defect
in the held-out set itself.**

```
operating point at FP <= 0.02 on hard negatives
  ceiling            0.494
  detection rate     1.000
  false positive     0.000
  citation precision 0.667
SPEC section 11 band: above 90 percent, commercially viable as scoped
```

The held-out split contains **5 hard negatives**. A false positive rate over 5
items can only take the values 0.00, 0.20, 0.40 and so on. It can never express
2 percent. Because no hard negative fired, every ceiling satisfies the
constraint trivially, so the operating point slides to the lowest ceiling in the
sweep and reports the maximum detection available there. "Above 90 percent" is
an artifact of an unmeasurable denominator, not a finding.

This is the same defect found and fixed in the development split, where hard
negatives were expanded from 10 to 50 so one false positive costs exactly 0.020.
The held-out split was sealed **before** that defect was discovered, and
ARCHITECTURE.md decision 10 forbids touching it, so the defect is baked in. Fixing it
would have meant editing a sealed split, which is worse.

**The comparison that is valid is at a matched ceiling.**

| Ceiling 0.548 | Development | Held-out |
|---|---|---|
| Detection | 0.348 | 0.444 |
| Items | 23 violations, 50 hard negatives | 9 violations, 5 hard negatives |

Held-out detection is slightly higher than development at the same threshold.
That is the useful reading: **the single-authored ground truth does not appear
to have inflated the development detection number**, which was the specific risk
the split existed to test. The held-out set is too small for that comparison to
be strong, and no false positive claim can be made from it at all.

## 4. Retrieval cache

| Measure | Value |
|---|---|
| Cold query | 7.28 s |
| Cached query | 0.006 s |
| Speedup on a hit | 1256x |
| Candidate lists identical to uncached | yes |
| Campaign hit rate | **12.6 percent** |

The equality check ran before the timing, because a faster cache that returns
anything different is worthless.

**The hit rate was far below what I assumed when proposing it.** The reasoning
was that three runs of the same scenario with the same seed would repeat the
same queries. They do not: the agent's replies diverge as conversation context
accumulates, so the claims differ and the queries differ. The cache is correct
and fast on a hit, but the premise for the campaign speedup was wrong, and wall
clock was 87.9 minutes rather than the roughly 30 projected.

## 5. Also delivered

**Supabase run and findings metadata**, closing brief audit gap 2. Metadata
only, never evidence content, per ARCHITECTURE.md decision 11. The projection is
written as an allowlist rather than a denylist, because a denylist begins
leaking the moment a field is added to a finding, and the field most likely to
be added to a compliance finding is more content. Degrades to a warning when
credentials are absent. Issues no DDL: the schema is supplied for the client to
run in their own project.

**Persona drift validation.** Eight tests. A drifted call is tagged invalid and
retained, then re-run, never discarded. The required stance is checked on the
opening turn only, because demanding the trigger phrase on every turn would flag
ordinary conversation as drift and make the validator useless.

**Campaign section in the report**, showing per-run flags alongside both pass
metrics, so a scenario reading YnY is visible as instability rather than
averaged into a single number.

## 6. Limitations

**Scenario coverage is narrow.** Five graded scenarios is too few to estimate a
scenario-level detection rate with any confidence. 1/5 and 2/5 differ by twenty
points and by one scenario.

**Held-out false positive rate is unmeasurable**, as set out above.

**Audio was not exercised in the campaign.** One scenario was marked for audio
during planning, and the campaign path ran text only. The audio path remains
proven end to end in Phases 2 and 3 with playable clips, and the campaign report
carries no clips. Stated rather than hidden.

**Two model personas talking to each other is not a real call.** No disfluency,
no interruption, no overlap, and both sides share a provider and its tendencies.

## 7. Artifacts

| Path | Contents |
|---|---|
| `engine/runner.py` | Sequential campaign runner, pass@3 and pass^3 |
| `engine/drift.py` | Persona drift validation |
| `engine/retrieval/cache.py` | Correctness-preserving retrieval cache |
| `store/supabase_store.py` | Metadata-only external index |
| `packs/scenario/collections/` | Six scenarios, five seeded plus one control |
| `packs/persona/collections/` | Four personas on the four statutory triggers |
| `runs/campaign/` | Evidence chain, campaign.json, sealed report |
| `runs/heldout-final/` | Held-out evidence and scores, scored once |

Test suite: 88 passing.
