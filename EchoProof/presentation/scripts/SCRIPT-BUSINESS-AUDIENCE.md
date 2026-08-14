# Business audience, 10 minutes

For buyers, executives and anyone whose first question is what this costs and
what it saves. The architecture is evidence that the thing works, not the
subject of the talk. Lead with exposure and deal cycle, not with retrieval.

Deck: [../demo-day/deck.html](../demo-day/deck.html). Use slides 1, 2, 3, 5, 9,
11, 12. Skip 4, 6, 7, 8, 10.

**Latency strategy.** Live run of `Furnished to a credit bureau before contact`
launched at 1:45, measured 120.2 seconds warm, return at 4:15. A 150 second
margin, deliberately generous, because this audience will interrupt with
questions and you cannot control the clock as tightly.

| Clock | On screen | Say |
|---|---|---|
| 0:00 | Deck 1 | "Every enterprise deploying a voice agent into a regulated conversation has the same unanswered question: which of the things it says are going to cost us." |
| 0:20 | Deck 2 | "This is a real agent sentence. Warm, helpful, and a federal violation, because a collector cannot discuss a debt with someone who is not the debtor. FDCPA statutory damages, plus class exposure, plus the consent order that follows." |
| 0:50 | Deck 2 | "What makes it expensive is that nothing catches it. It is not a wrong answer, so your eval suite passes it. You find out from a regulator." |
| 1:15 | No slide, talk | "What compliance review looks like today: a person listening to recorded calls with a rulebook open beside them. It samples a fraction of calls, it happens weeks after launch, and it produces a spreadsheet of opinions with no citation attached. It is also the thing that holds up the deal, because legal will not sign off on a system nobody has checked." |
| 1:45 | Browser, `/rig` | Click `02 FURNISHED TO A CREDIT BUREAU BEFORE CONTACT` under `CONTRADICTED`, title it, **click `RUN ADJUDICATION →`**. "Let me start a real one and talk while it works." |
| 2:00 | Deck 3 | "In one sentence: we sit in front of the agent, read what it said, find the governing rule in the client's own rulebook, and produce a verdict with the paragraph attached. It adds a tenth of a millisecond to the live call, so it does not slow anything down." |
| 2:30 | Deck 5 | "The part that matters commercially. There is nothing about debt collection in the engine. A client brings four things: their rulebook, the scenarios they care about, the customer personas, and the thresholds that decide what blocks a release. We proved it by swapping a federal regulation for a telecom standard with no code change." |
| 3:10 | Deck 5 | "So the same product sells into collections, insurance, telecom and healthcare. What changes per client is data they already have, in a form their compliance team already maintains." |
| 3:40 | No slide, talk | "Cost. The 18 call campaign we ran cost 82 cents in model spend. Projected at longer calls it is roughly 23 dollars per hundred call campaign. That is not the interesting number. The interesting number is that a compliance review that currently takes weeks of a specialist's time becomes something you run every night against every agent change." |
| 4:15 | Browser | "And it is done." Open the assessment. |
| 4:30 | `/runs/{id}` | "Two findings, both critical, and `BLOCK RELEASE`. That threshold is the client's, from their own criteria pack. They said one critical finding blocks a release. We compute against their rule, we do not impose ours." |
| 5:00 | Case file | "Open one. What the agent said, exactly. The rule it broke, verbatim, section 1006.30(a)(1). And underneath, every step of how it got there, sealed so it cannot be edited afterwards." |
| 5:40 | Case file, `EVIDENCE TRACE` | "That last part is the one your legal team will care about. When a regulator asks how you knew, this is the answer, and it is tamper evident by construction." |
| 6:10 | Deck 9 | "Now the honest part, because you will find this out anyway and I would rather you hear it from me." |
| 6:30 | Deck 9 | "When it flags something, three or four times in five it names the correct paragraph. On a clean, compliant call it stayed silent every time we ran it, which is the result that protects your reviewers' trust. But it only catches about a third of the violations we planted, and when graded against a human it agreed less than half the time." |
| 7:10 | Deck 9 | "So this is triage, not certification. It reads every turn, which no human process does, and it hands your reviewer a short list with the rule already attached. It does not replace the reviewer and I would not sell it as though it did." |
| 7:40 | No slide, talk | "Which means the honest business case today is reviewer leverage, not headcount replacement. Your specialist stops listening to calls looking for problems and starts adjudicating a citation backed short list. And every decision they make is on the record." |
| 8:15 | Deck 11 | "Everything you saw runs on a laptop, deliberately. The production path is designed and not built, because building it would have cost the measurements I just showed you. The model swap to Bedrock is a configuration change." |
| 8:45 | Deck 12 | "Every claim has a source, every verdict has a rule, every finding has evidence. The gap is detection, and that is where the next work goes." |
| 9:10 | | "What I want is an introduction to someone who buys compliance tooling, so I can find out what they would actually pay for." |
| 9:30 | | Stop. Take questions. |

## Business questions you will get, and the short answers

**"What does it cost to run?"**
> "82 cents for the 18 call campaign we measured. Roughly 23 dollars per
> hundred calls projected at realistic call lengths. Model spend is not the
> constraint. Reviewer time is, and that is what this is aimed at."

**"How long to onboard a new client?"**
> "The work is building the policy pack, which is their rulebook chunked to
> paragraph level with real section identifiers. Reg F took a scripted pull
> from the government source. A private corpus is a document ingestion job, and
> I would want to measure retrieval on it before quoting anyone a date."

**"Who is the buyer?"**
> "Whoever signs off that the agent can go live. In collections that is the
> compliance officer, and the budget usually sits with whoever owns the
> deployment. I have not validated that with a real buyer yet, which is exactly
> what I am asking for."

**"Why would I not just have my compliance team check it?"**
> "You should, and you still will. They cannot listen to every call and this
> can read every turn. It is the difference between sampling and coverage."

**"What happens when it is wrong?"**
> "Two ways to be wrong. It stays quiet on a real violation, which happens
> about two thirds of the time and is why this is not a gate. Or it flags
> something clean, which on our control scenario did not happen in any run. The
> second kind is the one that destroys reviewer trust, and it is the one we
> tuned hardest against."

## Do not

- Do not use the word certification.
- Do not quote detection without the citation precision beside it, or the number sounds worse than it is.
- Do not quote citation precision without detection beside it, or it sounds better than it is.
