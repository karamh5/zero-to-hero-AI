# Final demo, 13 minutes

## Before you start

[run .venv/Scripts/python scripts/run_ui.py]

[open http://127.0.0.1:8077/rig in tab one]

[under 02 / select conversation, group supported, click 04 validation notice contents described]

[type warm up in the assessment title box, click run adjudication, let it finish]

[open presentation/demo-day/deck.html in tab two, press f for fullscreen]

[open http://127.0.0.1:8077/bench in tab three, check the top card reads third party disclosure - demo baseline]

[press n twice in the deck to check presenter notes open and close]

## Opening

[slide 1: click 2x]

Before this was a product, it was my job.

I worked in compliance at TELUS. And the thing nobody tells you before you do that work is that compliance is not really about knowing the rules. Almost everyone knows the rules. It is about proof. You can be completely right and still lose the room, because you could not show your work.

That idea is the whole of what I am about to show you.

Right now every large enterprise is racing to put AI agents into conversations that are legally governed. Collections. Insurance. Healthcare. And the thing holding those launches up is not the model.

## The bottleneck

[slide 2: click 1x]

[click 1x]

It is this. The model is ready. The integration is ready. The business case is signed.

[click 1x]

And then it stops, because one person has to put their name on a document saying this agent is safe to talk to customers, and they have nothing to base that on.

[click 1x]

The constraint is not capability. It is proof. Which brings me to how that proof gets produced today.

## What they do today

[slide 3: click 1x]

[click 1x]

It is a person, with headphones, and a rulebook open next to them. Industry benchmarks put manual quality review at somewhere between one and five percent of calls.

[click 1x]

And that number is not laziness, it is arithmetic. A trained analyst gets through ten to fifteen interactions in a day. It is a structural ceiling, and you cannot staff your way out of it.

So ninety five percent or more of what your agents say is never examined by anyone, it is reviewed weeks after go live, and what comes out is a score with no rule attached.

[click 1x]

This is a manual process, and EchoProof automates it. Not a new process to learn. The same review, on every single turn, before launch instead of after, and every flag comes out carrying the rule it broke.

## What it is

[slide 4: click 1x]

In one sentence, it reads what the agent said, finds the rule in the client's own rulebook that governs it, and rules from that rule.

[click 4x]

Four moves. It reads the turn, and only the agent's turns are ever adjudicated. It locates the claims as verbatim quotes. It retrieves the governing provision. And it rules on it and seals the record.

Everything from here is how each of those is made trustworthy, because any one done loosely turns this back into an opinion.

## The pipeline

[slide 5: click 1x]

[click 1x]

An OpenAI compatible proxy sits in front of the agent's model call. You change a base URL and nothing else in the stack moves.

Claim extraction returns verbatim quotes, and the offsets are computed in code by locating that quote, so a paraphrase gets rejected rather than stored.

[click 1x]

Then this gold path. Money and dates are canonicalised and compared in code, ahead of retrieval. A value that arithmetic can settle never reaches a model at all.

[click 1x]

And the turn travels as signal, cut at claim boundaries, because the claim is the unit of adjudication rather than the sentence or the call.

Which sets up the one decision this whole thing rests on.

## The isolation boundary

[slide 6: click 1x]

[click 1x]

Retrieval is hybrid. Keyword and dense search across the client's corpus, fused, then reranked by a cross encoder.

[click 1x]

It lifts exactly one provision out, and pairs it with one claim.

[click 1x]

Then the fence. Those two things are the only things that cross into the judge, and the judge rules from that text alone.

[click 1x]

The corpus does not cross. The model's own training knowledge does not cross.

Two reasons. The rule text it was handed is stored, so a verdict is falsifiable just by reading it. And if the judge could reach past that fence, a wrong verdict would be unattributable, because you could never tell whether retrieval or the judge failed.

## The five states

[slide 7: click 1x]

[click 2x]

Five verdict states, never a pass or a fail. Two of them decide.

[click 1x]

Three of them decline.

[click 1x]

Those three route to a human reviewer, and they are counted separately from findings everywhere in the system.

[click 1x]

Because a system that forces a verdict to avoid an abstention is optimising its own scoreboard. A confident wrong answer costs a compliance officer far more than an honest I do not know.

## Evidence and traceability

[slide 8: click 1x]

[click 1x]

Every model call, every retrieval call and every finding writes a span into an append only, hash chained log. Each entry's hash covers the entry before it.

[click 1x]

So watch what happens when somebody edits an entry in the middle. Every link after it breaks, in sequence. You cannot quietly amend this record. You can only visibly destroy it.

[click 1x]

And this is the part that matters most for governance. Published training lineage gives you traceability of the model. This gives you traceability of the decision, which is what a regulator actually asks about.

## Audio as evidence

[slide 9: click 1x]

[click 1x]

Speech to text is Deepgram Nova-3, which returns word level timestamps.

[click 1x]

The claim extractor gives character offsets into the transcript. Those two map onto each other deterministically.

[click 1x]

And that span slices the source audio, so a finding carries a clip of the exact sentence flagged, not the whole call.

Adjudication is text only. Audio attaches after the verdict exists, which makes it evidence for a finding and never an input to one.

## The stack

[slide 10: click 1x]

[click 1x]

This is a cascaded voice agent. Telephony, speech to text, an orchestrator, the model call, text to speech, back to the caller.

[click 1x]

EchoProof attaches at exactly one point, in front of the model call.

[click 1x]

The response goes back unmodified and is never delayed. Adjudication branches off to the side, after the response has already gone. A capture failure cannot become a request failure, and that is enforced by tests.

[click 1x]

Now swap every vendor in that stack. The attachment point does not move. One endpoint, any stack. Which is exactly what makes the next part possible.

## Where it sits at Hexaware

[slide 11: click 1x]

[click 1x]

The client brings the regulation, their policy and their risk threshold.

[click 1x]

Hexaware brings the agent build, the CX operations, the delivery centres.

[click 1x]

EchoProof sits in exactly one place. Between the build and the sign off.

[click 1x]

And out the other side comes the artifact. Not an assurance the agent was tested. An evidence file showing what was tested and against which rule, that the client can put in front of their own regulator.

Same layer regardless of client, regulation or vendor stack.

## Go to market

[slide 12: click 1x]

[click 1x]

Three routes, and all of them are motions Hexaware already runs. It attaches to CX engagements already being won, as the assurance line item.

[click 1x]

It opens a new one, which is auditing agents somebody else built, because being vendor neutral means Hexaware can assess a stack it did not deliver.

[click 1x]

And it recurs, because the rulebook is an input. When the regulation moves, the assessment re runs.

[click 1x]

The strategic one is the middle route, and here is why.

## Market and cost

[slide 13: click 1x]

[click 1x]

The voice AI agent market is around three and a half billion dollars this year, heading toward thirty five billion by 2033. Every one of those deployments is a governance sign off waiting to happen.

[click 1x]

And on cost, our measured campaign came to eighty two cents of model spend for eighteen calls, which projects to roughly twenty three dollars per hundred call campaign. Model spend is not the constraint here. Reviewer time is, and that is what this is aimed at.

## The landscape

[slide 14: click 1x]

[click 1x]

So who else is doing this. Two axes. Before or after deployment. And independent, or the vendor checking itself.

[click 1x]

Conversation intelligence, Observe.AI and Modulate, analyse production calls at full coverage. Genuinely valuable, but it is scoring against rubrics after the call.

[click 1x]

The closest thing to us is OpenAI Presence, launched in July. Strong product, evals and graders built in. But it is end to end. The same vendor supplies the voice, the model and the readiness answer, so what comes back is a self check. And it does not cover cascaded stacks at all. Same problem with the voice vendors shipping built in compliance engines.

[click 1x]

Which leaves this quadrant empty. Independent, and before launch.

And it matters commercially, because OpenAI is shipping Presence through select global systems integrators. Being able to say we assure any agent, not only the ones built on one vendor, is the differentiator in exactly that room.

## Scale

[slide 15: click 1x]

[click 1x]

Everything I am about to show you runs end to end on this laptop, with real evidence on disk. Nothing in the demo is mocked.

[click 1x]

Production is designed and deliberately not built. Bedrock is a base URL and a model string. Retrieval to OpenSearch, the cross encoder to a GPU, artifacts to S3 with object lock. And adjudication becomes a worker pool that scales linearly, because every turn is independent.

[click 1x]

The boundary between those columns is configuration, not a rewrite.

## How it got here

[slide 16: click 1x]

[click 1x]

One thing I want to be clear about. This did not come out of my head fully formed.

I took it to an applied engineer at Deepgram, and the feedback was direct. If you are citing audio as evidence you cannot slice on approximate timings, you need word level timestamps mapped onto the transcript. That audio path exists because of that conversation.

[click 1x]

And I took it to Roger on the Hexaware CX side. The feedback there was that a finding a reviewer cannot act on is just noise, and that the buyer is the person signing off, not the engineer. So the gate decision became client configured rather than ours, and the case file got rebuilt around the rule text instead of around a score.

Both of those changed the product, not the pitch. And the second one is what you are about to look at.

## The walkthrough

[alt tab to the browser, tab three, the bench]

So let me use it the way the person it is built for would use it.

I am the compliance engineer. It is Monday. A voice agent build has been handed to me and I have to decide whether it can go live.

This is the bench. Every assessment run, each card saying chain verified, meaning the chain was re verified when this page loaded.

[click the top card, third party disclosure - demo baseline]

First question I ask is always the same. Can this ship.

[point at the gate decision block at the top]

Block release. And that is not our opinion. It is computed on read from the client's own criteria pack. They told us one critical finding stops a deployment, so this stops.

[point at the verdicts table]

Second question. What is the shape of it. Two contradicted, six abstentions.

[point at the abstentions section]

And the abstentions are listed apart from the findings, deliberately. Those are the ones it declined to rule on, and they are my queue, not evidence that the agent was fine.

[scroll to findings and click the first finding]

Third question. Show me the worst one.

[point at what was said]

This is what the agent said, sliced out of the recorded transcript by character offset. Not summarised, not restated.

[point at the cream coloured card]

And this is the rule it broke, printed as the regulation prints it. Section 1006.6(d)(1). I am not asked to trust a verdict, I am shown what it rests on, so I can disagree in five seconds.

[point at why it failed]

The reasoning names the third party and says which exceptions it ruled out.

[scroll down to the evidence trace]

Fourth question, and this is the one that actually matters to me. How do I know this is right.

[point at the retrieval step]

Every step. This one is retrieval: the queries it ran, every candidate provision it was offered, and the one it selected.

[point at the last step, evidence seal]

And the seal at the end. If anyone edits any of it after the fact, this breaks visibly.

[click corpus in the top nav]

Fifth question. What did it not look at. This is the rulebook, and I can see which provisions retrieval reached on this run. My coverage gap, in one place.

[click delta in the top nav]

And then the loop that closes it. Same scenario, same seed, only the agent changed. The finding closed and nothing new opened. That is what I need to see before I sign, because a fix that closes one issue and opens another has not fixed anything.

[stop clicking and look at the room]

That is a compliance review that took two minutes instead of two weeks, and every step of it is on the record.

## Close

[alt tab back to the deck]

[press 1 7 and enter to jump to the last slide]

[click 3x]

Every claim has a source. Every verdict has a rule. Every finding has evidence.

I have not really been selling you a product here. The product is a proxy, a rulebook and a hash chain. What I am actually saying is that governance is the thing standing between these deployments and revenue, and it is solvable.

So the ask is a live engagement to point this at, and an introduction to whoever signs off that an agent can go live.

Thank you.

## If something goes wrong

### The bench will not load

[check the terminal is still running run_ui.py]

[reload the page]

If it does not come back, go back to the deck and close from the last slide. Say this.

That runs live on this laptop and I am not going to debug it in front of you. Everything I described is on disk and I will walk anyone through it afterwards.

### A screen renders half way

[hard reload with control shift r]

Keep talking through the reload. Do not narrate it.

## Questions you will get

### "How is this different from OpenAI Presence?"

Presence is a strong product and it does have evals and graders in it. The difference is who is holding the pen. It is OpenAI's model, OpenAI's guardrails and OpenAI's grader, so the readiness answer is a self check.

The other half is coverage. Presence is an end to end platform. A large share of real enterprise deployments are cascaded, with the speech layer from one vendor and the model from another, and an end to end product does not assess those at all. We are neutral to the whole stack, and a cascaded setup is actually easier for us to instrument because the seams are already there.

### "What about Observe.AI or the other conversation intelligence tools?"

They are good at what they do and they do get to full coverage, which is more than manual QA manages. But they are analysing production calls after the fact and scoring against rubrics somebody wrote.

We are pre deployment, and we adjudicate against the client's actual regulation with the provision cited. Different question, different point in the lifecycle. Honestly they are complements more than competitors.

### "Why not just have the model vendor build this in?"

Because you do not want the company supplying the agent to also be the company signing off that it is safe. That is a structural conflict, and every other regulated industry separates those two roles.

### "How does this handle a rulebook we have not seen?"

The rulebook is an input. It goes in as a data pack, chunked at section level with the real identifiers. We proved the boundary by swapping the corpus for a completely different industry's standard, with a different numbering convention, and no engine code changed.

### "What about open source, or running this on open weights models?"

There is a real thread there. The interface is one OpenAI compatible endpoint, so any model behind a compatible endpoint works, including open weights ones running in a client's own environment. For a bank that cannot send transcripts to a third party, that matters a lot.

And it lines up with where governance is heading. The reason people care about published training lineage on models like DeepSeek is traceability, being able to say where an answer came from. That is exactly the argument we make one layer up. Model lineage tells you where the weights came from. Our evidence chain tells you where the decision came from. A regulator asks the second question far more often than the first.

### "What does it cost to run at volume?"

Model spend is not the constraint. Our measured campaign was well under a dollar, and it projects to about twenty three dollars per hundred calls at realistic call lengths.

The real cost is compute on the reranker, which is a hardware line item and not a research problem, and the thing you are trading against is reviewer hours.

### "What is the hardest unsolved problem in it?"

Compound obligations. A rule that requires two things in one sentence gets split into two claims, and each half gets judged against the whole rule, so text that actually complies can be marked as violating.

That is structural rather than tuning. Claims are the unit of adjudication and obligations are not always claim shaped. Fixing it means evaluating multi element obligations at turn level, and that is not built.
