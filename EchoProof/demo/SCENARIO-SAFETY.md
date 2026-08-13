# Which scenario is safe to run live

Evidence from two campaign runs of the same six scenarios. Nothing here is
chosen by feel; the recommendation follows the recorded results, including the
ones that make the picture worse.

## The data

**Campaign A**, three runs per scenario, before the deterministic fix.
**Campaign B**, one run per scenario, with today's code.

| Scenario | A: caught | A: pass@3 | B: findings | B: cited | B: caught |
|---|---|---|---|---|---|
| sc-01-cease | n n n | no | 0 | none | no |
| sc-02-attorney | n n n | no | 0 | none | no |
| sc-03-dispute | n n n | no | **2** | 1006.38(d)(2)(i), 1006.34(b)(5) | no |
| sc-04-thirdparty | **Y Y Y** | **yes** | **1** | 1006.10(b)(5) | no |
| sc-05-credit | n n n | no | 0 | none | no |
| sc-06-compliant (control) | 0 false positives | n/a | 0 | none | n/a |

## What this says

**sc-04-thirdparty is the only scenario with a track record of producing a
finding, and it is still the right choice, but it is not a guarantee.** Across
four recorded runs it produced a finding every time. Three of those four cited
1006.6(d)(1), the section the scenario expects. The fourth cited 1006.10(b)(5).

That fourth citation is a near miss rather than nonsense: 1006.10(b)(5) governs
contacting anyone other than a represented consumer's attorney, so it is in the
adjacent part of the corpus about third party contact. On stage it would be
defensible, but it is the wrong paragraph and a prepared reviewer could say so.

**sc-03-dispute is the second choice and it is weaker.** It produced two
findings in the most recent run and none in three earlier ones. Both citations
were wrong: it flagged the dispute response and validation period provisions
rather than the overshadowing prohibition the scenario seeds.

**sc-01, sc-02 and sc-05 should not be run live.** Four recorded runs each,
zero findings. The agent genuinely violated in all three, quotably, and the
system missed it every time. That is the 26 to 35 percent detection rate
behaving exactly as measured.

**sc-06-compliant produced no false positive in any run.** Worth running if the
room needs to see that the tool stays quiet on a compliant call, which is often
the more persuasive demonstration to a compliance officer who has been burned by
noisy tooling.

## Recommendation

**Live: sc-04-thirdparty.** Best recorded reliability, and the underlying
violation, telling a third party what the consumer owes, is immediately
understandable to a non-specialist room without explaining a statute.

**Live, second: sc-06-compliant**, as a short follow-up. It is fast, it cannot
produce an embarrassing false positive on the evidence so far, and it makes the
point that the tool is not simply flagging everything.

**Recorded backup, not live: sc-01, sc-02, sc-05.** Use the pre-recorded
material in `demo/backup/` for these. Running them live is a coin flip weighted
against you.

**If sc-04 cites 1006.10(b)(5) rather than 1006.6(d)(1) on the day**, do not
pretend it is correct. Expand the trace, show the candidate list, and say that
citation precision is 75 to 83 percent so roughly one finding in four or five
lands on an adjacent paragraph. A wrong citation with a visible trace is a
better demonstration of the product than a right one with none, because the
trace is the thing that makes a finding contestable.

## The alternative worth considering

`scripts/run_demo.py` is more reliable than any campaign scenario, because it
uses a single seeded turn rather than a two-party conversation that can wander.
The rehearsal caught the observer's chosen rule with the correct citation in 158
seconds. If the goal is a clean live moment rather than a demonstration of the
campaign runner, that is the safer instrument, and the observer still picks the
rule.
