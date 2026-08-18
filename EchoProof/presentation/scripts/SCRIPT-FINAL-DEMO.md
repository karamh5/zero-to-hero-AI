================ FINAL DEMO, 13 MINUTES ================

---------------- BEFORE YOU START ----------------

[RUN .VENV/SCRIPTS/PYTHON SCRIPTS/RUN_UI.PY]

[OPEN HTTP://127.0.0.1:8077/RIG IN TAB ONE]

[UNDER 02 / SELECT CONVERSATION, GROUP SUPPORTED, CLICK 04 VALIDATION NOTICE CONTENTS DESCRIBED]

[TYPE WARM UP IN THE ASSESSMENT TITLE BOX, CLICK RUN ADJUDICATION, LET IT FINISH]

[OPEN PRESENTATION/DEMO-DAY/DECK.HTML IN TAB TWO, PRESS F FOR FULLSCREEN]

[OPEN HTTP://127.0.0.1:8077/BENCH IN TAB THREE, CHECK THE TOP CARD READS THIRD PARTY DISCLOSURE - DEMO BASELINE]

---------------- OPENING ----------------

[SLIDE 1: CLICK 2X]

Before this was a product, it was my job.

I worked in compliance at TELUS. And the thing nobody tells you is that compliance is not about knowing the rules. Almost everyone knows the rules. It is about proof. You can be completely right and still lose, because you could not show your work.

That idea is the whole of what I am about to show you.

Every large enterprise is now racing to put AI agents into legally governed conversations. Collections. Insurance. Healthcare. And what holds those launches up is not the model.

---------------- THE BOTTLENECK ----------------

[SLIDE 2: CLICK 1X]

[CLICK 1X]

It is this. The model is ready. The integration is ready. The business case is signed.

[CLICK 1X]

And then it stops, because one person has to put their name on a document saying this agent is safe to talk to customers, and they have nothing to base that on.

[CLICK 1X]

The constraint is not capability. It is proof. Which brings me to how that proof gets produced today.

---------------- WHAT THEY DO TODAY ----------------

[SLIDE 3: CLICK 1X]

[CLICK 1X]

It is a person, with headphones, and a rulebook open next to them. Industry benchmarks put manual quality review at somewhere between one and five percent of calls.

[CLICK 1X]

That is arithmetic, not laziness. A trained analyst gets through ten to fifteen interactions a day. It is a structural ceiling you cannot staff your way out of.

So most of what your agents say is never examined by anyone, it is reviewed weeks after go live, and what comes out is a score with no rule attached.

[CLICK 1X]

This is a manual process, and EchoProof automates it. Not a new process to learn. The same review, on every single turn, before launch instead of after, and every flag comes out carrying the rule it broke. Here is what that actually is.

---------------- WHAT IT IS ----------------

[SLIDE 4: CLICK 1X]

In one sentence: it reads what the agent said, finds the provision in the client's own rulebook that governs it, and decides from that text alone.

[CLICK 4X]

Four moves. It reads the turn, and only the agent's turns. It locates claims as verbatim quotes. It retrieves the governing provision. And it decides, then seals the record.

Everything from here is how each of those is made trustworthy, because any one done loosely turns this back into an opinion, starting with how it reads.

---------------- THE PIPELINE ----------------

[SLIDE 5: CLICK 1X]

[CLICK 1X]

An OpenAI compatible proxy sits in front of the model call. You change a base URL and nothing else moves.

Claim extraction returns verbatim quotes, and the offsets are computed in code by locating that quote, so a paraphrase gets rejected rather than stored.

[CLICK 1X]

Then this gold path. Money and dates are canonicalised and compared in code, ahead of retrieval. A value that arithmetic can settle never reaches a model at all.

[CLICK 1X]

And the turn travels as signal, cut at claim boundaries, because the claim is the unit of adjudication rather than the sentence or the call.

Which sets up the one decision this whole thing rests on.

---------------- THE ISOLATION BOUNDARY ----------------

[SLIDE 6: CLICK 1X]

[CLICK 1X]

Retrieval is hybrid. Keyword and dense search across the client's corpus, fused, then reranked by a cross encoder.

[CLICK 1X]

It lifts exactly one provision out, and pairs it with one claim.

[CLICK 1X]

Then the fence. Those two things are the only things that cross into the judge, and the judge rules from that text alone.

[CLICK 1X]

The corpus does not cross. The model's own training knowledge does not cross.

Two reasons. The provision it was handed is stored, so a verdict is falsifiable by reading it. And if it could reach past that fence, a wrong verdict would be unattributable, because you could never tell whether retrieval or the judge failed. That fence decides whether it speaks at all.

---------------- THE FIVE STATES ----------------

[SLIDE 7: CLICK 1X]

[CLICK 2X]

Five verdict states, never a pass or a fail. Two of them decide.

[CLICK 1X]

Three of them decline.

[CLICK 1X]

Those three route to a human reviewer, counted separately from findings everywhere in the system.

Because a system that forces a verdict to avoid an abstention is optimising its own scoreboard. A confident wrong answer costs a compliance officer far more than an honest I do not know. Every one of those gets logged the same way.

---------------- EVIDENCE AND TRACEABILITY ----------------

[SLIDE 8: CLICK 1X]

[CLICK 1X]

Every model call, every retrieval call and every finding writes a span into an append only, hash chained log. Each entry's hash covers the entry before it.

[CLICK 1X]

Watch what happens when somebody edits an entry in the middle. Every link after it breaks. You cannot quietly amend this record, only visibly destroy it.

[CLICK 1X]

And this is the part that matters most for governance. Published training lineage gives you traceability of the model. This gives you traceability of the decision, which is what a regulator actually asks about. And that traceability does not stop at text.

---------------- AUDIO AS EVIDENCE ----------------

[SLIDE 9: CLICK 1X]

[CLICK 1X]

Speech to text is Deepgram Nova-3, which returns word level timestamps.

[CLICK 1X]

The claim extractor gives character offsets into the transcript. Those two map onto each other deterministically.

[CLICK 1X]

And that span slices the source audio, so a finding carries the exact sentence flagged, not the whole call.

Adjudication is text only. Audio attaches after the verdict exists, so it is evidence for a finding and never an input to one. Now, where does all of this actually sit.

---------------- THE STACK ----------------

[SLIDE 10: CLICK 1X]

[CLICK 1X]

Top layer, the customer's voice agent. Telephony, Deepgram for speech to text, an orchestrator, text to speech.

[CLICK 1X]

Middle layer, us. One OpenAI compatible endpoint, sitting in front of the model call.

[CLICK 1X]

Bottom layer is our engine, and the response goes back unmodified and is never delayed. Adjudication runs to the side, after the response has gone. A capture failure cannot become a request failure, and that is enforced by tests.

[CLICK 1X]

Swap every vendor in that top layer. The attachment point does not move. Which is what makes the next part possible.

---------------- WHERE IT SITS AT HEXAWARE ----------------

[SLIDE 11: CLICK 1X]

[CLICK 1X]

The client brings the regulation, their policy and their risk threshold.

[CLICK 1X]

Hexaware brings the agent build, the CX operations, the delivery centres.

[CLICK 1X]

EchoProof sits in exactly one place. Between the build and the sign off.

[CLICK 1X]

And out the other side comes the artifact. Not an assurance the agent was tested, an evidence file showing what was tested and against which rule, that the client can put in front of their own regulator.

Same layer regardless of client, regulation or vendor stack, which is what makes this repeatable.

---------------- GO TO MARKET ----------------

[SLIDE 12: CLICK 1X]

[CLICK 1X]

Three routes, and all of them are motions Hexaware already runs. It attaches to CX engagements already being won, as the assurance line item.

[CLICK 1X]

It opens a new one, which is auditing agents somebody else built, because being vendor neutral means Hexaware can assess a stack it did not deliver.

[CLICK 1X]

And it recurs, because the rulebook is an input. When the regulation moves, the assessment re runs.

[CLICK 1X]

The strategic one is the middle route, but first, the size of that room.

---------------- MARKET AND COST ----------------

[SLIDE 13: CLICK 1X]

[CLICK 1X]

The voice AI agent market is around three and a half billion dollars this year, heading toward thirty five billion by 2033. Every one of those deployments is a governance sign off waiting to happen.

[CLICK 1X]

And on cost, our measured campaign came to eighty two cents of model spend for eighteen calls, which projects to roughly twenty three dollars per hundred call campaign. Model spend is not the constraint here. Reviewer time is, and that is what this is aimed at. Which is why that route matters, and who else is in this space.

---------------- THE LANDSCAPE ----------------

[SLIDE 14: CLICK 1X]

[CLICK 1X]

So who else is doing this. Two axes. Before or after deployment. And independent, or the vendor checking itself.

[CLICK 1X]

Conversation intelligence, Observe.AI and Modulate, analyse production calls at full coverage. Genuinely valuable, but it is scoring against rubrics after the call.

[CLICK 1X]

The closest thing to us is OpenAI Presence, launched in July. Strong product, evals and graders built in. But it is end to end. The same vendor supplies the voice, the model and the readiness answer, so what comes back is a self check. And it does not cover cascaded stacks at all. Same problem with the voice vendors shipping built in compliance engines.

[CLICK 1X]

Which leaves this quadrant empty. Independent, and before launch.

And it matters commercially, because OpenAI is shipping Presence through select global systems integrators. Being able to say we assure any agent, not only the ones built on one vendor, is the differentiator in exactly that room.

And on scale, because it is the obvious next question. Everything I am about to show you runs end to end on this laptop against real evidence. At volume the same interface points at Bedrock, retrieval moves to OpenSearch, the reranker moves to a GPU, and adjudication runs as a worker pool that scales linearly, because every turn is independent. None of this happened in isolation, though.

---------------- HOW IT GOT HERE ----------------

[SLIDE 15: CLICK 1X]

[CLICK 1X]

One thing I want to be clear about. This did not come out of my head fully formed.

I took it to an applied engineer at Deepgram, and the feedback was direct. If you are citing audio as evidence you cannot slice on approximate timings, you need word level timestamps mapped onto the transcript. That audio path exists because of that conversation.

[CLICK 1X]

And I took it to Roger on the Hexaware CX side. The feedback there was that a finding a reviewer cannot act on is just noise, and that the buyer is the person signing off, not the engineer. So the gate decision became client configured rather than ours, and the case file got rebuilt around the rule text instead of around a score.

Both of those changed the product, not the pitch. And the second one is what you are about to look at.

---------------- THE WALKTHROUGH ----------------

[ALT TAB TO THE BROWSER, TAB THREE, THE BENCH]

So let me use it the way the person it is built for would use it.

I am the compliance engineer. It is Monday. A voice agent build has been handed to me and I have to decide whether it can go live.

This is the bench. Every assessment run, each card saying chain verified, meaning the chain was re verified when this page loaded.

[CLICK THE TOP CARD, THIRD PARTY DISCLOSURE - DEMO BASELINE]

First question I ask is always the same. Can this ship.

[POINT AT THE GATE DECISION BLOCK AT THE TOP]

Block release. And that is not our opinion. It is computed on read from the client's own criteria pack. They told us one critical finding stops a deployment, so this stops.

[POINT AT THE VERDICTS TABLE]

Second, what is the shape of it. Two contradicted, six abstentions.

[POINT AT THE ABSTENTIONS SECTION]

Listed apart from findings, deliberately. Those are my queue, not evidence the agent was fine.

[SCROLL TO FINDINGS AND CLICK THE FIRST FINDING]

Third, show me the worst one.

[POINT AT WHAT WAS SAID]

This is what the agent said, sliced out of the recorded transcript by character offset. Not summarised, not restated.

[POINT AT THE CREAM COLOURED CARD]

And this is the rule it broke, printed as the regulation prints it. Section 1006.6(d)(1). I am not asked to trust a verdict, I am shown what it rests on, so I can disagree in five seconds.

[POINT AT WHY IT FAILED]

The reasoning names the third party and the exceptions it ruled out.

[SCROLL DOWN TO THE EVIDENCE TRACE]

Fourth, and this is the one that matters. How do I know it is right.

[POINT AT THE RETRIEVAL STEP]

Every step. This one is retrieval: the queries it ran, every candidate it was offered, and the one it selected.

[POINT AT THE LAST STEP, EVIDENCE SEAL]

And the seal at the end. If anyone edits any of it after the fact, this breaks visibly.

[CLICK CORPUS IN THE TOP NAV]

Fifth, what did it not look at. This is the rulebook, and I can see which provisions retrieval reached. My coverage gap, in one place.

[CLICK DELTA IN THE TOP NAV]

And the loop that closes it. Same scenario, same seed, only the agent changed. The finding closed and nothing new opened. That is what I need before I sign, because a fix that closes one issue and opens another has fixed nothing.

[STOP CLICKING AND LOOK AT THE ROOM]

That is a compliance review that took two minutes instead of two weeks, and every step of it is on the record. Which is the whole point, stated simply.

---------------- CLOSE ----------------

[ALT TAB BACK TO THE DECK]

[PRESS 1 6 AND ENTER TO JUMP TO THE LAST SLIDE]

[CLICK 2X]

Every claim has a source. Every verdict has a rule. Every finding has evidence.

I have not really been selling you a product here. The product is a proxy, a rulebook and a hash chain. What I am actually saying is that governance is the thing standing between these deployments and revenue, and it is solvable.

So the ask is a live engagement to point this at, and an introduction to whoever signs off that an agent can go live.

Thank you.

---------------- IF SOMETHING GOES WRONG ----------------

---- THE BENCH WILL NOT LOAD ----

[CHECK THE TERMINAL IS STILL RUNNING RUN_UI.PY]

[RELOAD THE PAGE]

If it does not come back, go back to the deck and close from the last slide. Say this.

That runs live on this laptop and I am not going to debug it in front of you. Everything I described is on disk and I will walk anyone through it afterwards.

---- A SCREEN RENDERS HALF WAY ----

[HARD RELOAD WITH CONTROL SHIFT R]

Keep talking through the reload. Do not narrate it.

---------------- QUESTIONS YOU WILL GET ----------------

---- "HOW IS THIS DIFFERENT FROM OPENAI PRESENCE?" ----

Presence is a strong product and it does have evals and graders in it. The difference is who is holding the pen. It is OpenAI's model, OpenAI's guardrails and OpenAI's grader, so the readiness answer is a self check.

The other half is coverage. Presence is an end to end platform. A large share of real enterprise deployments are cascaded, with the speech layer from one vendor and the model from another, and an end to end product does not assess those at all. We are neutral to the whole stack, and a cascaded setup is actually easier for us to instrument because the seams are already there.

---- "WHAT ABOUT OBSERVE.AI OR THE OTHER CONVERSATION INTELLIGENCE TOOLS?" ----

They are good at what they do and they do get to full coverage, which is more than manual QA manages. But they are analysing production calls after the fact and scoring against rubrics somebody wrote.

We are pre deployment, and we adjudicate against the client's actual regulation with the provision cited. Different question, different point in the lifecycle. Honestly they are complements more than competitors.

---- "WHY NOT JUST HAVE THE MODEL VENDOR BUILD THIS IN?" ----

Because you do not want the company supplying the agent to also be the company signing off that it is safe. That is a structural conflict, and every other regulated industry separates those two roles.

---- "HOW DOES THIS HANDLE A RULEBOOK WE HAVE NOT SEEN?" ----

The rulebook is an input. It goes in as a data pack, chunked at section level with the real identifiers. We proved the boundary by swapping the corpus for a completely different industry's standard, with a different numbering convention, and no engine code changed.

---- "WHAT ABOUT OPEN SOURCE, OR RUNNING THIS ON OPEN WEIGHTS MODELS?" ----

There is a real thread there. The interface is one OpenAI compatible endpoint, so any model behind a compatible endpoint works, including open weights ones running in a client's own environment. For a bank that cannot send transcripts to a third party, that matters a lot.

And it lines up with where governance is heading. The reason people care about published training lineage on models like DeepSeek is traceability, being able to say where an answer came from. That is exactly the argument we make one layer up. Model lineage tells you where the weights came from. Our evidence chain tells you where the decision came from. A regulator asks the second question far more often than the first.

---- "WHAT DOES IT COST TO RUN AT VOLUME?" ----

Model spend is not the constraint. Our measured campaign was well under a dollar, and it projects to about twenty three dollars per hundred calls at realistic call lengths.

The real cost is compute on the reranker, which is a hardware line item and not a research problem, and the thing you are trading against is reviewer hours.

---- "WHAT IS THE HARDEST UNSOLVED PROBLEM IN IT?" ----

Compound obligations. A rule that requires two things in one sentence gets split into two claims, and each half gets judged against the whole rule, so text that actually complies can be marked as violating.

That is structural rather than tuning. Claims are the unit of adjudication and obligations are not always claim shaped. Fixing it means evaluating multi element obligations at turn level, and that is not built.
