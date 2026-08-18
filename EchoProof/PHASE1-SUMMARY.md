# EchoProof - Phase 1 Summary

Wire retrieval into the judge, score the fixtures. SPEC sections 5, 6, 11.
Development split only. The held-out split remains sealed and unscored.

## 1. Headline result

Two scoring runs. The second followed three fixes made in response to the first.

| Measure | Run 1 | Run 2 |
|---|---|---|
| Operating point at FP <= 2% on hard negatives | **none exists** | ceiling 0.548 |
| Detection at that point | n/a | **0.348** |
| False positive rate there | n/a | 0.020 |
| Citation precision there | n/a | **0.750** |
| FP at maximum detection (ceiling 0.494) | 0.240 | **0.100** |
| Detection at ceiling 0.494 | 0.810 | 0.696 |

Run 1 had no usable operating point at all: every ceiling that reached 2% false
positives also reached zero detection. Run 2 has one. The false positive rate at
matched settings more than halved, from 0.240 to 0.100.

**SPEC section 11 band: below 70 percent. Reconsider the corpus, or restructure
the claim level approach.**

Detection of 0.348 at a 2% false positive rate is not a release gate. The honest
positioning is the one the band prescribes and ARCHITECTURE.md decision 12 requires
stating: EchoProof is a triage layer that routes to human review. The
Deployment Readiness Report must say so on its front page rather than in a
footnote.

What is genuinely working is the part that is hardest to fake. Citation
precision at the operating point is 0.750, meaning three quarters of emitted
findings cite the correct governing paragraph, and every finding carries the
retrieved rule text so a reviewer can check it in seconds.

## 2. Cost and throughput

| Measure | Value |
|---|---|
| Cost, 77 turns | $0.72 |
| Projected per 100 call campaign | **$23.49** |
| Wall clock, 77 turns | over one hour |
| Evidence spans written | 394, chain verifies |

Cost is comfortably inside the $100 to $300 estimate. Throughput is not.

**Throughput is a Phase 4 blocker and the cause is known.** Six scenarios at
three runs of roughly 25 turns is about 450 turns, which is several hours at
this rate. Two decisions taken during this phase caused it: multi-theory
retrieval triples reranking work per claim, and shortlist selection enlarges
every judge call. The fix is one of ONNX or GPU execution for the cross encoder,
caching retrieval by claim text, or reducing questions per claim. Recorded here
rather than fixed, because changing it now would land a change on top of an
in-flight measurement.

The brief's proxy overhead budget of 50ms is unaffected. This is throughput, not
latency, and the judge runs out of band by design.

## 3. What the three fixes were, and what each achieved

**Ground truth corrections.** Two of the twelve false positives in run 1 were
the system catching errors in labels this project had authored. 1006.100(b)
requires call recordings retained for three years after the date of the call,
not after the last activity on the account. 1006.34(b)(5) starts the validation
period when the collector provides the information, not when the consumer
receives it. Both fixtures were relabelled from compliant to violating, and two
correct counterparts were added so the false positive denominator stayed at 50.

**Exception blindness in the judge.** Run 1 flagged a permitted final contact
against the prohibition in 1006.6(c)(1) while ignoring 1006.6(c)(2)(i), which
expressly allows it. The judge prompt now requires checking the shortlist for an
exception, exclusion, safe harbour or narrowing definition before ruling any
prohibition contradicted. Verified fixed: that fixture now returns supported
against the exception itself.

**Deterministic path wiring.** Covered in section 5, because the outcome is
partial and the remaining gap matters.

## 4. Diagnostics

| Diagnostic | Value | Note |
|---|---|---|
| Citation precision at the operating point | 0.750 | A violation counts as correctly cited when any firing claim cites the governing paragraph |
| Abstain rate at the operating point | 0.599 | High, and by design under decision 6 |
| False positives on easy negatives | 0 at the operating point | Greetings and backchannels do not produce findings |
| Claim recall by type | **not measured** | See section 5 |
| Reproducibility | chain verifies on write and reload | Model-level determinism not separately established |

Claim type distribution across 147 extracted claims: policy_statement 72,
implicit 28, commitment 24, date 14, numeric 9.

## 5. Limitations, stated rather than buried

**Deterministic verification is only half wired.** Numeric and date claims are
now canonicalised in code and every one emits a check.deterministic span, which
run 1 did not do at all. But `decided_by` is still model for all 147 claims: the
comparison against an expected value never runs, because no expected value is
plumbed per claim. ARCHITECTURE.md decision 3 says money and dates are verified
deterministically in code. Normalisation happens in code. Comparison does not
yet. That is a real gap and it is not closed.

Of 23 deterministic claims, only 4 parsed to a value. The rest are spans like
"ninth call" and "in the last five days", which are numeric and date claims in
type but not bare values. Normalisation operates on values, so the parse rate is
a property of what the extractor selects, not a defect in the parser.

**Ground truth is single authored.** Every fixture and every label in this phase
was written by the same agent that wrote the judge. Measured on the retrieval
pairs, that authorship advantage was worth roughly +0.31 precision@1: pairs
written while reading the corpus scored 0.741, model-generated questions over
the same corpus scored 0.429. The held-out split is the only control and it is
sealed until Phase 4.

**Retrieval is no longer model independent.** The extractor generates the
retrieval questions. Measured on 56 pairs, 41% of generated questions introduced
rule vocabulary absent from the claim, some of it benign normalisation such as
lawyer to attorney, some of it substantive inference. Part of retrieval
performance is therefore the model recognising Regulation F, and that part will
not transfer to a client's private corpus.

**The calibrated ceiling does not transfer.** Thresholds calibrated on retrieval
pairs produce a ceiling of 0.740, which exceeds the highest score observed in
either fixture run. At shipped settings the system emits zero findings. The
operating point of 0.548 comes from the fixture sweep, not from pair
calibration, and thresholds must be recalibrated on the distribution they will
actually see.

**Required utterance detection is presence only**, per SPEC section 6. Semantic
equivalence, placement, completeness and intelligibility are designed and
deferred.

**Deviation from SPEC section 11 on set size.** The spec calls for 50 items. The
development split holds 77. A 50 item set cannot express its own decision bands:
with 10 hard negatives the false positive rate can only take values 0.0, 0.1,
0.2 and so on, so a 2% threshold is unmeasurable. Hard negatives were expanded
to 50 so that one false positive costs exactly 0.020.

**Deviation from ARCHITECTURE.md decision 4 on claim offsets.** The decision specifies
tool calling that returns character offsets. Implemented literally, the model
returned spans reading 'overy' and 'lance' on a 184 character turn; models do
not count characters. The extractor now returns a verbatim quote and the offsets
are computed in code by locating it. The stored claim is still an offset and
still never a paraphrase, and the guarantee is stronger, because a quote that
fails to appear verbatim is detected and rejected while a model-supplied integer
cannot be validated at all.

## 6. Artifacts

| Path | Contents |
|---|---|
| `runs/fixtures-dev/` | Run 1 evidence chain and per-claim scores |
| `runs/fixtures-dev-v2/` | Run 2, the results reported here |
| `packs/policy/reg_f/` | 303 paragraph records, manifest with corpus hash |
| `packs/criteria/` | Severity map, gate thresholds, abstain routing, calibrated thresholds |
| `fixtures/fixtures.jsonl` | 77 development items |
| `fixtures/heldout.jsonl` | 15 sealed items, unscored |

Both run directories are retained. Phase 0's build history check means a later
phase should read these rather than re-run them.
