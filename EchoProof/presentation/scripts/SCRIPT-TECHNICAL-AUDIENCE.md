# Technical audience, 15 minutes

For engineers, ML people and anyone who will ask how the evaluation was
constructed. Lead with the isolation boundary and the build order. Go deep on
methodology, including what is wrong with it.

Deck: [../demo-day/deck.html](../demo-day/deck.html), all 12 slides.

**Latency strategy.** Launch `Debt disclosed to a third party` at 1:30,
measured 224.3 seconds warm, return at 6:00. A 45 second margin. This audience
will let you talk about architecture for four minutes without fidgeting, so the
long conversation is affordable here and nowhere else.

| Clock | On screen | Say |
|---|---|---|
| 0:00 | Deck 1 | "The problem is not that models hallucinate. It is that a fluent, correct sounding, helpful sentence can be illegal, and nothing in a normal eval stack is shaped to catch that." |
| 0:30 | Deck 2 | "Real agent turn. It is not a wrong fact. Your accuracy benchmark scores it as a good response, and it violates 1006.6(d)(1)." |
| 1:00 | Browser, `/rig` | Click `03 DEBT DISCLOSED TO A THIRD PARTY` under `CONTRADICTED`. Title it. **Click `RUN ADJUDICATION →`** at 1:30. "Starting a real one. Eight claims, so roughly three and a half minutes, and I will explain the architecture while it runs." |
| 1:45 | Deck 3 | "OpenAI compatible proxy in front of the agent's model call. It returns the upstream response unmodified and never delays it, and a capture failure never becomes a request failure. Both are pinned by tests." |
| 2:15 | Deck 3, boundary | "Here is the decision everything else rests on. The judge receives one claim and the rule text retrieval selected. It never sees the corpus and it is prompted to rule from the supplied text alone. That is what makes a verdict falsifiable: the retrieved paragraph is stored in the span, so you can read what it was given and disagree." |
| 2:50 | Deck 3, gold path | "Money and dates short circuit ahead of retrieval. Canonical normalisation then comparison in code, with both sides recorded and `decided_by: deterministic` in the span. The model never compares two numbers." |
| 3:15 | Deck 3 | "One honest limit on that: it only fires where the scenario supplies a known true value, and most fixtures do not, so most numeric claims still reach the judge. The path is live and exercised, not universal." |
| 3:40 | Deck 7 | "Build order was a decision. Retrieval was built and measured before the judge was tuned. If you tune the judge first, you tune it against whatever retrieval hands it, you absorb the recall defects into the prompt, and then every retrieval improvement regresses the judge. The failure becomes unattributable." |
| 4:15 | Deck 7 | "The cost of that ordering, measured: the extractor writes the retrieval questions, and on 56 pairs, 41 percent introduced rule vocabulary absent from the claim. So part of retrieval performance is the model recognising Regulation F, and that part will not transfer to a client's private corpus. I would expect a real drop on first contact with a private rulebook." |
| 4:50 | Deck 4 | "Five states. Two decide, three abstain. Abstentions are counted separately everywhere, because folding a refusal into detection would inflate the headline." |
| 5:15 | Deck 4 | "Two are marked. `no_governing_rule` is unreachable: 71 retrieval calls, lowest top 1 was 0.5009 against a floor of 0.4937. The cross encoder's sigmoid does not approach zero for unrelated text, so a floor calibrated there cannot separate nothing governs this from something weakly resembles this. A conversation about clock towers in Bruges scored 0.50. Recalibrating is open work, and I did not do it because changing the floor invalidates comparison against every scored run." |
| 5:50 | Deck 4 | "`conflicting_sections` agreed with a human zero times out of three, and the human labeller never once selected it. No weight goes on that state." |
| 6:10 | Browser | "Finished." Open the assessment. |
| 6:25 | `/runs/{id}` | "Two contradicted, six abstained. The gate decision is computed on read from the criteria pack, never stored, so it cannot drift from the findings it summarises." |
| 6:50 | Case file `rf-06-thirdparty-t00-c02` | "Claim text is a character offset slice, not model output. Worth saying how that works, because the spec said tool calling returning offsets and that failed: models do not count characters, and it returned spans reading `overy` and `lance`. The extractor now returns a verbatim quote and offsets are computed in code by locating it. A quote that does not appear verbatim gets rejected, which is a stronger guarantee than a model supplied integer that cannot be validated at all." |
| 7:40 | Case file, step 04 | "Retrieval. Three queries under different legal theories, hybrid BM25 and dense, RRF fused, cross encoder reranked, `BAAI/bge-reranker-base`. Ten candidates offered, selected at 0.716, floor 0.4937, ceiling 0.548." |
| 8:20 | Case file, step 04 | "The thresholds are worth a note. Thresholds calibrated on retrieval pairs gave a ceiling of 0.740, which exceeds every score in a fixture run and would abstain on everything. The operating point of 0.548 is from the fixture sweep. Thresholds do not transfer between distributions." |
| 8:50 | Case file, step 08 | "Every span into an append only chain, verified on read." |
| 9:10 | Deck 6 | "Entry N's hash covers N minus one. Content addressed artifacts on disk; the metadata index holds run and finding records only, never evidence content, so you cannot quietly rewrite the record through the database." |
| 9:40 | Deck 9 | "Evaluation. This is the part I want to be hardest on." |
| 10:00 | Deck 9 | "Detection is a range, 0.261 to 0.348, because the same 77 item split scored twice gave both. Nothing changed between the runs that accounts for it: the only code difference touched one claim in 162. That is run to run model variance, measured elsewhere at roughly one fixture in six. A single figure would imply precision the measurement does not have." |
| 10:40 | Deck 9 | "Citation precision 0.750 to 0.833 at that operating point, false positive rate 0.020 and 0.060. Campaign pass at 3 is one of five graded scenarios, and I checked the misses by reading the agent turns out of the evidence log: they are real detection failures, not a compliant agent. The agent plainly continued after a cease request and plainly contacted a represented consumer." |
| 11:20 | Deck 9 | "Judge to human agreement 0.480 against a floor of 0.85, kappa 0.310. The kappa matters because it rules out the skewed distribution explanation. The two labellers genuinely disagree." |
| 11:50 | Deck 9 | "And the defect in that metric: the baseline is self graded. The project owner declined to label, so the instrument produced the baseline that validates the instrument. That is exactly the circularity the spec's human baseline exists to break. Mitigation was labelling from a sheet verified to contain no verdict, rationale, severity or score. One observation cuts against the worst reading: a labeller reproducing the judge scores high, and it scored 48 percent." |
| 12:30 | Deck 9 | "The held out split has five hard negatives, so its false positive rate can only take values 0.00, 0.20, 0.40. It cannot express the 2 percent threshold the bands are stated against. The development split was expanded to 50 hard negatives to fix that, but held out was already sealed and I did not touch it. At a matched ceiling, held out detection was 0.444 against development's 0.348, which suggests the single authored labels did not inflate development." |
| 13:10 | Deck 9 | "Three independent measurements point the same way. Triage layer routing to human review, not a release gate." |
| 13:30 | Deck 8 | "Throughput. 105 seconds median a turn, retrieval is 91 of it. Two or three queries per claim, fifty candidates reranked per query, CPU. The cache is 1256x on a hit and got a 12.6 percent hit rate in a real campaign, because agent replies diverge as context accumulates so the same scenario stops reissuing the same queries. Do not plan around warm cache timings. Production needs ONNX or GPU for the cross encoder." |
| 14:10 | Deck 11 | "One model interface throughout, OpenAI SDK against a compatible base URL, so Bedrock is a base URL and a model string. Whichever backend produced a scored run's numbers stays the backend for that run; no silent swap after fixtures are scored." |
| 14:40 | Deck 12 | "Every claim has a source, every verdict has a rule, every finding has evidence. The gap is detection." |
| 15:00 | | Stop. |

## Hard technical questions, short answers

**"Why not fine tune a classifier instead of retrieval plus a judge?"**
> "Because a classifier cannot cite. The product is not a label, it is a label
> with the governing paragraph attached, and a reviewer who can check it in five
> seconds. Also a client's corpus changes, and retrieval absorbs that without
> retraining."

**"Your retrieval questions come from the same model that extracted the claim. Is that not leakage?"**
> "It is, and I measured it: 41 percent of 56 pairs introduced rule vocabulary
> that was not in the claim. It is the single biggest threat to transfer onto a
> private corpus, and it is why I quote Reg F numbers as an upper bound rather
> than an expectation."

**"How do you know the judge is not just pattern matching Reg F from pretraining?"**
> "I do not, fully, and that is the point of the telecom pack. Same engine,
> synthetic corpus with invented identifiers it cannot have seen. Four of four
> contradicted cases cited correctly. That is a portability signal, not an
> accuracy one: 15 provisions in plain prose is a much easier retrieval problem
> than 303 in statutory language."

**"Five scenarios is not an evaluation."**
> "Agreed. Five graded scenarios is a smoke test with a pass rate attached, and
> 1 of 5 versus 2 of 5 is one scenario and twenty points. The 77 item fixture
> split is the real measurement, and even that is single authored."

**"What is the actual failure mode you are most worried about?"**
> "Compound obligations. A rule that requires two things in one sentence gets
> split into two claims, and each half is judged against the whole rule, so a
> compliant sentence gets failed twice. We observed it on the telecom standard's
> CC-5.1. It is structural: claims are the unit of adjudication and obligations
> are not always claim shaped. The fix is turn level evaluation for
> multi element obligations, and it is not built."
