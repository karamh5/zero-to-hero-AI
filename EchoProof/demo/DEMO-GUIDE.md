# Running the demo

Everything here is rehearsable. The prepared conversations are real stored
test artifacts that have been run through the real pipeline, and the outcomes
below are what they actually produced, not what they were written to produce.

## Before the room arrives

```bash
python scripts/run_ui.py            # serves the UI and API on :8077
```

Open `/rig` once and run any conversation to warm the stack. The first run of
a session loads the embedding and reranker weights, roughly 20 seconds warm,
and you do not want that happening on stage. After that the weights stay
resident.

Check `/bench` shows the assessments you expect and that every entry reads
`chain verified`.

## The path through the product

**1. Home.** The corpus is the object in the middle. Three statements carry
the argument: every claim has a source, every verdict has a rule, every
finding has evidence.

**2. Rig.** Choose Regulation F, choose a conversation, give the assessment a
title, run it. The source conversation is shown in full before it runs, with
consumer turns marked `context only`. Say that out loud: **only the agent is
being assessed.** The consumer's words are used to judge whether the agent
responded correctly, and never receive a verdict themselves.

A turn takes 105 seconds median. While it runs, the stage log prints real
pipeline events and the core changes state as they arrive. There is no
progress bar because there is nothing honest to put in one.

**3. Bench.** The assessment appears under the title you gave it, with its
own number.

**4. Case file.** This is where the argument lands. The claim highlighted in
what the agent said, the governing rule quoted verbatim beside it, and an
eight step evidence trace. Open the retrieval step: every candidate the judge
was offered, placed by its retrieval score, with the selected rule largest.

**5. Corpus.** The rulebook itself, and which provisions retrieval reached.

## Which conversations to run

Every conversation below has been run through the real pipeline and produces
the outcome shown. The rig groups them by that recorded outcome, so what you
see in the list is what you will get.

**Contradicted, cites the right paragraph:**

| Conversation | Cites |
|---|---|
| Debt disclosed to a third party | `1006.6(d)(1)` |
| Suit threatened on a time-barred debt | `1006.26(b)` |
| Furnished to a credit bureau before contact | `1006.30(a)(1)` |

**Supported:**

| Conversation |
|---|
| Required initial disclosure |
| Written contact by postcard |
| Call placed inside permitted hours |
| Validation notice contents described |

The third party conversation is the strongest single demonstration: the
violation is immediately understandable to a non specialist without
explaining a statute, and it cites the section the scenario is about.

Pair one contradicted conversation with one supported conversation. A tool
that only ever finds problems is not obviously better than a tool that flags
everything, and the supported case is what shows it stays quiet when the
agent is doing its job.

## The abstention examples

Five conversations produce `retrieval_below_confidence`: cease contact
continued, attorney representation ignored, payment pressed during an open
dispute, and two written to be outside the rulebook entirely. They sit in the
library under that heading and are worth running deliberately if the room
asks what happens when the system is unsure.

The line to use: retrieval did not surface a governing provision with enough
confidence to adjudicate, so the system declined rather than guessed, and the
claim routes to human review. Declining is a designed outcome, not a failure
to produce one.

Do not present them as demonstrations of a caught violation. The three
collections ones were written to be violations and are not detected as such,
which matches the campaign, where those same scenario types were the misses.

## Two verdict states have no demonstration

**`no_governing_rule` cannot currently be produced.** Measured across the
whole prepared library, 71 retrieval calls, the lowest top-1 score was 0.5009
against a floor of 0.4937, so nothing ever falls below the floor. A
conversation deliberately written about clock towers and stained glass still
scored 0.50. This is why the policy gap list is empty on every run. Do not
promise this state in a demo, and if asked, say the floor is calibrated below
the reranker's practical output range and recalibrating it is open work.

**`conflicting_sections` is not demonstrated on purpose.** It is the least
reliable of the five states and there is no conversation that produces it
dependably.

## If something goes wrong

**The rig will not start a run.** Check `MISTRAL_API_KEY` is in `.env`. The
rig reports its own disabled state and the rest of the product still works.

**A run is slower than expected.** Nothing else should be running against the
model at the same time. Two processes competing roughly doubles wall clock.

**The stream disconnects.** The job continues on the server. Reload and open
the assessment from the bench; the evidence is written either way.

**Someone asks to type their own conversation.** The rig does not accept free
text, and that is a deliberate answer, not a missing feature: without speaker
labels there is no way to guarantee that only the agent's turns are assessed.
Offer to add their scenario to the library and run it before the next
session.
