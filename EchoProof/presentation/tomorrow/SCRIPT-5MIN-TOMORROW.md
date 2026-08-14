# Five minutes, AI Launchpad

## Before you start

[open a terminal in the EchoProof folder]

[run .venv/Scripts/python scripts/run_ui.py]

[open http://127.0.0.1:8077/rig in tab one]

[under 02 / select conversation, group supported, click 04 validation notice contents described]

[type warm up in the assessment title box, click run adjudication, let it finish]

[open presentation/tomorrow/deck.html in tab two, press f for fullscreen]

[open http://127.0.0.1:8077/bench in tab three and check the top card reads third party disclosure - demo baseline]

[press n twice in the deck to check presenter notes open and close]

## The idea

[deck on slide one]

Companies are putting AI voice agents into conversations governed by law. Debt collection, insurance, healthcare.

The agent sounds great. It is polite, it is fast, and it has no idea which of the things it says are actually legal.

[click twice, the marks and the chain draw]

EchoProof checks that before the agent is ever put in front of a customer.

## The problem

[click to the next slide]

Here is a real thing a collections agent said on a call. Read it. It sounds helpful, like good customer service.

[click, the rule appears on the right]

And it is against federal law, because you cannot tell somebody else about another person's debt. The agent was talking to her brother.

[click, the line underneath appears]

Here is the uncomfortable part. Nothing in a normal build process catches this. It is not a bug and it is not a wrong answer, so every test you would run says this agent is working perfectly.

## Why nothing catches it today

[click to the next slide]

Three reasons, and they stack up.

[click, the first panel appears]

Checking this today means a person listening to recordings with the rulebook open next to them. There are thousands of calls. They get through a handful.

[click, the second panel appears]

It also happens weeks after the agent is already live and already talking to real customers.

[click, the third panel appears]

And what you get at the end is a spreadsheet of somebody's opinion with no rule attached. If you want to know why a call was marked bad, you go and ask them.

## What you get instead

[click to the next slide]

[click three times, the three panels appear one at a time]

Every single thing the agent said gets checked, not a sample, and it happens before launch instead of weeks after.

When something is flagged, the exact rule it broke comes attached to it, quoted word for word.

And all of it goes into a sealed record you could hand to a regulator, where you can prove afterwards that nothing was edited.

## What it does

[click to the next slide]

Four steps.

[click, the first box appears]

One. It reads what the agent said. Only the agent. What the customer said is context, and the customer never gets judged.

[click, the second box appears]

Two. It finds the rule that governs that specific sentence, in the client's own rulebook. Not a general idea of the law, their actual document.

[click, the third box appears]

Three. It rules on it, using only that one rule. It is not allowed to use anything it happens to know from training.

[click, the fourth box appears]

Four. It attaches the evidence. The sentence, the rule, the reasoning, and a clip of the audio where the agent said it.

## Where it plugs in

[click to the next slide]

[click, the chain appears]

A voice agent is a chain. The customer speaks, that becomes text, something decides what to say next, and a model writes the reply.

[click, echoproof appears in the chain]

EchoProof sits at exactly one point, in front of the model. You change one setting to point at us, and nothing else in the stack changes.

[click, the return path and the side branch appear]

And the reply goes straight back, untouched. We are not in the middle of the call slowing it down. The checking happens off to the side, after the customer already has their answer.

[click, the three line statement appears]

Every claim has a source. Every verdict has a rule. Every finding has evidence.

## The walkthrough

[alt tab to the browser, tab three, the bench]

So let me show you the real thing.

This is every assessment that has been run. Each says chain verified, meaning it was checked for tampering just now, on load.

[click the top card, third party disclosure - demo baseline]

This is the conversation from that slide.

[point at block release at the top]

At the top it says block release. That is not our opinion. The client tells us what blocks a release, and their rule was that one serious finding is enough.

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

### "What would you need from a company to run this on their agent?"

Their rulebook, in a form we can read section by section. The situations they care about. And their own threshold for what is serious enough to stop a release, because that decision should be theirs and not ours.

The engine itself has nothing about debt collection in it. We swapped the rulebook out for a completely different industry's standard and did not change any code.

### "What is the hardest part still?"

Finding every violation. It is much better at being right about the ones it does flag than it is at flagging all of them, so the way to think about it is that it hands a reviewer a short list with the rules already attached, rather than replacing the reviewer.

That is the part I would work on next.
