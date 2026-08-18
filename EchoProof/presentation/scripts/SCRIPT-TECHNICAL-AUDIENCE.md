# Technical audience, 15 minutes

Uses the demo deck, all 16 slides. Full vocabulary. Lead with the isolation
boundary and the build order argument.

## Before you start

[run .venv/Scripts/python scripts/run_ui.py]

[open http://127.0.0.1:8077/rig in tab one]

[under 02 / select conversation, group supported, click 04 validation notice contents described]

[type warm up in the assessment title box, click run adjudication, let it finish]

[open presentation/demo-day/deck.html in tab two, press f for fullscreen]

[open http://127.0.0.1:8077/bench in tab three, check the top card reads third party disclosure - demo baseline]

## Opening

[slide 1: click 2x]

I worked in compliance before I built this, and the useful thing that gave me is a precise idea of what the artifact has to be. Not a score. A citation and a record.

The interesting technical problem in regulated voice AI is not that models hallucinate. We know how to look for that. It is that a fluent, correct, helpful sentence can be illegal, and nothing in a normal evaluation stack is shaped to catch that class of failure.

## The bottleneck

[slide 2: click 1x]

[click 3x]

The model is ready, the integration is ready, and the launch sits waiting on a signature nobody can evidence. The constraint is proof.

## What the current instrument is

[slide 3: click 1x]

[click 3x]

Manual review at one to five percent coverage, bounded by an analyst getting through ten to fifteen interactions a day. It is a sampling instrument with a hard ceiling, and no amount of headcount changes the shape of it.

## The shape of the system

[slide 4: click 1x]

[click 4x]

Four moves. Read the turn, agent turns only. Locate claims as verbatim quotes. Retrieve the governing provision. Decide, and seal.

The rest of this is how each of those is made attributable when it fails.

## The pipeline

[slide 5: click 1x]

[click 1x]

The adapter is an OpenAI compatible proxy. You point the agent's base URL at us.

Claim extraction is worth a minute, because the obvious implementation does not work. The spec originally said tool calling returning character offsets, and models do not count characters. It came back with spans five characters off, mid word.

So the extractor returns a verbatim quote and the offsets are computed in code by locating that quote. If the quote does not appear verbatim, the claim is rejected. That is strictly stronger than a model supplied integer, because an integer cannot be validated and a quote can.

[click 1x]

The gold path is deterministic verification. Money and dates are canonicalised then compared in code, ahead of retrieval. The model never compares two numbers, and the span records both sides and marks the decision as decided in code.

Canonicalisation is doing real work there. Spoken numbers arrive as words because verbatim transcription is preferred, and relative dates have to be anchored to the call date to mean anything.

[click 1x]

And the turn travels as signal, cut at claim boundaries, because the claim is the unit of adjudication.

## The isolation boundary

[slide 6: click 1x]

[click 1x]

Retrieval is hybrid. BM25 and dense vectors over structure aware chunks, split on section boundaries with the parent heading kept attached, fused by reciprocal rank fusion, then reranked by a cross encoder.

Chunking on section boundaries is not a detail. A provision is a legal unit, and half a provision is not a weaker version of the rule, it is a different rule.

[click 1x]

That hands forward exactly one provision, alongside one claim.

[click 1x]

The judge receives those two things and is prompted to rule from the supplied text alone.

[click 1x]

It never sees the corpus, and it is not permitted to fall back on the regulation it may have memorised in pretraining.

Two reasons, and the second is the one engineers care about. First, the rule text is stored in the span, so a verdict is falsifiable by reading it. Second, attribution. If the judge could reach past the fence, a wrong verdict would be unattributable, and you could never tell whether retrieval surfaced the wrong provision or the judge misread the right one.

That is also why the build order was what it was. Retrieval was built and measured before the judge was tuned, because if you tune the judge first you tune it against whatever retrieval hands it, you absorb its weaknesses into the prompt, and then every subsequent retrieval improvement regresses the judge. At that point the two components cannot be separated even in principle.

## The five states

[slide 7: click 1x]

[click 2x]

Five states, never a boolean. Two decide.

[click 1x]

Three decline, and they are genuinely different failures rather than one abstention with three labels. Nothing plausible surfaced at all. Something surfaced but not confidently enough. Two candidates were plausible and pointed different ways.

Keeping the first two separate matters, because collapsing them turns a retrieval bug into a positive claim that no rule exists, which is a much worse thing to put in front of a compliance officer.

[click 1x]

All three route to human review and are counted apart from findings.

A system that forces a verdict to avoid an abstention is optimising its own scoreboard.

## Evidence

[slide 8: click 1x]

[click 1x]

Append only, hash chained. Each entry hash covers the previous. Spans for the session, the turn, extraction, deterministic checks, retrieval with candidates and scores, the judge call with the rule text that went in, and the finding.

Every finding pins the policy pack version, the document hash, the model version, the prompt hash, the retriever config and the seed. Which gives reproducibility as a property rather than an aspiration: the same stored inputs regenerate the same verdict, verified by recomputing the hash.

[click 1x]

Edit an entry in the middle and every hash after it stops matching.

[click 1x]

Artifacts are content addressed on disk and the index holds records, never evidence content. That split is the part I would defend hardest in a design review, because the moment evidence lives in a mutable store the chain is decorative.

And this is the traceability argument. Published training lineage on open weights models gives you traceability of the model. This gives you traceability of the decision, and a regulator asks the second question far more often than the first.

## Audio

[slide 9: click 1x]

[click 3x]

Deepgram Nova-3 gives word level timestamps, the extractor gives character offsets, and those map deterministically onto each other. The resulting span slices the source audio with ffmpeg, so a finding carries the flagged sentence rather than the whole call.

The ordering is deliberate. Adjudication is text only. Audio bolts on after the verdict exists, so it is never an input to a decision, only evidence for one.

## The stack

[slide 10: click 1x]

[click 2x]

Three layers. Top is the customer cascaded voice agent, telephony, Deepgram for speech to text, an orchestrator, text to speech. Middle is us, one OpenAI compatible endpoint in front of the model call. Bottom is our engine: the OpenAI SDK model interface with Mistral today and Bedrock at volume, FAISS and BM25 behind a retriever interface, the cross encoder, and the hash chained log.

[click 1x]

The upstream response is returned unmodified and never delayed. Adjudication runs on a worker off the hot path. Two invariants hold that up and both are pinned by tests: the proxy never modifies the upstream response, and a capture failure never becomes a request failure.

[click 1x]

Swap every vendor and the attachment point does not move.

## Where it sits

[slide 11: click 1x]

[click 4x]

Practically, it sits between the agent build and the client sign off, and the output is a deployment readiness report rather than a dashboard. The engine holds no field, constant or branch that knows its industry. Everything client specific is a data pack: policy, scenario, persona, criteria.

The criteria pack is the one people underestimate. It holds the thresholds that produce the gate decision, computed on read rather than stored, so what blocks a deployment is the client's policy expressed as configuration.

## Go to market and market

[slide 12: click 1x]

[click 4x]

Three routes: attach to existing engagements, audit agents built by others, and recur when regulations change.

[slide 13: click 1x]

[click 2x]

The market is around three and a half billion this year heading to thirty five billion by 2033, and our measured run cost was eighty two cents of model spend for eighteen calls. Model spend is not the constraint, reranker compute is.

## The landscape

[slide 14: click 1x]

[click 2x]

Two axes. Conversation intelligence sits after the call, scoring against rubrics.

[click 1x]

OpenAI Presence is the closest, launched in July, with evals and graders built in. But it is end to end, so the grader and the agent come from the same vendor, and it does not cover cascaded stacks.

[click 1x]

Which leaves independent and pre deployment empty.

On scale: everything runs on this laptop today. The same model interface points at Bedrock by changing a base URL, retrieval moves to OpenSearch, and the cross encoder moves to GPU, which is the single biggest throughput lever. Adjudication runs as a horizontally scaled worker pool that scales linearly, because turns are independent.

There is a discipline rule around that swap. Whichever backend produced a scored run's numbers stays the backend for that run, so nothing gets silently swapped underneath a measurement.

## How it got here

[slide 15: click 1x]

[click 2x]

Two conversations changed the build. An applied engineer at Deepgram made the point that approximate timings are not evidence, which is why the offset to timestamp mapping is deterministic rather than nearest match. And Roger on the Hexaware CX side made the point that a finding a reviewer cannot act on is noise, which is why the gate is client configured and the case file is built around rule text rather than a score.

## The walkthrough

[alt tab to the browser, tab three, the bench]

[click the top card, third party disclosure - demo baseline]

[point at the gate decision block at the top]

Gate decision, computed on read from the criteria pack rather than stored, so it cannot drift from the findings underneath it.

[point at the abstentions section]

Abstentions listed apart from findings, always.

[scroll to findings and click the first finding]

[point at what was said]

The claim as an offset slice of the recorded transcript.

[point at the cream coloured card]

The provision it was judged against, verbatim.

[scroll down to the evidence trace]

[point at the retrieval step]

Three retrieval queries under different legal theories, because one sentence can engage several unrelated provisions. Every candidate the judge was offered, and the one it selected.

[point at the last step, evidence seal]

And the proof block pins the model, the prompt hash, the retriever configuration and the thresholds in force. That is what makes the run reproducible rather than merely recorded.

[click corpus in the top nav]

The corpus view gives per run retrieval coverage, which is the honest way to see what was never reached.

[click delta in the top nav]

And fix and re run. Same scenario, same seed, same policy pack, only the agent changed. Findings are keyed by section and verdict, never by claim id, because claim ids regenerate every run and keying on them would report every finding as simultaneously closed and new.

## Close

[alt tab back to the deck]

[press 1 6 and enter]

[click 2x]

Every claim has a source. Every verdict has a rule. Every finding has evidence.

The ask is an engagement to point it at, and an introduction to whoever signs off that an agent can go live.

## If something goes wrong

### The bench will not load

[check the terminal is still running run_ui.py]

[reload the page]

If it does not recover, return to the deck and close from there.

## Questions you will get

### "Your retrieval queries come from the same model that extracted the claim. Is that not leakage?"

It is, and it is the thing I would attack first. A meaningful share of generated questions introduce rule vocabulary that was not in the claim, which means part of retrieval performance is the model recognising a well known federal regulation. That part will not transfer to a private corpus, and it is why I treat results on a public regulation as an upper bound.

### "Why a cross encoder rather than a bigger dense model?"

Because the discrimination needed is between provisions that are lexically almost identical. Statutory text repeats itself heavily and a bi encoder collapses that into one vector. The cross encoder sees the claim and candidate together, which is what separates two subsections differing by one clause. It costs a lot of compute per query, which is precisely what a GPU fixes.

### "How do you stop prompt injection through the transcript?"

Architecturally rather than by filtering. The judge receives the claim as data in a structured call and its system prompt constrains it to the retrieved rule text, so an injected instruction becomes another claim to adjudicate rather than an instruction to follow. I have tested it and it did not flip a verdict. One test is not a guarantee.

### "Could this run on open weights models?"

Yes, and it is a genuinely interesting direction. One OpenAI compatible endpoint means any model behind a compatible endpoint works, including open weights running inside a client environment, which matters for anyone who cannot send transcripts to a third party.

It also rhymes with the traceability argument. The reason people care about published training lineage is being able to say where an answer came from. That is the same argument one layer up: model lineage tells you where the weights came from, the evidence chain tells you where the decision came from.

### "What breaks first at scale?"

The cross encoder. Every claim fires several queries and each reranks a large candidate set on CPU today. That is the wall, and it is a hardware fix. Everything else is embarrassingly parallel because turns are independent.

### "What is the deepest unsolved problem?"

Compound obligations. A provision requiring two things in one sentence gets split into two claims by extraction, and each half is judged against the whole rule, so compliant text can be marked as violating twice. That is structural: claims are the unit of adjudication and obligations are not always claim shaped. The fix is turn level evaluation for multi element obligations, and it is not built.
