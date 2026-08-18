# Business and partnership, 10 minutes

Uses the demo deck, slides 1, 2, 3, 4, 11, 12, 13, 14 and 16. Lead with the
commercial problem. The architecture is evidence, not subject matter.

## Before you start

[run .venv/Scripts/python scripts/run_ui.py]

[open http://127.0.0.1:8077/rig in tab one]

[under 02 / select conversation, group supported, click 04 validation notice contents described]

[type warm up in the assessment title box, click run adjudication, let it finish]

[open presentation/demo-day/deck.html in tab two, press f for fullscreen]

[open http://127.0.0.1:8077/bench in tab three, check the top card reads third party disclosure - demo baseline]

## Opening

[slide 1: click 2x]

Before this was a product it was my job. I worked in compliance at TELUS, and what you learn quickly is that compliance is not about knowing the rules. It is about proof. You can be entirely right and still lose, because you could not show your work.

That matters commercially more than it sounds, and here is why.

## What is actually stalling deployments

[slide 2: click 1x]

[click 2x]

Every enterprise putting a voice agent into a regulated conversation has the same problem. The model is ready. The integration is ready. The business case is signed. And then it sits.

Because somebody has to put their name on a document saying this agent is safe to talk to customers, and they cannot see what it says at scale.

[click 1x]

So the deployment does not fail. It just never quite starts. The pilot runs another quarter. The rollout that was six weeks becomes nine months, and the cost is the value of the deployment you did not get, every month you did not get it.

## Why the current answer does not unblock it

[slide 3: click 1x]

[click 2x]

Because what exists today is a person listening to recordings with a rulebook next to them, covering somewhere between one and five percent of calls. And that is arithmetic, not effort, because a trained analyst gets through ten to fifteen a day.

You cannot sign off on a sample. If your general counsel is asked to put their name on a deployment and the evidence is that a handful of calls looked fine to an analyst, they will not sign, and they are right not to.

[click 1x]

This is a manual process, and we automate it. Every turn, before launch, with the governing rule attached to every flag, and a sealed record at the end.

## What that changes

[slide 4: click 1x]

[click 4x]

Four steps, and the two that matter commercially are the last two. It finds the actual provision in your rulebook that governs a sentence, decides using only that provision, then prints it next to the verdict.

Which means your compliance officer is reviewing a citation instead of forming an opinion. That is the difference between a tool they resent and one they use.

And it means when somebody asks in eighteen months how you knew the agent was safe, there is an answer that does not depend on anybody's memory.

## Where it sits

[slide 11: press 1 1 and enter]

[click 1x]

The client brings the regulation, their policy, and their own threshold for what is serious enough to stop a release.

[click 1x]

Hexaware brings the agent build, the CX operations, the delivery centres.

[click 1x]

EchoProof sits in exactly one place. Between the build and the sign off. It is a configuration change, not a re architecture, and nothing else in the stack moves.

[click 1x]

And what comes out is the handover artifact. Not an assurance that the agent was tested. An evidence file showing what was tested and against which rule, that the client can hand to their own regulator.

## Go to market

[slide 12: click 1x]

[click 1x]

Three routes, and all of them are motions Hexaware already runs. First, it attaches to CX engagements already being won, as the assurance line item. Shortest path, no new buyer.

[click 1x]

Second, it opens a new motion, which is auditing agents somebody else built. Being vendor neutral means Hexaware can assess a stack it did not deliver. New logos, no build risk.

[click 1x]

Third, it recurs. The rulebook is an input, so when the regulation moves the assessment re runs. That is recurring revenue rather than a one off.

[click 1x]

And the strategic one is the middle route, for a specific reason I will come to.

## The market

[slide 13: click 1x]

[click 1x]

The voice AI agent market is around three and a half billion dollars this year and heading toward thirty five billion by 2033. Every one of those deployments is a governance sign off waiting to happen, and the ones in regulated industries cannot ship without it.

[click 1x]

On cost, our measured campaign was eighty two cents of model spend for eighteen calls, projecting to roughly twenty three dollars per hundred calls. Model spend is not the constraint. Reviewer time is, and that is what this is aimed at.

## Who else is in this

[slide 14: click 1x]

[click 2x]

Two axes. Before or after deployment, and independent or the vendor checking itself.

Conversation intelligence, Observe.AI and Modulate, get to full coverage on production calls. Genuinely useful, but it is after the call and it is scoring against rubrics somebody wrote.

[click 1x]

The closest thing to us is OpenAI Presence, which launched in July. Strong product, evals and graders built in. But it is end to end, so the vendor supplying the agent is also the vendor grading it, and that is a structural conflict every other regulated industry separates. It also does not cover cascaded stacks at all.

[click 1x]

Which leaves this quadrant empty, and here is the strategic point. OpenAI is shipping Presence through select global systems integrators. Being able to say we assure any agent, not only the ones built on one vendor, is the differentiator in exactly that conversation.

## The walkthrough

[alt tab to the browser, tab three, the bench]

Let me show you the artifact itself, quickly.

[click the top card, third party disclosure - demo baseline]

[point at the gate decision block at the top]

Block release, at the top. That threshold belongs to the client. They decide what stops a deployment and we compute against their rule.

[scroll to findings and click the first finding]

[point at the cream coloured card]

And every finding carries the rule, printed as the regulation prints it. Your reviewer is being handed a citation and asked to agree or disagree, in seconds.

[scroll down to the evidence trace]

And the full record of how it got there, sealed so it visibly breaks if anyone edits it. That is what you hand a regulator.

[stop scrolling and look at the room]

## Close

[alt tab back to the deck]

[press 1 6 and enter]

[click 2x]

Every claim has a source. Every verdict has a rule. Every finding has evidence.

I have not really been selling a product here. The product is a proxy, a rulebook and a hash chain. What I am selling is that governance is the thing standing between these deployments and revenue, and it is solvable.

So the ask is a live engagement to point this at, and an introduction to whoever signs off that an agent can go live.

## If something goes wrong

### The bench will not load

[check the terminal is still running run_ui.py]

[reload the page]

If it does not recover, close from the deck. Say this.

That is a live system on this laptop and I would rather show it working properly than fight it now. I will send a walkthrough after this.

## Questions you will get

### "What does it cost to run?"

Model spend is not the constraint at any volume I have measured, and it projects to about twenty three dollars per hundred calls. The real cost is compute on the reranker, which is a hardware line item.

I have not set pricing, because I have not validated it with a buyer. I would rather tell you that than invent a number.

### "Who owns this internally, compliance or engineering?"

Compliance owns the output. Engineering owns the integration, which is a configuration change. The budget tends to sit with whoever owns the deployment, because the thing being bought is the deployment happening on time.

### "How long to onboard a client?"

The work is turning their rulebook into something addressable section by section. If their compliance team already maintains a structured policy document, that is fast. If it is a folder of PDFs, that is a project.

I would want to measure retrieval against their corpus before quoting a date, because a private rulebook is a harder problem than a public regulation.

### "Does it replace our compliance reviewers?"

No, and I would not sell it that way. It reads every turn, which no human process does, and it hands your reviewer a short list where each item already has the governing rule attached. Their time goes into judgement instead of into searching.

### "Why would we not wait for the model vendors to build this?"

Because the thing being checked is your rulebook, not a general notion of the law, and the record has to be yours.

And structurally, you do not want the company supplying the agent to also be the company signing off that it is safe. Those should be different parties, and in every other regulated industry they are.

### "What about open source models?"

The interface is one OpenAI compatible endpoint, so any model behind a compatible endpoint works, including open weights models running inside a client's own environment. For a bank that cannot send transcripts to a third party, that matters a lot, and it is a configuration change rather than a port.
