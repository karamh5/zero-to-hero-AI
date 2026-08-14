# Ten minutes, business audience

## Before you start

[open a terminal in the EchoProof folder]

[run .venv/Scripts/python scripts/run_ui.py]

[open http://127.0.0.1:8077/rig in tab one]

[under 02 / select conversation, group supported, click 04 validation notice contents described]

[type warm up in the assessment title box, click run adjudication, let it finish]

[open presentation/demo-day/deck.html in tab two, press f for fullscreen]

[open http://127.0.0.1:8077/bench in tab three and check the top card reads third party disclosure - demo baseline]

## The exposure

[deck on slide one]

Every enterprise putting a voice agent into a regulated conversation is carrying the same unpriced risk. They do not know which of the things it says are going to cost them.

And the way they find out is a regulator, or a plaintiff.

[click twice, the claim marks and the chain draw]

EchoProof answers that question before the agent is ever pointed at a customer.

## What the risk actually looks like

[click to the next slide]

Here is a real agent turn from a collections call. It sounds like the agent is being helpful.

[click, the rule appears on the paper card]

It is a federal violation. You may not discuss a person's debt with somebody who is not them, and the agent was speaking to her brother.

That is statutory damages per violation, and these agents do not make a mistake once. They make it consistently, on every call that hits the same conversational pattern, until somebody notices.

[click, the line underneath appears]

Which is the part that makes it expensive. It is not a bug and not a wrong answer, so every test the engineering team runs says the agent is working correctly. There is nothing to notice.

## What actually stalls the deployment

[stay on this slide and stop clicking]

I want to name the commercial problem underneath this, because it is not really the fine.

It is that legal will not sign off. Somebody has to put their name on the statement that this agent is safe to talk to customers, and right now nobody can, because nobody can see what it says at scale.

So the deployment sits in review. The pilot runs for another quarter. The rollout that was supposed to take six weeks takes nine months, and the cost is the value of the deployment you did not get, every month you did not get it.

And what does exist today does not solve it. A person listening to recordings with a rulebook next to them, sampling a fraction of calls, weeks after launch, producing a spreadsheet of opinions with no rule attached to any of them.

You cannot sign off on a sample. If your general counsel is asked to put their name on a deployment and the evidence is that a handful of calls looked acceptable to an analyst, they will not sign, and they are right not to.

So the deployment does not fail. It never quite starts, and the thing missing is not effort. It is coverage and evidence.

## What it does about it

[click to the next slide]

[click, the read box appears]

So here is what it does instead. It reads every turn the agent produced, and only the agent's turns.

[click, the claim box appears]

It pulls out the specific things the agent claimed, word for word.

[click, the retrieve box appears]

It finds the rule in your rulebook that governs each one.

[click, the rule and seal box appears]

And it rules on it and seals the record. So every flag arrives with the exact rule it broke, quoted, which means your compliance officer is reviewing a citation instead of forming an opinion.

And the sealed part matters just as much. When somebody asks in eighteen months how you knew the agent was safe, there is an answer that does not depend on anybody's memory.

That last one changes the conversation with legal. The question they are actually being asked is not whether the agent is perfect. It is whether the company exercised diligence, and whether that can be demonstrated afterwards.

A sampled spreadsheet demonstrates nothing. A record of every turn, each flagged item carrying the provision it engaged, provably unedited since it was written, is a different kind of object entirely.

## What it changes about the review

[no slide change, keep talking over the same slide]

Which changes what your compliance team spends its time on.

Today they are searching. They listen to calls hunting for something worth flagging, and most of what they listen to is fine, so most of that time produces nothing.

With this they are adjudicating. The list is already assembled and every item on it arrives with the governing rule attached, so the question in front of them is a judgement call rather than a search. That is the work you actually hired them for.

And every decision they make lands in the same sealed record, so the review itself becomes part of the evidence rather than a separate spreadsheet nobody can find later.

## What it costs you to adopt

[press 9 to jump to the stack slide]

[click, the first stack draws]

Before the commercial question, the integration question, because this is usually where a compliance tool dies.

This is what a voice agent looks like. Telephony, speech to text, the thing that decides what to say, the model that writes it, and speech back out.

[click, echoproof appears in the chain]

We attach at one point. It is a configuration change in front of the model, and nothing else in that chain moves.

[click, the return path and the side branch appear]

And we do not sit in the middle of your call. The reply goes back untouched and is never held up. The checking runs off to the side, after the customer already has their answer.

[click, the second stack appears]

Swap out every vendor in that diagram and the attachment point is the same. So this is not a bet on your current stack staying still.

## Whose standard it is

[click to the next slide]

[click, the cartridges seat into the core]

This is the part that matters for how it fits your organisation. The engine has no industry knowledge in it.

A client brings four things. Their rulebook. The situations they care about. The customer types to test against. And their own thresholds for what is serious enough to stop a release.

That last one is the important one. We do not tell you what blocks a deployment. You tell us, and we compute against your rule.

[click, the policy cartridge swaps]

Which is also why this is not a debt collection product. Swap the rulebook and the same system runs a telecom standard, with no engineering work.

[click, the industries appear]

Collections, insurance, healthcare, telecom, financial services. Anywhere a regulated conversation is being automated.

And commercially that is the thesis. The expensive part of a compliance product is normally that every client is a rebuild. Here the rules are the input rather than the implementation, so a new sector is a data exercise.

## What is real

[click to the next slide]

[click, the today column appears]

I want to be honest about the line between what exists and what is designed.

Everything I am about to show you is real and runs today. Real assessments, real evidence on disk.

[click, the production column appears]

The production version is designed and not built. Enterprise model hosting, cloud storage with retention locks, the throughput work to run this at volume.

[click, the configuration line appears]

The important commercial fact is that the gap between those two columns is configuration rather than a rewrite. That was decided on day one, and it is why this is a deployment question rather than a rebuild.

## The walkthrough

[alt tab to the browser, tab three, the bench]

Let me show you the actual thing.

Every assessment that has been run, each one sealed and re-verified when the page loads.

[click the top card, third party disclosure - demo baseline]

This is the conversation from earlier.

[point at gate decision at the top]

Block release, at the top. That is computed from the client's own thresholds. They said one serious finding is enough to stop a deployment, so this agent does not ship.

Your compliance team sets that number. It is their policy, running automatically.

[point at the abstentions section]

And these are the ones it declined to rule on, kept separate from the findings and routed to a person. It does not guess in order to look decisive.

[scroll to findings and click the first one]

[point at what was said]

The sentence the agent said, exactly.

[point at the cream coloured card]

And the rule, printed the way the regulation prints it. Your reviewer is not being asked to trust a machine. They are being handed the citation and asked to agree or disagree.

That is the difference between a tool your compliance officer resents and one they use. A system that says trust me gets ignored the first time it is wrong. A system that shows its source gets corrected and kept.

[scroll down to the evidence trace]

And underneath, the full record of how it got there, sealed so that it visibly breaks if anyone edits it.

That is the artifact you hand a regulator.

[stop scrolling and look at the room]

## Close

[alt tab back to the deck]

[press end to jump to the last slide]

[click three times, the lines and the ask appear]

Every claim has a source. Every verdict has a rule. Every finding has evidence.

What I am looking for is an introduction to somebody who signs off that a voice agent can go live, because I want to find out what that person would actually pay for.

## If something goes wrong

### The bench will not load

[check the terminal is still running run_ui.py]

[reload the page]

If it does not come back, go to the deck and close from there. Say this.

That is a live system on this laptop and I would rather show you it working properly than fight it now. I will send you a walkthrough after this.

## Questions you will get

### "What does this cost to run?"

Model spend is not the constraint at any volume I have measured. The constraint is reviewer time, and that is exactly what this is aimed at.

I have not set pricing, because I have not validated it with a buyer. I would rather tell you that than invent a number in front of you.

### "Who owns this internally, compliance or engineering?"

Compliance owns the output and engineering owns the integration, which is usually a one line configuration change.

The budget tends to sit with whoever owns the deployment, because the thing being bought is the deployment happening on time.

### "How long does it take to onboard us?"

The real work is turning your rulebook into something addressable section by section. If your compliance team already maintains a structured policy document, that is fast. If it is a folder of PDFs, that is a project.

I would want to measure how well it retrieves against your corpus before I gave you a date, because a private rulebook is a harder problem than a public regulation and I would rather find that out with you than promise around it.

### "Does it replace our compliance reviewers?"

No, and I would not sell it that way. It reads every turn, which no human process does, and it hands your reviewer a short list where each item already has the governing rule attached.

The gain is that their time goes into judgement rather than into listening to recordings looking for something to judge.

### "What happens when it gets something wrong?"

Two kinds of wrong, and they are not equally bad. It can stay quiet about something real, which is why this is a layer in front of a human rather than a replacement for one.

Or it can flag something that is fine, which is the one that destroys reviewer trust, and it is the failure mode we tuned hardest against. If your reviewers stop believing the flags, the product is worthless regardless of what it catches.

### "Why would we not just wait for the model vendors to build this?"

Because the thing being checked is your rulebook, not a general notion of the law, and the record has to be yours. A vendor building a general compliance filter is building for the average of every regulation, and you are not average.

There is also a structural reason. You do not want the company that supplies the agent to also be the company that signs off that it is safe. Those should be different parties.
