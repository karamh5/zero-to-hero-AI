# Presentation kit

One deck, five scripts. Everything is built against the running system: every
UI instruction was verified by walking the interface at
`http://127.0.0.1:8077`, and every bracketed click was verified against a real
build step in the deck it refers to.

---

## 1. What is here

| File | What it is | Use it when |
|---|---|---|
| [demo-day/deck.html](demo-day/deck.html) | The deck. 16 slides, 15 original inline SVG diagrams, offline, arrow keys, no presenter notes so it is safe to share | Every talk. There is only one deck |
| [scripts/SCRIPT-FINAL-DEMO.md](scripts/SCRIPT-FINAL-DEMO.md) | 13 minutes, all 16 slides plus the full UI walkthrough | **Demo day. Rehearse this one** |
| [scripts/SCRIPT-5MIN.md](scripts/SCRIPT-5MIN.md) | 5 minutes, slides 1, 2, 3, 4, 11, 16 plus a short walkthrough | A brief internal or intro slot |
| [scripts/SCRIPT-2MIN-ELEVATOR.md](scripts/SCRIPT-2MIN-ELEVATOR.md) | 2 minutes, no deck, one screen and one scroll | Corridor, lift, quick intro |
| [scripts/SCRIPT-BUSINESS-AUDIENCE.md](scripts/SCRIPT-BUSINESS-AUDIENCE.md) | 10 minutes, slides 1, 2, 3, 4, 11, 12, 13, 14, 16. Leads with what stalls deployments | Buyers, partnership conversations |
| [scripts/SCRIPT-TECHNICAL-AUDIENCE.md](scripts/SCRIPT-TECHNICAL-AUDIENCE.md) | 15 minutes, all 16 slides, full vocabulary | Engineers, ML people |
| [DEMO-RUNBOOK.md](DEMO-RUNBOOK.md) | Pre-flight, warm-up, what to run, failure playbook | Every single time you present |
| [QA-BANK.md](QA-BANK.md) | Deeper question bank | Prep, the night before |

**Start here:** read `DEMO-RUNBOOK.md` section 1, then rehearse
`scripts/SCRIPT-FINAL-DEMO.md` once end to end with a timer.

---

## 2. The deck

16 slides, one visual system throughout. Slide 10 is an isometric three layer
stack carrying the real vendor names. The deck ships with no presenter notes,
and every slide is written to stand on its own, so it can be sent to somebody
who will read it without anyone narrating.

| # | Slide | # | Slide |
|---|---|---|---|
| 1 | Title | 9 | Audio as evidence |
| 2 | The bottleneck | 10 | The stack, isometric |
| 3 | What they do today | 11 | Where EchoProof sits |
| 4 | What it is | 12 | Go to market |
| 5 | The pipeline | 13 | Market and cost |
| 6 | The isolation boundary | 14 | The landscape |
| 7 | The five verdict states | 15 | How it got here |
| 8 | Evidence and traceability | 16 | Close |

Keys: arrows, space, click, swipe, `O` overview, `F` fullscreen,
`B` blackout, `?` key map, `Home` and `End`, and a slide number followed by
`Enter` to jump.

---

## 3. Where the numbers come from

| Figure | Value | Source |
|---|---|---|
| Manual QA coverage | 1 to 5 percent of calls | Published contact centre QA benchmarks, 2026 |
| Analyst throughput | 10 to 15 interactions per day | Same |
| Voice AI agent market, 2026 | about $3.5B | Published industry forecasts, 2026 |
| Voice AI agent market, 2033 | about $35B, roughly 39 percent CAGR | Same |
| Measured campaign cost | $0.8219 for 18 calls | `runs/campaign/campaign.json`, field `cost_usd` |
| Projected campaign cost | about $23 per 100 calls | `PHASE1-SUMMARY.md`, projection at realistic call length |
| OpenAI Presence | launched July 2026, evals and graders built in, delivered via forward deployed engineers and select global systems integrators | OpenAI announcement and press coverage, July 2026 |
| Hexaware | global IT and BPS provider, CX delivery across global centres | Hexaware public company material |
| Hero finding | `1006.6(d)(1)`, critical | `/runs/prepared-reg_f-rf-06-thirdparty/claims/rf-06-thirdparty-t00-c02`, live UI |
| Speech to text | Deepgram Nova-3, word level timestamps | `SPEC.md` section 8 |

Competitor characterisations for Observe.AI and Modulate are from their own
public product material. Verify anything you plan to say about a named
competitor before you say it in a room where they might be represented.

---

## 4. Verified in the running UI

Nav `BENCH RIG CORPUS DELTA`. Bench card anatomy with `CHAIN VERIFIED`. Run
page headings including the gate decision block reading `BLOCK RELEASE`, the
verdicts table, and the abstentions section listed apart from findings. Case
file headings `WHAT WAS SAID`, `WHAT RULE GOVERNS IT`, `WHY IT FAILED`,
`PROOF`, `EVIDENCE TRACE`, with the eight trace steps and step `04 RETRIEVAL`
rendering open by default. Corpus per run coverage. Delta categories
`CLOSED PERSISTED NEW`.

---

## 5. Open items

1. **`QA-BANK.md` predates this rebuild.** It still contains the evaluation
   figures and the triage layer framing that the current deck and scripts
   deliberately leave out. Use the question sections at the bottom of each
   script instead, or have it rewritten to match.
2. **Pricing is unvalidated.** The scripts say so explicitly rather than
   inventing a number.
3. **Named competitors change fast.** Presence launched in July 2026. Re check
   the landscape slide before any external talk.
