# 5 min Demo

## Before you start

[run .venv/Scripts/python scripts/run_ui.py]

[open http://127.0.0.1:8077/rig in tab one]

[under 02 / select conversation, group supported, click 04 validation notice contents described]

[type warm up in the assessment title box, click run adjudication, let it finish]

[open presentation/tomorrow/deck.html in tab two, press f for fullscreen]

[open http://127.0.0.1:8077/bench in tab three, check the top card reads third party disclosure - demo baseline]

## Presentation

[slide 1: click 2x]

Companies are putting AI voice agents into conversations governed by law. Debt collection, insurance, healthcare.

The agent sounds great. It is polite, it is fast, but it has no idea which of the things it says are actually legal.

EchoProof checks that before the voice agent is ever deployed to a customer.

And the easiest way to show you what I mean is to show you one of these agents getting it wrong.

## The problem

[slide 2: click 1x]

Here is a real thing a collections agent said on a call. This is an instance where the agent is telling somebody about another person's debt.

[click 2x]

And it is against federal law, because you cannot tell somebody else about another person's debt. No matter how closely related to them you are.

Nothing that exists in a normal voice agent stack catches this. It is not a bug and it is not a wrong answer, so every test you would run says this agent is working perfectly.

Which brings me to my next point.

## Why nothing catches it today

[slide 3: click 1x]

Three main reasons.

[click 1x]

Checking this today means a person listening to recordings with the rulebook open next to them. There are thousands of calls. They only get through a handful.

[click 1x]

It also happens weeks after the agent is already live and already talking to real customers.

[click 1x]

And what you get at the end is a spreadsheet of the QA team's opinion with no rule attached. If you want to know why a call was marked bad, you go and ask them.

So sampled, late, and unciteable. Here is what replaces all three.

## What you get instead

[slide 4: click 1x]

[click 3x]

Every single thing the agent said gets checked, not a sample, and it happens before launch instead of weeks after.

When something is flagged, the exact rule it broke comes attached to it, quoted word for word.

And all of it goes into a sealed record you could hand to a regulator or compliance team, where you can prove afterwards that nothing was edited.

Which raises the obvious question of how it actually does that.

## What it does

[slide 5: click 1x]

Four steps.

[click 1x]

One. It reads what the agent said. Only the agent. What the customer said is context, and the customer never gets judged. Rather, it assesses only the agent to see whether or not it escalates to human agents when necessary and does not provide responses that are not compliant.

[click 1x]

Two. It finds the rule that governs that specific sentence, in the client's own rulebook. Not a general idea of the law, their actual document. Which is essential when it comes to traceability.

[click 1x]

Three. It rules on it, using only that one rule. It is not allowed to use anything it happens to know from training.

[click 1x]

Four. It attaches the evidence. The sentence, the rule, the reasoning, and a clip of the audio where the agent said it.

Now, where does all of that sit relative to the agent itself.

## Where it plugs in

[slide 6: click 1x]

[click 1x]

A voice agent is a chain. The customer speaks, that becomes text, something decides what to say next, and a model writes the reply.

[click 1x]

EchoProof sits at exactly one point in front of the model. You change one setting to point at us, and nothing else in the stack changes.

[click 1x]

And the reply goes straight back, untouched. We are not in the middle of the call slowing it down. The checking happens off to the side as a third party spectator to avoid disrupting the process.

[click 1x]

Every claim has a source. Every verdict has a rule. Every finding has evidence. Which is a principle EchoProof lives by.

And being a third party is the whole point, which brings me to who else is in this space.

## The landscape

[slide 7: click 1x]

[click 1x]

The closest thing is OpenAI's Presence, and it is end to end. Same vendor supplies the voice, the model, and the readiness answer, so what you get back is a self check rather than an independent one.

It also does not cover cascaded setups, where the speech layer and the model come from different vendors.

[click 1x]

EchoProof is designed to be neutral to that, and a cascaded stack is actually easier for us to instrument. Same story with the new DeepSeek harness.

[click 1x]

And the engine itself has nothing about debt collection in it. We swapped the rulebook out for a completely different industry's standard and did not change any code.

Which is easier to show than to describe, so let me open the real thing.

## The walkthrough

[alt tab to the browser, tab three, the bench]

This is every assessment that has been run. Each says chain verified, meaning it was checked for tampering just now, on load.

[click the top card, third party disclosure - demo baseline]

This is the conversation from that slide.

[point at block release at the top]

At the top it says block release. The client tells us what blocks a release, and their rule was that one serious finding is enough.

[point at abstentions]

Down here are the ones it was not sure about, kept separate from the findings, because a maybe is not a catch.

[scroll to findings and click the first one]

[point at what was said]

This is what the agent said, pulled straight out of the transcript, word for word.

[point at the cream coloured card]

And this is the rule, printed exactly as it is written in the regulation. You do not have to trust the verdict. The rule is right there next to it.

[scroll down to the evidence trace]

And underneath is every step of how it got there. What it searched, every rule it considered, which one it picked, and a seal that breaks visibly if anyone edits any of it.

[stop scrolling and look at the room]

A source, a rule, and evidence. That is EchoProof.

Happy to take questions.

## If something goes wrong

### The bench will not load

[check the terminal is still running run_ui.py]

[reload the page]

If it does not come back, stay in the deck and finish on the last slide. Say this.

The demo runs against a real system on this laptop and I would rather show you it working properly than fight it now. Grab me after and I will run it for you.

### A page looks wrong or half rendered

[hard reload with control shift r]

Keep talking while it reloads. Do not narrate the reload.

## Questions you will get

### "How is this different from just asking ChatGPT if the call was okay?"

Because you cannot check the answer. It would be answering from memory of a law it might have read once, and you would have no way of knowing which version or whether it made it up.

Ours never gets to browse. It gets handed one rule and it has to answer from that rule, and then we print the rule next to the answer. If it is wrong, you can see that it is wrong in about five seconds.

### "Does this slow the call down?"

No, and that was deliberate. The reply goes back to the customer untouched and we never hold it up. All the checking happens afterwards, off to the side.

And the main way you would use this is before the agent is live at all. You run your agent against a set of test conversations, you see what it says wrong, you fix it, and then you deploy.

### "Why would OpenAI not just build this in?"

They partly have, and that is the Presence point. But the buyer here is the person signing off that the agent can go live, and you do not want the company supplying the agent to also be the company grading it.

The other half is cascaded stacks. If your speech layer and your model come from different vendors, an end to end product does not cover you, and that is a large share of real deployments.

### "What would you need from a company to run this on their agent?"

Their rulebook, in a form we can read section by section. The situations they care about. And their own threshold for what is serious enough to stop a release, because that decision should be theirs and not ours.

The engine itself has nothing about debt collection in it. We swapped the rulebook out for a completely different industry's standard and did not change any code.

### "What is the hardest part still?"

Finding every violation. It is much better at being right about the ones it does flag than it is at flagging all of them, so the way to think about it is that it hands a reviewer a short list with the rules already attached, rather than replacing the reviewer.

That is the part I would work on next.
