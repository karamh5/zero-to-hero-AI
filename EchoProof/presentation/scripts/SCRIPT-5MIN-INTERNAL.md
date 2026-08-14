# Five minutes, internal

## Before you start

[open a terminal in the EchoProof folder]

[run .venv/Scripts/python scripts/run_ui.py]

[open http://127.0.0.1:8077/rig in tab one]

[under 02 / select conversation, group supported, click 04 validation notice contents described]

[type warm up in the assessment title box, click run adjudication, let it finish]

[open presentation/tomorrow/deck.html in tab two, press f for fullscreen]

[open http://127.0.0.1:8077/bench in tab three and check the top card reads third party disclosure - demo baseline]

## What this is

[deck on slide one]

There is a wave of companies putting AI voice agents into conversations that are legally regulated. Chasing a debt, handling a claim, booking a medical appointment.

The agent is fluent and confident and it does not know which of the sentences coming out of it are allowed.

[click twice, the marks and the chain draw]

EchoProof is the thing that checks, before the agent is ever pointed at a real customer.

## The problem

[click to the next slide]

This is a real sentence from a collections agent. It reads like good service.

[click, the rule appears on the right]

It is also illegal. You cannot discuss somebody's debt with a person who is not them, and the agent was speaking to her brother.

[click, the line underneath appears]

And this is the shape of the whole problem. It is not a bug, it is not a crash, and it is not a wrong fact. Every test a normal team runs marks this response as good.

## Why it survives to production

[click to the next slide]

[click, the first panel appears]

The way this gets checked today is a person listening to recordings with a rulebook next to them. There are thousands of calls and they hear a few dozen.

[click, the second panel appears]

That review lands weeks after launch, so whatever the agent is doing wrong, it has been doing it to real people the whole time.

[click, the third panel appears]

And the output is a judgement with nothing behind it. A call marked bad, and no rule attached saying which one and why. Which means nobody downstream can act on it without going back and asking the reviewer what they meant.

## What you get instead

[click to the next slide]

[click three times, the three panels appear one at a time]

Every turn the agent produced gets checked, not a sample of them, and it happens while the agent is still in staging.

Anything flagged arrives with the rule that governs it, quoted exactly.

And the whole thing lands in a sealed record, so months later you can prove what was decided and that nobody changed it.

## How it works

[click to the next slide]

[click, the first box appears]

It reads what the agent said, and only what the agent said. The customer's turns are context and are never given a verdict.

[click, the second box appears]

It finds the rule that governs that particular sentence, inside the client's own rulebook rather than some general notion of the law.

[click, the third box appears]

It rules on it using only that one rule. It is not permitted to fall back on anything it picked up in training.

[click, the fourth box appears]

And it attaches the evidence: the sentence, the rule, the reasoning, and the audio of the moment it was said.

## Where it connects

[click to the next slide]

[click, the chain appears]

A voice agent is a chain. Speech becomes text, something decides what to say, a model writes it, and it becomes speech again.

[click, echoproof appears in the chain]

We attach at one point, in front of the model. It is a setting change, and nothing else in the stack moves.

[click, the return path and the side branch appear]

The reply goes back untouched and it is never held up. The checking runs off to the side once the customer already has their answer.

[click, the three line statement appears]

Every claim has a source. Every verdict has a rule. Every finding has evidence.

## The walkthrough

[alt tab to the browser, tab three, the bench]

Here it is running.

Every assessment ever produced, each one sealed, each one saying chain verified because it was re-checked on load.

[click the top card, third party disclosure - demo baseline]

This is the conversation from the slide.

[point at block release at the top]

Block release, at the top. That threshold belongs to the client. They decide what is serious enough to stop a deployment, and we compute against their rule.

[point at abstentions]

And these are the ones it declined to call, listed apart from the findings, because something it was unsure about is not something it caught.

[scroll to findings and click the first one]

[point at what was said]

The sentence, lifted out of the transcript exactly as spoken.

[point at the cream coloured card]

The rule, printed the way the regulation prints it. You are not being asked to trust a verdict, you are being shown the thing it rests on.

[scroll down to the evidence trace]

And every step of the reasoning underneath: what it searched, what it considered, what it chose, and a seal that breaks if a single character of it is altered.

[stop scrolling and look at the room]

A source, a rule, and evidence. That is the whole idea.

## If something goes wrong

### The bench will not load

[check the terminal is still running run_ui.py]

[reload the page]

If it does not recover, close the browser and finish from the last slide. Say this.

That runs against a live system on this laptop and I would rather show it working than debug it in front of you. Find me afterwards and I will walk you through it properly.

### A screen renders half way

[hard reload with control shift r]

Keep talking through the reload. Do not narrate it.

## Questions you will get

### "Why not just ask a model whether the call was compliant?"

Because you cannot audit the answer. It would be recalling a regulation it may have seen at some unknown version, and there is nothing to check it against.

Ours is handed one rule and has to answer from that rule alone, and then we print the rule beside the answer. Anyone can disagree with it in five seconds, which is the entire point.

### "Does it slow the call down?"

No. The reply goes back to the customer untouched and we never delay it. The checking happens afterwards, off the hot path.

And the main use is before anything is live at all. Run the agent against your test conversations, see what it says wrong, fix it, then deploy.

### "What does a company have to give you?"

Their rulebook, structured so we can address it section by section. The scenarios they care about. The customer types to play against the agent. And their own threshold for what stops a release.

The engine holds nothing about any particular industry. We swapped the rulebook for a completely different sector's standard and changed no code at all.

### "Where does it struggle?"

Catching everything. It is considerably better at being right about what it flags than it is at flagging everything it should, so the honest way to use it is as a way of handing a reviewer a short list with the rules already attached.

That gap is the thing I would work on next.
