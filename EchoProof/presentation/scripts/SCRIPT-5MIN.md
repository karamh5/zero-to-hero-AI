# Five minutes

Uses the demo deck, slides 1, 2, 3, 4, 11 and 17.

## Before you start

[run .venv/Scripts/python scripts/run_ui.py]

[open http://127.0.0.1:8077/rig in tab one]

[under 02 / select conversation, group supported, click 04 validation notice contents described]

[type warm up in the assessment title box, click run adjudication, let it finish]

[open presentation/demo-day/deck.html in tab two, press f for fullscreen]

[open http://127.0.0.1:8077/bench in tab three, check the top card reads third party disclosure - demo baseline]

## Opening

[slide 1: click 2x]

Before this was a product, it was my job. I worked in compliance at TELUS, and the thing nobody tells you is that compliance is not really about knowing the rules. It is about proof. You can be completely right and still lose, because you could not show your work.

Every enterprise right now is racing to put AI agents into conversations that are legally governed. Collections, insurance, healthcare. And what is holding those launches up is not the model.

## The bottleneck

[slide 2: click 1x]

[click 2x]

It is this. The model is ready, the integration is ready, the business case is signed. And then it stops, because one person has to put their name on a document saying this agent is safe to talk to customers, and they have nothing to base that on.

[click 1x]

The constraint is not capability. It is proof. Which brings me to how that proof gets made today.

## What they do today

[slide 3: click 1x]

[click 2x]

A person, headphones, rulebook open next to them. Manual review covers somewhere between one and five percent of calls, and that is arithmetic rather than laziness, because an analyst gets through ten to fifteen interactions a day.

So most of what your agents say is never examined, it is reviewed weeks after go live, and the output is a score with no rule attached.

[click 1x]

This is a manual process, and EchoProof automates it. Same review, every turn, before launch instead of after, and every flag carries the rule it broke.

## What it does

[slide 4: click 1x]

[click 4x]

Four moves. It reads what the agent said, and only the agent. It pulls the claims out as verbatim quotes. It finds the provision in the client's own rulebook that governs each one. And it rules on it and seals the record.

The important part is the third and fourth. The model doing the ruling never sees the rulebook. It gets handed one provision and has to answer from that text alone, and then we print the provision next to the answer. So you check it rather than trust it.

Which brings me to where that fits.

## Where it sits

[slide 11: press 1 1 and enter]

[click 4x]

The client brings the regulation. The delivery partner brings the agent build and the operations. EchoProof sits in exactly one place, between the build and the sign off.

And what comes out is the artifact. Not an assurance the agent was tested, an evidence file showing what was tested and against which rule, that the client can put in front of their own regulator.

Same layer regardless of client, regulation or vendor stack.

## The walkthrough

[alt tab to the browser, tab three, the bench]

Let me use it the way the person it is built for would.

I am the compliance engineer. A build has been handed to me and I have to decide whether it ships.

[click the top card, third party disclosure - demo baseline]

[point at the gate decision block at the top]

First question, can this ship. Block release. And that is not our threshold, it is computed from the client's own criteria.

[scroll to findings and click the first finding]

[point at what was said]

Second, show me the worst one. This is what the agent said, sliced out of the transcript exactly.

[point at the cream coloured card]

And this is the rule it broke, printed as the regulation prints it.

[scroll down to the evidence trace]

Third, how do I know it is right. Every step is here, and a seal at the end that breaks visibly if anyone edits any of it.

[stop scrolling and look at the room]

That is a compliance review that took two minutes instead of two weeks.

## Close

[alt tab back to the deck]

[press 1 7 and enter]

[click 3x]

Every claim has a source. Every verdict has a rule. Every finding has evidence.

I am not really pitching a product. What I am saying is that governance is the thing standing between these deployments and revenue, and it is solvable.

## If something goes wrong

### The bench will not load

[check the terminal is still running run_ui.py]

[reload the page]

If it does not come back, finish from the deck. Say this.

That runs live on this laptop and I would rather show you it working properly than fight it now. Grab me after.

## Questions you will get

### "How is this different from OpenAI Presence?"

Presence is strong and it does have evals built in. The difference is who holds the pen. It is their model, their guardrails and their grader, so the readiness answer is a self check.

And it is end to end. A lot of real deployments are cascaded, speech from one vendor and the model from another, and an end to end product does not assess those at all.

### "Does it slow the call down?"

No. The reply goes back untouched and is never held up. The checking happens afterwards, off the hot path. And the main use is before anything is live at all.

### "What do you need from a company to run this?"

Their rulebook structured section by section, the scenarios they care about, and their own threshold for what stops a release. The engine has nothing industry specific in it. We swapped the rulebook for a different sector's standard and changed no code.
