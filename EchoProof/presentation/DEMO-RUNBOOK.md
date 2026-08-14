# Demo runbook

Written to be followed by someone who is nervous and short of time. Do the
steps in order. Do not improvise the setup.

---

## 1. Pre-flight, 15 minutes before

### Step 1. Start the server with the right interpreter

```bash
.venv/Scripts/python scripts/run_ui.py
```

**Use `.venv/Scripts/python`. Never bare `python`.**

This is the single most dangerous mistake available to you. The system
interpreter has no `openai` module. If you start with it, everything looks
perfect: the bench loads, the corpus loads, the rig renders, and
`/api/adjudicate/availability` even reports `available: true`. Then the run
fails three seconds after you click, in front of the room, with
`No module named 'openai'`. This happened while preparing these documents.

Expected output: uvicorn startup lines ending in
`Uvicorn running on http://127.0.0.1:8077`.

### Step 2. Confirm the server is alive and live runs are possible

```bash
curl -s http://127.0.0.1:8077/api/adjudicate/availability
```

Expected, exactly:

```json
{"available":true,"reason":null,"stack_state":"cold","stack_error":null,"model_key_present":true,"deepgram_key_present":true,"queued":0}
```

If `model_key_present` is `false`, `MISTRAL_API_KEY` is missing from `.env`.
The rig will report its own disabled state and everything else still works, so
switch to the bench only path in section 5.

### Step 3. Warm the stack. Not optional.

A cold start loads embedding and reranker weights. **Measured at 40 seconds**
on this machine, and it happens on the first run of a session. Do not let it
happen on stage.

1. Open `http://127.0.0.1:8077/rig`.
2. Under `02 / SELECT CONVERSATION`, group `SUPPORTED`, click
   `04 VALIDATION NOTICE CONTENTS DESCRIBED`.
3. Type `Validation notice, warm-up` into the `03 / ASSESSMENT TITLE` box.
4. Click `RUN ADJUDICATION →`.
5. Wait for `SEALED assessment complete` in the stage log.

This costs about two minutes and leaves a clean, all supported assessment on
the bench, which is useful if anyone asks whether the system ever says yes.

Confirm the weights are resident: run availability again and check
`stack_state` is no longer `cold`.

### Step 4. Check the bench

Open `http://127.0.0.1:8077/bench`. Confirm:

- The top card is `0001 THIRD PARTY DISCLOSURE - DEMO BASELINE`.
- Every card reads `CHAIN VERIFIED`.
- Your warm-up run appears with the title you gave it.

### Step 5. Windows and tabs

| Tab | URL | Why |
|---|---|---|
| 1 | `http://127.0.0.1:8077/rig` | Where you launch the run |
| 2 | The deck for your slot | Slides |
| 3 | `http://127.0.0.1:8077/runs/prepared-reg_f-rf-06-thirdparty/claims/rf-06-thirdparty-t00-c02` | The fallback case file, pre-loaded |

- Browser zoom exactly 100 percent. The type scale is tuned for it.
- Window maximised. The rig is a two column layout and collapses under 900px.
- Close every other tab. A notification during a demo is a lost room.
- Press `N` in the deck once to confirm presenter notes open, then `N` again to close.

### Step 6. Check nothing else is competing

Nothing else should be hitting the model. Two processes competing roughly
doubles wall clock. Close any other terminal running a campaign or a script.

---

## 2. Which conversation to run, by slot length

Timings measured on this machine, warm stack.

| Conversation | Claims | Measured | Use in |
|---|---|---|---|
| `Validation notice contents described` | 4 | not timed, roughly 95 s | warm-up, and the supported example |
| `Furnished to a credit bureau before contact` | 5 | **120.2 s** | 5 min, 10 min, business |
| `Debt disclosed to a third party` | 8 | **224.3 s** | 15 min and technical only |

The rule: budget the wait against the measured time for the conversation you
actually chose, not against the 105 second per turn median in `demo/latency.json`.
That median is per turn, and every prepared conversation has two agent turns.

## 3. Do not run these

### `Correct call opening`, telecom pack. Never.

It misfires, and it misfires in the most confusing possible way. `CC-5.1`
requires the agent to identify the company AND state the purpose of the call.
The agent does both in one sentence. Claim extraction splits that sentence into
two claims and the judge evaluates each half against the whole rule, so each
half is marked a violation of a rule the sentence actually satisfies. You will
be standing in front of a red finding trying to explain that it is correct
behaviour from a component that is wrong.

If it comes up unprompted, the answer is in
[QA-BANK.md](QA-BANK.md) under "What is broken that you have not mentioned".
It is a disclosed structural limitation, not a bug.

### The abstention conversations, unless asked deliberately

Five conversations produce `retrieval_below_confidence`. They are legitimate
and worth showing if the room asks what happens when the system is unsure. Do
not present them as caught violations. Three of them were written to be
violations and are not detected as such, which matches the campaign misses.

### Anything promising `no_governing_rule`

It cannot currently be produced. The policy gap list is empty on every run
because the retrieval floor is never crossed, not because the corpus is
complete. Do not promise this state.

---

## 4. Failure playbook

| Failure | What you see | Say | Do |
|---|---|---|---|
| Provider rate limit | Stage log shows `FAILED`, error mentions rate or 429 | "That failed, which is worth seeing. It is a live model call and the provider rate limits us. Nothing is lost, every assessment ever run is on disk with its chain." | Go to `BENCH`, open `0001`, continue from the case file block. Permanent switch, do not retry on stage. |
| Run still going when you return | Stage log still scrolling, no `SEALED` line | "Still working. About two minutes a conversation: several searches per sentence, fifty candidates reranked each time, on a laptop CPU. That is the first thing production fixes." | Switch to `BENCH`, open `0001`, run the case file block there. Check the rig again before you close. |
| Run hangs past the measured time plus 60 s | No new stage log lines for over a minute | Same words as above. | Do not wait. Switch to bench and do not come back to it. |
| `No module named 'openai'` | Stage log `FAILED` within about 3 seconds | "I started the server on the wrong Python. The stored assessments are all here." | Bench only for the rest of the talk. Restart with `.venv/Scripts/python` afterwards. |
| No `MISTRAL_API_KEY` | Rig shows `live adjudication disabled` before you click | "Live runs are off on this machine, so let me show you assessments that already ran." | Bench only path, section 5. Do not click run. |
| Server not started | Browser shows connection refused | Nothing. Do not narrate. | Run the Step 1 command. If it takes more than 20 seconds, go to slides only and offer to demo after. |
| Port 8077 occupied | Startup error `address already in use` | Nothing, this is pre-flight. | `netstat -ano \| grep ":8077"`, then `taskkill //PID <pid> //F`. Or start on another port with `--port 8080` and update your tabs. |
| Stale build in browser cache | UI renders but looks wrong or a route 404s | Nothing. | Hard reload with `Ctrl+Shift+R`. If still wrong, go bench only. |
| Audio clip will not play | Clip control present, no sound | "Audio is evidence attached to a finding, never a detection input, so the record is complete without it." | Move on. Do not troubleshoot audio live. Only `audio-demo` and `demo-campaign` have clips at all. |
| Network down entirely | Everything local still works | Nothing to say, the demo is local. | The decks are self contained and the UI is on localhost. Only a live run needs the network, so go bench only. |

**Recoverable mid talk:** stale cache, audio, port conflict caught in pre-flight.

**Switch permanently to bench:** rate limit, hang, wrong interpreter, missing
key, network down. Do not attempt a second live run in the same session. A
second failure costs the room more than the first one did.

---

## 5. The bench only path

Everything below is stored, chain verified, and needs no model call. This path
carries the entire argument. Use it whenever a live run is unavailable.

1. `BENCH` in the top nav. Point at `CHAIN VERIFIED` on the cards.
2. Open `0001 THIRD PARTY DISCLOSURE - DEMO BASELINE`.
3. Point at `GATE DECISION, COMPUTED FROM THE CLIENT'S CRITERIA PACK`,
   reading `BLOCK RELEASE`, with the reason `2 critical finding(s) meets the
   client's block threshold of 1.`
4. Point at `ABSTENTIONS 6`, counted separately from findings.
5. Under `FINDINGS 2`, open claim `rf-06-thirdparty-t00-c02`.
6. `WHAT WAS SAID`, then the cream `WHAT RULE GOVERNS IT` card showing
   `1006.6(d)(1)`, then `WHY IT FAILED`.
7. Scroll to `EVIDENCE TRACE`. Step `04 RETRIEVAL` is **already open**. Do not
   click it, you would close it. Point at the three queries and the candidate
   field, selected at 0.716.
8. Step `08 EVIDENCE SEAL`.

For a supported counterexample, open
`/runs/prepared-reg_f-rf-11-validation`: 4 claims, 4 supported, 0 abstentions,
citing `1006.34(c)(2)(v)`, `1006.34(c)(2)(viii)` and `1006.38(d)(2)`.

Do not use `Written contact by postcard` as the supported example. The rig
files it under `SUPPORTED` by its recorded outcome, but the stored run produces
zero supported verdicts and four abstentions.

---

## 6. Two second sanity check before you speak

- Server started with `.venv/Scripts/python`.
- Stack warm.
- Bench top card is `0001`, everything `CHAIN VERIFIED`.
- Zoom 100, window maximised, other tabs closed.
- You know which conversation you are running and its measured time.
