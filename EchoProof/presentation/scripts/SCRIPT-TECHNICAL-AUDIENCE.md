# Fifteen minutes, technical audience

## Before you start

[open a terminal in the EchoProof folder]

[run .venv/Scripts/python scripts/run_ui.py]

[open http://127.0.0.1:8077/rig in tab one]

[under 02 / select conversation, group supported, click 04 validation notice contents described]

[type warm up in the assessment title box, click run adjudication, let it finish]

[open presentation/demo-day/deck.html in tab two, press f for fullscreen]

[open http://127.0.0.1:8077/bench in tab three and check the top card reads third party disclosure - demo baseline]

## Opening

[deck on slide one]

The interesting problem in regulated voice AI is not that models hallucinate. We know how to look for that.

The problem is that a fluent, correct, helpful sentence can be illegal, and nothing in a normal evaluation stack is shaped to catch that class of failure.

[click twice, the claim marks and the chain draw]

EchoProof is a pre-deployment compliance assurance layer built around that observation.

## The failure mode

[click to the next slide]

Real agent turn from a collections call.

[click, the provision appears on the paper card]

It violates 1006.6(d)(1). A debt collector may not communicate about a debt with any person other than the consumer, and the agent is talking to the consumer's brother.

[click, the mono line appears underneath]

Note what it is not. It is not a factual error, so a groundedness check passes it. It is not toxic, so a safety classifier passes it. It is not off policy in any way a rubric written by a product team would express.

It is illegal, and the only way to know that is to have the statute in the loop.

## The shape of the system

[click to the next slide]

[click four times, the four moves appear one at a time]

Four moves. Read the turn, and only agent turns are adjudicated. Locate claims as verbatim quotes. Retrieve the governing provision. Rule on it, and seal the record.

The rest of this is how each of those is made attributable when it fails.

## The pipeline

[click to the next slide]

[click, the six stages draw]

The adapter is an OpenAI compatible proxy. You point the agent's base URL at us and nothing else in the stack changes.

Claim extraction is worth a minute, because the obvious implementation does not work. The specification originally said tool calling that returns character offsets, and models do not count characters. It came back with spans reading five characters off, mid word.

So the extractor returns a verbatim quote, and the offsets are computed in code by locating that quote in the transcript. If the quote does not appear verbatim, the claim is rejected. That is a strictly stronger guarantee than a model supplied integer, because an integer cannot be validated and a quote can.

[click, the gold path drops out and rejoins]

The gold path is deterministic verification. Money and dates are canonicalised, then compared in code, ahead of retrieval. The model never compares two numbers, and the span records both sides of the comparison and marks the decision as decided in code.

Canonicalisation is doing real work there. Spoken numbers arrive as words rather than digits, because verbatim transcription is preferred, so thirty five dollars and thirty five cents and a written figure all have to normalise to the same value before anything is compared. Dates are worse, because relative phrases have to be anchored to the date of the call to mean anything.

The rule underneath it is simple. If arithmetic can settle it, arithmetic settles it, and the model is never asked a question that has a correct answer computable in code.

[click, the waveform appears and gets sliced]

And the turn travels as signal, cut at claim boundaries, because the claim is the unit of adjudication.

## The isolation boundary

[click to the next slide]

This is the load bearing decision.

[click, retrieval sweeps the corpus]

Retrieval is hybrid. BM25 and dense vectors over structure aware chunks, split on section boundaries with the parent heading kept attached to each chunk. The two result sets are fused by reciprocal rank fusion and then reranked by a cross encoder.

Chunking on section boundaries rather than by token window is not a detail. A provision is a legal unit, and half a provision is not a weaker version of the rule, it is a different rule. Keeping the parent heading attached matters for the same reason, because a subsection that reads as a bare list of exceptions is meaningless without the prohibition it modifies.

The other thing worth naming is that a claim gets several queries rather than one, written under genuinely different legal theories. A single sentence can engage unrelated provisions at once, and a single query written from the surface wording of the claim tends to find only the most obvious of them.

[click, one provision and one claim lift out]

That process hands forward exactly one provision, alongside one claim.

[click, the fence and the judge draw]

The judge receives those two things and is prompted to rule from the supplied text alone.

[click, the blocked arrows appear]

It never sees the corpus. It is not permitted to fall back on the regulation it may or may not have memorised in pretraining.

Two reasons, and the second is the one engineers care about. The first is trust: the rule text the judge was handed is stored in the span, so a verdict is falsifiable by reading it.

The second is attribution. If the judge could reach past that fence, a wrong verdict would be unattributable. You could never tell whether retrieval surfaced the wrong provision or the judge misread the right one. Fencing it means every failure lands in exactly one component.

That is also why the build order was what it was. Retrieval was built and measured before the judge was tuned, because if you tune the judge first, you tune it against whatever retrieval happens to hand it, you absorb its weaknesses into the prompt, and then every subsequent retrieval improvement regresses the judge.

It is worth being concrete about how that goes wrong, because it is a trap that looks like progress. You start with a judge that is underperforming. You add prompt language compensating for the fact that the right provision often is not in the shortlist, telling it to reason around gaps. It gets better. Then somebody improves retrieval, the right provision starts arriving, and the compensating language now actively hurts, because the judge has been instructed to distrust its inputs.

At that point you cannot separate the two components even in principle. Building them in the other order costs more up front and it is the only version where a failure has an address.

## The five verdict states

[click to the next slide]

[click twice, supported and contradicted appear]

Five states, never a boolean. Two decide.

[click, the three abstentions appear]

Three decline, and the three are genuinely different failures rather than one abstention with three labels.

No governing rule means nothing in the corpus was a plausible match at all. Retrieval below confidence means something plausible surfaced, but not with enough confidence to adjudicate on it. Conflicting sections means two candidates were plausible and pointed different ways.

Keeping the first two separate matters a lot. Collapsing them turns a retrieval bug into a positive claim that no rule exists, which is a much worse thing to put in front of a compliance officer.

[click, the routing appears]

All three route to human review and are counted apart from findings.

[click, the closing line appears]

A system that forces a verdict to avoid an abstention is optimising its own scoreboard.

## Evidence

[click to the next slide]

[click, the intact chain draws]

Append only, hash chained. Each entry's hash covers the previous entry's hash. Spans for the session, the turn, extraction, deterministic checks, retrieval with candidates and scores, the judge call with the rule text that went in, and the finding.

Every finding pins the policy pack version, the document hash, the model version, the prompt hash, the retriever config and the seed. Which gives you reproducibility as a property rather than an aspiration: the same stored inputs regenerate the same verdict, and you verify that by recomputing the hash.

[click, the middle entry is edited and the links break]

Edit an entry in the middle and every hash after it stops matching.

[click, the content addressing line appears]

Artifacts are content addressed on disk. The index holds records and never evidence content, so there is no path to rewriting evidence through the database.

That split is deliberate and it is the part I would defend hardest in a design review. The moment evidence content lives in a mutable store, the chain is decorative, because anyone with database access can rewrite the thing the hashes are supposed to protect and then recompute them.

Keeping the index to pointers means the worst an attacker with database access can do is lose the reference, which is loud, rather than change the content, which is silent.

## Audio

[click to the next slide]

[click, the transcript bar appears]

[click, the word ticks appear]

Deepgram Nova-3 gives word level timestamps. The extractor gives character offsets. Those map deterministically onto each other.

[click, the clip bracket draws]

The resulting span slices the source audio with ffmpeg, so a finding carries the flagged sentence rather than the whole call.

[click, the ordering line appears]

And the ordering is deliberate. Adjudication is text only. Audio bolts on after the verdict exists, so it is never an input to a decision, only evidence for one.

## The stack

[click to the next slide]

[click, the first stack draws]

A cascaded voice agent. Telephony, speech to text, orchestrator, model, text to speech.

[click, echoproof appears in the chain]

We attach at one point, in front of the model call.

[click, the return path and the adjudication branch appear]

The upstream response is returned unmodified and never delayed. Adjudication runs on a worker off the hot path, after the response has already gone back.

Two invariants hold that up and both are pinned by tests: the proxy never modifies the upstream response, and a capture failure never becomes a request failure.

[click, the second stack appears]

Swap every vendor. The attachment point does not move.

## Verticals and the packs

[click to the next slide]

[click, the four cartridges seat into the core]

The engine holds no field, constant or branch that knows its industry. Four client data packs: policy, scenario, persona, criteria.

The criteria pack is the one people underestimate. It holds the thresholds that produce the gate decision, which is computed on read rather than stored. So what blocks a deployment is the client's policy expressed as configuration, rather than our judgement hardcoded.

[click, the policy cartridge swaps]

Swapping the policy pack to a telecom standard with a different identifier convention required no engine change. It did surface two places where engine code had assumed one regulation's identifier format, and those were real boundary defects that only a differently numbered corpus could have exposed.

[click, the industries appear]

## Today and production

[click to the next slide]

[click, the today column appears]

Everything I am about to show runs on this laptop.

[click, the production column appears]

One model interface, the OpenAI SDK against a compatible base URL, so Bedrock is a base URL and a model string. Retrieval to OpenSearch. Cross encoder to GPU, which is the single biggest throughput lever. Artifacts to S3 with object lock. Adjudication to a horizontally scaled worker pool, which scales linearly because turns are independent.

[click, the configuration line appears]

There is also a discipline rule around that swap. Whichever backend produced a scored run's numbers stays the backend for that run, so nothing gets silently swapped underneath a measurement.

## The walkthrough

[alt tab to the browser, tab three, the bench]

[click the top card, third party disclosure - demo baseline]

[point at gate decision at the top]

Gate decision, computed on read from the criteria pack rather than stored, so it cannot drift from the findings it summarises.

[point at the abstentions section]

Abstentions listed separately from findings, always.

[scroll to findings and click the first one]

[point at what was said]

The claim as an offset slice of the recorded transcript.

[point at the cream coloured card]

The provision it was judged against, verbatim.

[scroll down to the evidence trace]

[point at the retrieval step]

And this is the part worth looking at. Three retrieval queries under different legal theories, because one sentence can engage several unrelated rules. Every candidate the judge was offered, and the one it selected.

[point at the proof block]

The proof block pins the model, the prompt hash, the retriever configuration and the thresholds that were in force. That is what makes the run reproducible rather than merely recorded.

## Fix and re-run

[alt tab back to the deck]

[click to the next slide]

[click twice, the before panel and the arrow appear]

Same scenario, same seed, same policy pack, same judge, same thresholds. Only the agent changed.

[click, the after panel appears]

The finding closed and nothing new opened.

[click, the closing lines appear]

Both conditions are required. And findings are keyed by section and verdict, never by claim id, because claim ids are regenerated every run and keying on them would report every finding as simultaneously closed and new.

## Close

[click to the next slide]

[click three times, the lines and the ask appear]

Every claim has a source. Every verdict has a rule. Every finding has evidence.

[stop clicking and look at the room]

What I want is an introduction to somebody who signs off that a voice agent can go live.

## If something goes wrong

### The bench will not load

[check the terminal is still running run_ui.py]

[reload the page]

If it does not recover, return to the deck and continue from fix and re-run.

That is running live and I am not going to debug it in front of you. Everything I described is on disk and I will show anyone who wants to see it afterwards.

## Questions you will get

### "Your retrieval queries are generated by the same model that extracted the claim. Is that not leakage?"

It is, and it is the thing I would attack first. The extractor writes the retrieval questions, and a meaningful share of them introduce rule vocabulary that was not present in the claim.

Which means part of retrieval performance is the model recognising a well known federal regulation, and that part will not transfer to a client's private corpus. It is the main reason I treat results on a public regulation as an upper bound rather than an expectation.

### "Why a cross encoder rather than just dense retrieval with a bigger model?"

Because the discrimination we need is between provisions that are lexically almost identical. Statutory text repeats itself heavily, and a bi encoder collapses that distinction into one vector.

The cross encoder sees the claim and the candidate together, which is what lets it separate two subsections that differ by one clause. It costs an enormous amount of compute per query, which is precisely the thing a GPU fixes.

### "How do you stop prompt injection through the transcript?"

Architecturally rather than by filtering. The judge receives the claim as data inside a structured call, and its system prompt constrains it to the retrieved rule text. An injected instruction in the transcript becomes another claim to adjudicate rather than an instruction to follow.

I have tested it, and it did not flip a verdict. One test is not a security guarantee and I would want an actual corpus of attacks before claiming anything.

### "What breaks first at scale?"

The cross encoder. Every claim fires several queries and each query reranks a large candidate set, all on CPU today. That is the wall, and it is a hardware fix rather than a research problem.

Everything else scales trivially because turns are independent, so the worker pool is embarrassingly parallel.

### "What is the deepest unsolved problem?"

Compound obligations. A provision that requires two things in one sentence gets split into two claims by extraction, and each half is then judged against the whole rule, so compliant text can be marked as violating twice.

That is structural. Claims are the unit of adjudication and obligations are not always claim shaped. Fixing it means evaluating multi element obligations at turn level, and it is not built.

### "Why not LangGraph or a framework from the start?"

Because a sequential runner made every stage's failure legible while I was still deciding what the stages were. The orchestration swap is the cheapest one on the list, and doing it early would have bought complexity before I knew the shape of the pipeline.
