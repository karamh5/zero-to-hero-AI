# 5 minute script, AI Launchpad internal, tomorrow

Audience: the AI Launchpad team, Erik and Patrick. Not the demo day audience.
Patrick asked for a couple of slides to introduce the idea, then a brief
walkthrough of the demo. That is exactly what this is.

Plain language throughout. Every technical term is defined in the same breath.
Total spoken content is about 680 words, which is 4 minutes 50 seconds at a
normal presenting pace. It fits with room to breathe.

---

## Pre-flight, done before the room fills

Not optional. The stack is cold until something has run, and a cold start adds
40 seconds of nothing happening.

```bash
.venv/Scripts/python scripts/run_ui.py
```

**Use `.venv/Scripts/python`, not `python`.** This matters more than it looks.
The system interpreter has no `openai` module, so the UI serves every stored
screen perfectly, the rig reports itself available, and then the run fails
three seconds after you click. This exact failure happened while preparing
this script.

Then, at least ten minutes before you present:

1. Open `http://127.0.0.1:8077/rig`.
2. Under `02 / SELECT CONVERSATION`, group `SUPPORTED`, click
   `04 VALIDATION NOTICE CONTENTS DESCRIBED`.
3. Title it `Validation notice, warm-up`.
4. Click `RUN ADJUDICATION →` and let it finish, roughly 2 minutes.

That warms the model weights and leaves a clean supported assessment on the
bench that you can point at if anyone asks whether it ever says yes.

**Check before you start:**

- `http://127.0.0.1:8077/bench` opens with `0001 THIRD PARTY DISCLOSURE - DEMO BASELINE` at the top, and every card reads `CHAIN VERIFIED`.
- Two browser tabs open: tab 1 on `/rig`, tab 2 on `presentation/tomorrow/deck.html`.
- Browser zoom at 100 percent, window maximised.
- Press `N` once in the deck to confirm presenter notes toggle, then press `N` again to hide them.

---

## The timing, and why it works

| Event | Clock |
|---|---|
| Click `RUN ADJUDICATION →` | 0:55 |
| Measured completion, warm stack, this conversation | +120 s |
| Expected finish | 2:55 |
| You return to the browser | 3:25 |
| Margin | 30 s |

The 120 seconds is measured, not estimated. A full timed run of
`Furnished to a credit bureau before contact` on a warm stack completed in
120.2 seconds on this machine.

**Why this conversation and not the third party one.** The third party
conversation is the better story, but it carries 8 claims and takes 224
seconds measured. That does not fit in a 5 minute slot. The credit bureau
conversation carries 5 claims, produces two critical findings citing
`1006.30(a)(1)`, and is just as easy to understand: they reported you to a
credit bureau without ever telling you.

The third party case is still in the talk. It is the sentence on slide 2, and
it is sitting on the bench as assessment `0001` if anyone wants to see it.

---

## The script

Left column is the clock. Do not drift; the run is on its own timer.

| Clock | On screen | Action | Say, word for word |
|---|---|---|---|
| 0:00 | Deck, slide 1 | Stand still. Do not read the slide. | "Voice AI agents are being put into regulated conversations right now. Debt collection, insurance, healthcare. The agent talks to a real customer, and every sentence it says is either allowed or it is not." |
| 0:15 | Deck, slide 2 (`→`) | Let them read the quote for two full seconds before speaking. | "Here is a real sentence from a collections agent. It sounds helpful. It is also a federal violation, because you cannot discuss someone's debt with a person who is not them. Right now, nothing catches that before the agent goes live. You find out from a regulator." |
| 0:35 | Switch to browser tab 1, `/rig` | `Alt+Tab` to the browser. It is already on `/rig`. | "So let me start it running, and then I will explain what it is doing while it works." |
| 0:42 | `/rig` | Point at `01 / SELECT CORPUS`. Regulation F already shows `SELECTED`. **Do not click it.** | "This is the client's rulebook. This one is Regulation F, the federal debt collection rule, 303 provisions pulled straight from the government source." |
| 0:48 | `/rig` | Under `02 / SELECT CONVERSATION`, in the group headed `CONTRADICTED`, click `02 FURNISHED TO A CREDIT BUREAU BEFORE CONTACT`. The right panel `SOURCE CONVERSATION` fills in. | "And this is a recorded conversation with the agent. Notice the customer's lines are marked context only. Only the agent gets judged. The customer is never assessed." |
| 0:53 | `/rig` | Click the `03 / ASSESSMENT TITLE` box and type `Credit bureau, live`. | "I name the run so I can find it later." |
| 0:55 | `/rig` | **Click `RUN ADJUDICATION →`.** Wait for the first line to appear in `stage log, every line a real event`. | "And it is running. Every line in that log is a real event from the pipeline, not an animation. There is no progress bar, deliberately, because there is nothing honest to put in one." |
| 1:00 | Switch to deck, slide 3 (`Alt+Tab`, then `→`) | Leave the run going. Do not look back at it. | "While that works. What a compliance review looks like today is a person listening to call recordings with the rulebook open next to them. It is slow, it only samples a fraction of calls, and it happens weeks after the agent is already live." |
| 1:20 | Deck, slide 3 | Gesture at the third column. | "EchoProof does it before you deploy, on every single turn, and it shows its work. When it flags something it names the exact paragraph and quotes it back to you." |
| 1:40 | Deck, slide 4 (`→`) | Walk the four columns left to right, about eight seconds each. | "Four steps. First, we read only what the agent said. Second, we pull the claims out as exact quotes, stored as positions in the real transcript, so nothing is ever paraphrased. Third, we search the client's rulebook for the provision that governs that specific sentence. Fourth, a model rules on it." |
| 2:15 | Deck, slide 5 (`→`) | This is the slide to cut if you are behind. | "And here is the one decision that makes this different from just asking ChatGPT whether something is compliant. The judge never sees the whole rulebook, and it never uses what it learned in training. It sees one retrieved paragraph and rules from that alone. That is why the answer can be checked instead of trusted." |
| 2:45 | Deck, slide 6 (`→`) | Slow down. Make eye contact with Erik and Patrick. **Do not skip this slide.** | "I want to be straight about where this actually is. When it flags something, three quarters of the time it names the right paragraph, and on the clean control call it stayed silent every single time we ran it." |
| 3:05 | Deck, slide 6 | Point at the two red figures. | "But it only catches about a third of the violations we planted, and when I graded it against a human it agreed less than half the time. So this is a triage layer that routes work to a human reviewer. It is not a release gate, and I am not going to call it one." |
| 3:25 | Switch to browser tab 1 | `Alt+Tab`. The run should read `SEALED assessment complete` in the stage log. | "And it has finished." |
| 3:30 | `/rig` result, or `/bench` | Click through to the assessment. If the rig shows the finished assessment, click it. Otherwise click `BENCH` in the top nav and click the top card, `CREDIT BUREAU, LIVE`. | "Two findings. Both marked critical." |
| 3:40 | `/runs/{id}` | Point at `GATE DECISION, COMPUTED FROM THE CLIENT'S CRITERIA PACK`, reading `BLOCK RELEASE`. | "That is the client's own threshold, not ours. They said one critical finding blocks a release, so this agent does not ship today." |
| 3:52 | `/runs/{id}` | Scroll to `FINDINGS 2`. Click the first finding, claim `rf-04-creditreport-t00-c00`. | "Let me open one." |
| 4:00 | Case file | Point at `WHAT WAS SAID`. | "This is what the agent said, quoted exactly: we reported this account to the credit bureau before we ever contacted you about it." |
| 4:10 | Case file | Point at `WHAT RULE GOVERNS IT`, the cream coloured card. | "And this is the rule it broke, printed verbatim, section 1006.30(a)(1). You do not have to trust the verdict. The paragraph is right there next to it." |
| 4:22 | Case file | Scroll to `EVIDENCE TRACE`. Do not click anything; step 04 is already open. | "And underneath, all eight steps of how it got there. The search queries it ran, every candidate rule it considered, which one it picked and at what score, and a hash chain so you can prove none of it was edited afterwards." |
| 4:35 | Deck, slide 7 (`Alt+Tab`, `→`) | Stop moving. | "So: every claim has a source, every verdict has a rule, and every finding has evidence. It is a triage layer today, and the honest gap is detection. And the engine has nothing about debt collection in it, so the same code ran a telecom rulebook with no changes. Happy to take questions." |
| 5:00 | | Stop talking. | |

---

## If the run is still going when you return at 3:25

Do not wait in silence and do not apologise. Say this:

> "Still working. It takes about two minutes a conversation, and the reason is
> honest: it runs several searches per sentence and reranks fifty candidate
> rules for each one, on a laptop CPU. That is the number one thing production
> would fix, by moving that step to a GPU."

Then switch to `BENCH` in the top nav, open `0001 THIRD PARTY DISCLOSURE - DEMO BASELINE`,
and run the 3:40 to 4:35 block against that assessment instead. It is the
third party conversation from slide 2, it has two critical findings citing
`1006.6(d)(1)`, and the case file looks identical. Claim to open:
`rf-06-thirdparty-t00-c02`.

Check back at the rig at the end if there is time. If it finished, say so.

## If the run failed outright

The stage log will show `FAILED`. Say this, without flinching:

> "That one failed on me, which is worth seeing too. It is a live model call
> and the provider rate limits us sometimes. It does not lose anything: every
> assessment that has ever run is on disk with its evidence chain, so let me
> show you one that already ran."

Then go to `BENCH`, open `0001 THIRD PARTY DISCLOSURE - DEMO BASELINE`, and
continue from the 3:40 block. Nothing about the argument changes. Everything
you were going to point at is on that screen.

## If the whole server is down

Skip the browser entirely. Stay in the deck, and after slide 6 say:

> "The demo is a live run against a real model, so I will not fake it here.
> Grab me after and I will run it in front of you."

Slides alone carry the idea. Patrick asked for slides plus a walkthrough, so
losing the walkthrough is a dent, not a disaster.

---

## Things not to say

- Do not say "accuracy" without a number attached. The numbers are asymmetric and the question will come back.
- Do not say it "checks compliance". It routes claims to a human reviewer with the governing rule attached.
- Do not promise the `no_governing_rule` verdict state. It cannot currently be produced, and the policy gap list is empty on every run for that reason.
- Do not offer to type a custom conversation. The rig refuses free text on purpose: without speaker labels there is no way to guarantee only the agent is assessed. If asked, say exactly that, and offer to add their scenario to the library.

## The two questions Erik or Patrick are most likely to ask

**"How is this different from just asking an LLM if the call was compliant?"**
> "Because a model asked that question answers from memory, and you cannot
> check it. Ours never sees the rulebook. It gets one paragraph that a search
> step retrieved, and it has to rule from that text. The paragraph is printed
> next to the verdict, so you can disagree with it in five seconds."

**"Only a third caught. Is that usable?"**
> "As a gate, no, and I would not sell it as one. As triage, yes: it reads
> every turn, and the things it does surface come with the right rule attached
> three quarters of the time. It turns a pile of recordings into a short list
> with citations. The gap is detection, and that is the next thing I would
> work on."
