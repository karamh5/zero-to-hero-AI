# Fifteen minutes, demo day

## Before you start

[open a terminal in the EchoProof folder]

[run .venv/Scripts/python scripts/run_ui.py]

[open http://127.0.0.1:8077/rig in tab one]

[under 02 / select conversation, group supported, click 04 validation notice contents described]

[type warm up in the assessment title box, click run adjudication, let it finish]

[open presentation/demo-day/deck.html in tab two, press f for fullscreen]

[open http://127.0.0.1:8077/bench in tab three and check the top card reads third party disclosure - demo baseline]

[press n twice in the deck to check presenter notes open and close]

## Opening

[deck on slide one]

Enterprises are putting voice AI agents into conversations that are governed by law. Collections, insurance, healthcare, telecom.

The agent is fluent. It is confident. And it has no idea which of its sentences are legal.

[click twice, the claim marks and the chain draw]

EchoProof is a pre-deployment compliance assurance layer for those agents. Three claims on that slide, and I am going to show you the evidence for all three.

## The failure mode

[click to the next slide]

This is a real agent turn from a collections call. Read it.

It is warm, it is helpful, and it is exactly what you would want a customer service agent to say.

[click, the provision appears on the paper card]

It is also prohibited. A debt collector may not communicate about a debt with any person other than the consumer, and the agent is talking to her brother.

[click, the mono line appears underneath]

And this is the shape of the problem. It is not a hallucination and it is not a wrong fact, so nothing in a normal evaluation stack is shaped to look for it. Your eval suite scores this as a good response.

## What EchoProof is

[click to the next slide]

So, in one sentence. It reads what the agent said, finds the rule in the client's own rulebook that governs it, and rules from that rule.

[click, the read box appears]

Four moves. It reads the turn, and only the agent's turns are ever adjudicated.

[click, the claim box appears]

It locates the claims as verbatim quotes.

[click, the retrieve box appears]

It retrieves the governing provision.

[click, the rule and seal box appears]

And it rules on it and seals the record. Everything after this slide is how each of those four is made trustworthy.

## The pipeline

[click to the next slide]

[click, the six stages draw]

An OpenAI compatible proxy sits in front of the agent's model call.

Claim extraction returns verbatim quotes, and the character offsets into the transcript are computed in code by locating that quote. A paraphrase gets rejected rather than stored, which is a stronger guarantee than asking a model to count characters.

[click, the gold path drops out and rejoins]

Then this gold path. Money and dates are canonicalised and compared in code, ahead of retrieval. A value that arithmetic can settle never reaches a model at all, and the evidence records both sides of the comparison.

[click, the waveform appears and gets sliced]

And the turn itself travels as signal. That waveform is the agent turn, and it gets cut at claim boundaries, because the claim is the unit of adjudication rather than the sentence or the call.

## The isolation boundary

[click to the next slide]

This is the argument. Everything else is engineering. This is the reason a verdict here means anything at all.

[click, retrieval sweeps the corpus]

On the left is the client's corpus, every provision in their rulebook. Retrieval is hybrid: BM25 and dense vectors, fused by reciprocal rank fusion, then reranked by a cross encoder.

[click, one provision and one claim lift out]

It lifts exactly one provision out. That provision and one claim.

[click, the fence and the judge draw]

And then the fence. Those two things are the only things that cross into the judge, and the judge rules from that text alone.

[click, the blocked arrows appear]

The corpus does not cross. The model's own training knowledge does not cross.

That constraint is what makes a verdict checkable rather than an opinion. The exact text the judge was handed is stored in the evidence span and printed next to the verdict, so you can read what it was given and disagree with it.

There is a second reason for the fence, which is about debugging rather than trust. If the judge could reach past it, a wrong verdict would be unattributable, because you could never tell whether retrieval handed it the wrong provision or the judge misread the right one. Fencing it means every failure lands in exactly one component, and you can go and fix that component.

## The five verdict states

[click to the next slide]

[click, supported appears]

Five verdict states, never a pass or a fail. These are the exact strings in the evidence log.

Two of them decide. The retrieved rule supports what the agent said.

[click, contradicted appears]

Or it contradicts it.

[click, the three abstentions appear]

Three of them decline. Nothing in the corpus was a plausible match at all. Or something probably governs this but retrieval was not confident enough to adjudicate. Or two plausible candidates point in different directions.

[click, the routing to human review appears]

Those three route to human review, and they are counted separately from findings everywhere in the system.

[click, the closing line appears]

Because a system that forces a verdict in order to avoid an abstention is a system optimising its own scoreboard. Declining is a designed result.

## Evidence and the seal

[click to the next slide]

[click, the intact chain draws]

Every model call, every retrieval call and every finding writes a span into an append only, hash chained evidence log. Each entry's hash covers the hash of the entry before it.

[click, the middle entry is edited and the links break]

So watch what happens when somebody edits an entry in the middle. Every link after it breaks, in sequence, and the seal visibly fails.

You cannot quietly amend this record. You can only visibly destroy it.

[click, the content addressing line appears]

The artifacts themselves are content addressed on disk, and the index holds records and never evidence content, so there is no path to rewriting the evidence through the database either.

## Audio as evidence

[click to the next slide]

[click, the transcript bar appears]

Audio. Speech to text is Deepgram Nova-3, which returns word level timestamps.

[click, the word ticks appear]

The claim extractor gives us character offsets into the transcript. Those two map onto each other deterministically.

[click, the clip bracket draws]

And the resulting time span slices the source audio with ffmpeg. So a finding carries a clip of the exact sentence that was flagged, not the whole call. A reviewer hears the thing itself, in the agent's voice, with the tone intact.

That matters more than it sounds. A transcript of a sentence and a recording of a sentence are not the same evidence, and when somebody senior is deciding whether to hold a launch, they want to hear it.

[click, the ordering line appears]

The ordering matters. Adjudication is text only. Audio is attached after the verdict already exists, which makes it evidence for a finding and never an input to one.

## The stack

[click to the next slide]

[click, the first stack draws]

This is a cascaded voice agent. Caller on the phone, telephony, speech to text, an orchestrator holding conversation state, a model call, text to speech, audio back to the caller.

[click, echoproof appears in the chain]

EchoProof attaches at exactly one point. In front of the model call, as an OpenAI compatible proxy. You change a base URL.

[click, the return path and the adjudication branch appear]

And this is the part that matters operationally. The upstream response is returned unmodified and it is never delayed. The adjudication path branches off to the side, after the response has already gone back to the orchestrator.

A capture failure cannot become a request failure. That is enforced by tests, not by intent.

[click, the second stack appears]

Now swap every vendor in that stack. Different telephony, different speech to text, a different orchestration framework, a different model provider.

The attachment point does not move. One endpoint, any stack.

## Verticals and the packs

[click to the next slide]

This is the commercial architecture. The engine holds no field, no constant and no branch that knows which industry it is running in.

[click, the four cartridges seat into the core]

Everything client specific arrives as one of four data packs. The policy pack is their rulebook. The scenario pack is the situations they care about. The persona pack is the customers to play against the agent.

And the criteria pack is the thresholds that decide what blocks a release, which is what makes the gate decision theirs rather than ours.

[click, the policy cartridge swaps]

Swap the policy cartridge from Regulation F to a telecom customer contact standard, with a completely different section identifier convention, and no engine code changes.

[click, the industries appear]

Which means the same product reaches every industry where a regulated conversation happens. What changes per client is data their compliance team already maintains, rather than a services engagement to rebuild the engine around their sector.

And it is worth saying what that boundary cost to hold. Swapping the corpus is what surfaced the places where engine code had quietly assumed one regulation's identifier format. Those were real defects, and they only became visible because the second corpus numbered its sections differently.

## Today and production

[click to the next slide]

[click, the today column appears]

I want to be precise about what is real and what is designed.

Everything I am about to show you runs end to end on this laptop. Real adjudications, real evidence on disk, chains that verify on read. Nothing in the demo is mocked.

[click, the production column appears]

Production is designed and deliberately not built. There is one model interface in the codebase, the OpenAI SDK against a compatible base URL, so pointing it at Bedrock is a base URL and a model string.

Artifacts move to S3 with object lock. Retrieval moves to OpenSearch and the cross encoder moves to a GPU. Adjudication becomes a horizontally scaled worker pool, and it scales cleanly because every turn is independent of every other turn.

[click, the configuration line appears]

The boundary between those two columns is configuration, not a rewrite. That was a day one decision and it is the reason the swap is cheap.

## The walkthrough

[alt tab to the browser, tab three, the bench]

Let me show you it running.

This is every assessment on disk. Each one is an append only evidence log, and each card says chain verified because the chain was re-verified when the page loaded, not because a flag was stored somewhere.

[click the top card, third party disclosure - demo baseline]

This is the conversation from the second slide.

[point at gate decision at the top]

Gate decision, computed from the client's criteria pack. It reads block release. That is a computation over their thresholds, not our opinion, and it is computed on read rather than stored, so it cannot drift away from the findings it summarises.

[point at the abstentions section]

And these are the abstentions, listed apart from the findings. Claims where retrieval did not clear the bar, routed to a human rather than guessed at.

[scroll to findings and click the first one]

[point at what was said]

The claim, sliced out of the recorded transcript by character offset. Never restated, never paraphrased.

[point at the cream coloured card]

The governing provision, verbatim, 1006.6(d)(1). You are not asked to trust the verdict, you are shown the text it rests on.

[point at why it failed]

And the reasoning names the third party explicitly, and says which exceptions it checked and ruled out.

[scroll down to the evidence trace]

Then the trace. Eight steps.

[point at the retrieval step]

This one is retrieval, and it is open already. Three search queries under genuinely different legal theories, because one sentence can engage several unrelated rules. Every candidate the judge was offered, and the one it selected.

[point at the last step, evidence seal]

And the seal. That is the chain we just looked at on the slide, for this specific finding.

## Fix and re-run

[alt tab back to the deck]

[click to the next slide]

[click, the before panel appears]

One more thing, because a finding is only worth having if you can prove the fix worked.

[click, the arrow appears]

Same scenario, same seed, same policy pack, same judge, same thresholds. Only the agent changed.

[click, the after panel appears]

The finding against 1006.18(b)(3) closed, and nothing new opened.

[click, the closing lines appear]

Both of those conditions are required, and this is the part people get wrong. A change that closes one finding while opening another has not fixed the agent, it has moved the problem.

Findings are tracked by the rule they cite, never by claim id. Claim ids change every run, so keying on them would report every issue as closed and new at the same time, which looks like a perfect fix and is worse than useless.

## Close

[click to the next slide]

So, three lines.

[click, the second line appears]

Every claim has a source, because it is a verbatim quote resolved to an offset in the transcript the agent actually produced.

[click, the third line appears]

Every verdict has a rule, because the judge only ever saw one retrieved provision, and that provision is printed beside the verdict.

[click, the ask appears]

Every finding has evidence, because every stage wrote a span into a hash chain that breaks visibly if anyone touches it.

[stop clicking and look at the room]

What I want from this room is an introduction to somebody who signs off that a voice agent can go live, so I can find out what they would actually pay for.

## If something goes wrong

### The bench will not load

[check the terminal is still running run_ui.py]

[reload the page]

If it does not come back, go back to the deck and continue from fix and re-run. The walkthrough is the proof, but the argument survives without it. Say this.

That is running live on this laptop and I am not going to debug it in front of you. Everything I just described is on disk and I will show anybody who wants to see it afterwards.

### A screen renders half way

[hard reload with control shift r]

Keep talking through the reload.

## Questions you will get

### "How do you know the judge is not just recognising the regulation from pretraining?"

I cannot rule it out entirely, and that is exactly why the second corpus exists. It is a synthetic telecom standard with invented section identifiers the model cannot have seen, and the engine adjudicates against it without a code change.

That is a portability result rather than a general claim, and I would want to run it against a real client's private rulebook before saying anything stronger.

### "Why not fine tune a classifier instead of retrieval and a judge?"

Because a classifier cannot cite. The product is not a label, it is a label with the governing paragraph attached and a reviewer who can check it in seconds.

There is also an operational reason. A client's corpus changes when the regulation changes, and retrieval absorbs that without retraining anything.

### "What happens when retrieval gets it wrong?"

One of two things, and they are deliberately different. If nothing plausible surfaces at all, that is no governing rule and it lands on the policy gap list. If something surfaces but not confidently enough, that is retrieval below confidence and it routes to a human.

Keeping those separate matters, because collapsing them turns a retrieval failure into a false claim that no rule exists.

### "Can this run in real time on a live call?"

Not the full path, and I would not want it to. The deterministic checks on money and dates are instant because they are code rather than a model, so a narrow version could.

But the value here is pre-deployment, where you can afford to be thorough and where abstaining is free. Blocking a live customer call is a different product with a different risk profile.

### "What is the hardest unsolved problem in it?"

Compound obligations. A rule that requires two things in a single sentence gets split into two claims, and each half gets judged against the whole rule, so text that actually complies can be failed twice.

It is structural rather than a tuning problem: claims are the unit of adjudication and obligations are not always claim shaped. The fix is evaluating multi element obligations at turn level, and that is not built.

### "Who is the buyer?"

Whoever signs off that the agent can go live. In collections that tends to be the compliance officer, with the budget sitting wherever the deployment sits.

That is a hypothesis and not a validated finding, and validating it is what I am asking this room for.
