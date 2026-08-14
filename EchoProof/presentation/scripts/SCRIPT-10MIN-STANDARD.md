# Ten minutes, general audience

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

Enterprises are putting voice AI agents into conversations that are governed by law. Collections, insurance, healthcare, telecom.

The agent is fluent, it is confident, and it has no idea which of its sentences are legal.

[click twice, the claim marks and the chain draw]

EchoProof is a pre-deployment compliance assurance layer for those agents.

## The failure mode

[click to the next slide]

This is a real agent turn from a collections call. Read it. It is warm, it is helpful, it is what you would want an agent to say.

[click, the provision appears on the paper card]

It is also prohibited. A debt collector may not communicate about a debt with any person other than the consumer, and the agent is speaking to her brother.

[click, the mono line appears underneath]

This is the shape of the problem. It is not a hallucination and it is not a wrong fact, so nothing in a normal evaluation stack is looking for it. Your eval suite scores this as a good response.

## What it is

[click to the next slide]

In one sentence: it reads what the agent said, finds the rule in the client's own rulebook that governs it, and rules from that rule.

[click, the read box appears]

Four moves. It reads the turn, and only the agent's turns are adjudicated.

[click, the claim box appears]

It locates claims as verbatim quotes.

[click, the retrieve box appears]

It retrieves the governing provision.

[click, the rule and seal box appears]

And it rules on it and seals the record.

## The pipeline

[click to the next slide]

[click, the six stages draw]

An OpenAI compatible proxy sits in front of the agent's model call, so the agent itself does not change.

Claim extraction returns verbatim quotes, and the character offsets into the transcript are computed in code by locating that quote. A paraphrase is rejected rather than stored, which means a claim is always the agent's own words.

[click, the gold path drops out and rejoins]

This gold path is deterministic verification. Money and dates are canonicalised and compared in code, ahead of anything else. A value that arithmetic can settle never reaches a model, and the evidence records both sides of the comparison.

[click, the waveform appears and gets sliced]

And the turn travels as signal, cut at claim boundaries, because the claim is the unit of adjudication rather than the sentence or the call.

## The isolation boundary

[click to the next slide]

This is the argument. Everything else is engineering.

[click, retrieval sweeps the corpus]

On the left is the client's rulebook. Retrieval is hybrid: keyword and dense vector search, fused, then reranked by a cross encoder that looks at the claim and each candidate provision together.

[click, one provision and one claim lift out]

It hands forward exactly one provision, alongside one claim.

[click, the fence and the judge draw]

Those two things are the only things that cross into the judge, and the judge rules from that text alone.

[click, the blocked arrows appear]

The rulebook does not cross. The model's own training knowledge does not cross.

That is what makes a verdict checkable rather than an opinion. The exact text the judge was handed is stored and printed next to the verdict, so you can read what it was given and disagree.

And there is a second reason, which is about debugging. If the judge could reach past that fence, a wrong verdict would be unattributable. You could never tell whether retrieval surfaced the wrong rule or the judge misread the right one, so you would never know which half to go and fix.

## The five verdict states

[click to the next slide]

[click twice, supported and contradicted appear]

Five states, never a pass or a fail. Two of them decide.

[click, the three abstentions appear]

Three of them decline, and they are three genuinely different failures. Nothing in the rulebook cleared the bar at all. Or something did but not confidently enough. Or two candidates were plausible and pointed different ways.

[click, the routing appears]

All three route to human review, counted separately from findings everywhere in the system.

[click, the closing line appears]

Because a system that forces a verdict in order to avoid an abstention is a system optimising its own scoreboard.

## Evidence and the seal

[click to the next slide]

[click, the intact chain draws]

Every model call, every retrieval call and every finding writes a span into an append only, hash chained log. Each entry's hash covers the entry before it.

[click, the middle entry is edited and the links break]

Edit something in the middle and every link after it breaks. You cannot quietly amend this record, you can only visibly destroy it.

[click, the content addressing line appears]

The artifacts are content addressed on disk, and the index holds records rather than evidence content, so there is no way around it through the database either.

## The stack

[press 9 to jump to the stack slide]

[click, the first stack draws]

This is a cascaded voice agent. Telephony, speech to text, an orchestrator holding conversation state, the model call, text to speech, and audio back to the caller.

[click, echoproof appears in the chain]

EchoProof attaches at exactly one point, in front of the model call. You change a base URL.

[click, the return path and the adjudication branch appear]

And the response goes back unmodified and is never delayed. Adjudication branches off to the side after the response has already gone. A capture failure cannot become a request failure.

[click, the second stack appears]

Swap every vendor in that stack and the attachment point does not move. One endpoint, any stack.

## Verticals and the packs

[click to the next slide]

[click, the four cartridges seat into the core]

The engine holds nothing that knows what industry it is in. Everything client specific is one of four data packs: their rulebook, the scenarios they care about, the personas to test against, and the criteria that decide what blocks a release.

That last pack is what makes the gate decision theirs rather than ours.

[click, the policy cartridge swaps]

Swap the rulebook from a federal regulation to a telecom standard with a completely different numbering convention, and no engine code changes.

[click, the industries appear]

Which is why this is not a debt collection product. It reaches every industry where a regulated conversation is being automated.

## Today and production

[click to the next slide]

[click, the today column appears]

Everything I am about to show you runs end to end on this laptop. Real adjudications, real evidence on disk. Nothing in the demo is mocked.

[click, the production column appears]

Production is designed and deliberately not built. One model interface throughout, so pointing it at enterprise hosting is a base URL and a model string. Storage to object storage with retention locks. The reranker to a GPU, which is the throughput lever. Adjudication to a worker pool, which scales cleanly because every turn is independent.

[click, the configuration line appears]

The boundary between those columns is configuration, not a rewrite.

## The walkthrough

[alt tab to the browser, tab three, the bench]

Let me show you it running.

Every assessment on disk, each one an append only evidence log, each card saying chain verified because the chain was re-verified when this page loaded.

[click the top card, third party disclosure - demo baseline]

This is the conversation from the second slide.

[point at gate decision at the top]

Gate decision, computed from the client's criteria pack. Block release. That is a computation over their thresholds, not our opinion, and it is computed on read rather than stored so it cannot drift from the findings underneath it.

[point at the abstentions section]

These are the abstentions, listed apart from the findings.

[scroll to findings and click the first one]

[point at what was said]

The claim, sliced out of the recorded transcript by character offset.

[point at the cream coloured card]

The governing provision, verbatim. You are not asked to trust the verdict, you are shown the text it rests on.

[scroll down to the evidence trace]

[point at the retrieval step]

And the trace. This step is retrieval: several queries under different legal theories, every candidate the judge was offered, and the one it selected.

[point at the last step, evidence seal]

And the seal, for this specific finding.

## Close

[alt tab back to the deck]

[press end to jump to the last slide]

[click, the second line appears]

Every claim has a source, because it is a verbatim quote resolved to an offset in the transcript the agent produced.

[click, the third line appears]

Every verdict has a rule, because the judge only saw one retrieved provision and that provision is printed beside the verdict.

[click, the ask appears]

Every finding has evidence, because every stage wrote a span into a chain that breaks visibly if anyone touches it.

[stop clicking and look at the room]

What I want is an introduction to somebody who signs off that a voice agent can go live.

## If something goes wrong

### The bench will not load

[check the terminal is still running run_ui.py]

[reload the page]

If it does not recover, go back to the deck and close from the last slide. Say this.

That runs live on this laptop and I am not going to debug it in front of you. Everything I described is on disk and I will show anyone who wants it afterwards.

### A screen renders half way

[hard reload with control shift r]

Keep talking through the reload.

## Questions you will get

### "How is this different from asking a model whether the call was compliant?"

Because you cannot audit that answer. It would be recalling a regulation from training, at some version you cannot identify, and you have nothing to check it against.

Ours is handed one provision and has to rule from that text, and then we print the provision next to the verdict. You can disagree with it in five seconds, which is the whole design.

### "What happens when retrieval gets it wrong?"

One of two different things, deliberately. If nothing plausible surfaces at all, that is no governing rule and it goes on the policy gap list. If something surfaces but not confidently enough, that routes to a human.

Keeping those separate matters, because collapsing them turns a retrieval failure into a positive claim that no rule exists.

### "Can it run on a live call?"

The proxy already does, and it adds effectively nothing because it never blocks. The adjudication is the slow part and it runs after the response has gone.

But the value is pre-deployment, where you can afford to be thorough and where abstaining costs nothing. Interrupting a live customer call is a different product.

### "What does a client have to give you?"

Four things: their rulebook structured section by section, the scenarios they care about, the customer personas to test against, and their own thresholds for what stops a release.

The engine has no industry knowledge in it, so that is the entire integration on the data side.

### "What is the hardest problem left?"

Compound obligations. A rule that requires two things in one sentence gets split into two claims, and each half gets judged against the whole rule, so text that complies can be marked as violating.

It is structural rather than a tuning issue, and the fix is evaluating those obligations at turn level rather than claim level. That is not built.
