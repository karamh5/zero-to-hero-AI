# 10 minute standard

Deck: [../demo-day/deck.html](../demo-day/deck.html), skipping the two slides
marked `OPTIONAL` (slide 7, build order; slide 10, fix and rerun).

**Latency strategy.** One live run, launched at 1:30, on
`Furnished to a credit bureau before contact`, measured at 120.2 seconds warm.
You return at 4:30, which is 180 seconds later, a 60 second margin. The wait is
covered by the architecture, verdict states and packs slides, all of which you
were going to deliver anyway.

**Pre-flight.** Start the server with `.venv/Scripts/python scripts/run_ui.py`,
not bare `python`. Warm the stack with one throwaway run at least ten minutes
before. Full checklist in [../DEMO-RUNBOOK.md](../DEMO-RUNBOOK.md).

| Clock | On screen | Say |
|---|---|---|
| 0:00 | Deck 1 | "Enterprises are putting voice AI agents into conversations that are governed by law. The agent is fluent, confident, and has no idea which of its sentences are legal." |
| 0:15 | Deck 2 | "Here is a real agent turn. Warm, helpful, and prohibited: a collector may not discuss a debt with a third party." |
| 0:45 | Deck 2 | "This is the failure mode no accuracy benchmark looks for. It is not a hallucination and not a wrong fact. It is a lawful sounding sentence that happens to be illegal." |
| 1:15 | Browser, `/rig` | "Let me start one running, and explain while it works." |
| 1:30 | `/rig` | Corpus already reads `SELECTED` on Regulation F. Under `CONTRADICTED`, click `02 FURNISHED TO A CREDIT BUREAU BEFORE CONTACT`. Title it `Credit bureau, live`. **Click `RUN ADJUDICATION →`.** "Customer turns are marked context only. Only the agent is assessed." |
| 1:45 | Deck 3 | "A proxy sits in front of the agent's model call, so the agent does not change. Extract claims, settle in code what code can settle, retrieve the governing rule, then judge." |
| 2:15 | Deck 3, point at the dashed boundary | "This boundary is the argument. The only things crossing into the judge are one claim and the rule text retrieval selected. Not the corpus. Not the model's training knowledge. That is why the verdict is checkable rather than an opinion." |
| 2:45 | Deck 4 | "Five outcomes, never a pass or fail. Two decide, three decline. Declining is a designed result, and abstentions are counted separately everywhere, because reporting a refusal as a detection would flatter the numbers." |
| 3:15 | Deck 4 | "Two of the five are marked honestly. `no_governing_rule` is unreachable today because the retrieval floor sits below what the reranker actually outputs. `conflicting_sections` agreed with a human zero times out of three." |
| 3:35 | Deck 5 | "The commercial argument. The engine has no industry knowledge. A client brings four data packs. We proved it by swapping a 303 provision federal regulation for a 15 provision telecom standard, different identifiers, no engine change. That proves portability, not accuracy." |
| 4:10 | Deck 8 | "Two numbers at opposite ends. The proxy adds a tenth of a millisecond to the live call against a 50 millisecond budget. Adjudication takes about 105 seconds a turn, and retrieval is nearly all of it: two or three searches per claim, fifty candidates reranked on a CPU. Engineering fix, not a research problem." |
| 4:30 | Browser | "And it has finished." Open the assessment from `/bench` if the rig has not already navigated. |
| 4:45 | `/runs/{id}` | "Two findings, both critical. `BLOCK RELEASE` is the client's own threshold: one critical finding blocks. Not our opinion." |
| 5:05 | Case file, `rf-04-creditreport-t00-c00` | "This is what the agent said, quoted exactly. This is the rule, verbatim, 1006.30(a)(1). You do not have to trust the verdict, the paragraph is next to it." |
| 5:35 | Case file, `EVIDENCE TRACE` | "Eight steps. Step 04 is the retrieval field, already open: every candidate the judge was offered, placed by score, the selected one largest. It chose this rule at 0.716." |
| 6:05 | Case file, step 08 | "And it is sealed. Entry N covers entry N minus one, so editing anything in the middle breaks every hash after it." |
| 6:25 | Deck 6 | "That is what the chain looks like intact, and what it looks like when someone edits the middle." |
| 6:50 | Deck 9 | "Now the part that matters most. Everything, including what fails." |
| 7:05 | Deck 9, left side | "Citation precision three quarters to five sixths. Zero false positives on the compliant control across three runs. Every one of 41 chains verifies. Seven adversarial cases, no crashes, and a prompt injection did not flip a verdict." |
| 7:35 | Deck 9, right side | "And: detection between a quarter and a third. Campaign pass rate one scenario in five. Judge to human agreement 0.48 against a floor I set at 0.85 before measuring." |
| 8:05 | Deck 9 | "Three independent measurements point the same way, so the conclusion is the narrow one. This is a triage layer that routes to human review. It is not a release gate, and I will not call it one." |
| 8:30 | Deck 11 | "Everything you saw runs on a laptop. Production is designed and deliberately not built, because building it would have cost the measurements. One model interface throughout, so the Bedrock swap is a base URL and a model string." |
| 9:00 | Deck 12 | "Every claim has a source. Every verdict has a rule. Every finding has evidence. The honest gap is detection. The ask is an introduction to someone who actually buys compliance tooling." |
| 9:30 | | Stop. Take questions. |

## If the run is still going at 4:30

> "Still working. About two minutes a conversation, and the reason is honest:
> several searches per sentence, fifty candidates reranked each time, on a
> laptop CPU. That is the first thing production fixes."

Go to `BENCH`, open `0001 THIRD PARTY DISCLOSURE - DEMO BASELINE`, and run the
4:45 to 6:25 block against claim `rf-06-thirdparty-t00-c02`. It is the sentence
from slide 2, which makes it a better story anyway.

## If the run failed

> "That failed, which is worth seeing. It is a live model call and the provider
> rate limits us. Nothing is lost: every assessment ever run is on disk with its
> chain, so let me show you one."

Same bench path. Nothing about the argument changes.

## Trims, in the order to take them

1. Deck 5, packs, 35 seconds. Mention it in one sentence instead.
2. The chain slide, deck 6, 25 seconds. The case file already showed the seal.
3. Deck 11, production, 30 seconds. Answer it in questions instead.

Never trim deck 9.
