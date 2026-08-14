# 2 minute elevator

**Latency strategy: nothing runs live.** A live adjudication takes 120 seconds
at its fastest measured, which is the entire slot. This script works only from
stored assessments on `/bench`, all of which are chain verified. Say nothing
that implies something is running now.

Have `http://127.0.0.1:8077/runs/prepared-reg_f-rf-06-thirdparty/claims/rf-06-thirdparty-t00-c02`
open in a tab before you start. That single screen is the whole demo.

| Clock | On screen | Say |
|---|---|---|
| 0:00 | Case file, top | "Enterprises are putting voice AI agents into conversations governed by law. Debt collection, insurance, healthcare." |
| 0:10 | Point at `WHAT WAS SAID` | "This is a real thing a collections agent said: tell her she owes four thousand five hundred dollars. It is warm, it is helpful, and it is a federal violation, because you cannot discuss a debt with someone who is not the debtor." |
| 0:25 | Same | "It is not a hallucination and not a wrong fact, so no accuracy benchmark is looking for it." |
| 0:35 | Point at the cream `WHAT RULE GOVERNS IT` card | "EchoProof caught it before deployment and printed the rule it broke, verbatim, section 1006.6(d)(1)." |
| 0:50 | Point at `WHY IT FAILED` | "The reasoning is right there, and the key design decision is that the judge never saw the rest of the rulebook. It gets one retrieved paragraph and rules from that alone, which is why you can check it instead of trusting it." |
| 1:10 | Scroll to `EVIDENCE TRACE` | "Underneath is every step: the searches it ran, every candidate rule it considered, which one it chose and at what score, sealed in a hash chain so nothing can be edited afterwards." |
| 1:30 | Look up, stop scrolling | "Honestly: it catches about a third of planted violations, so it is a triage layer that routes to a human reviewer, not a release gate. What it is good at is being right about which rule, three quarters of the time, and staying silent on clean calls." |
| 1:50 | | "The engine has no debt collection knowledge in it. Same code ran a telecom rulebook with no changes. What I need is an introduction to someone who buys compliance tooling." |
| 2:00 | Stop. | |

## Fallback

If the server is not running, this script still works from a screenshot of
that one case file. Keep one on your phone. If you have neither, the spoken
content stands alone; drop the pointing instructions and keep every word.

## The honest line is not optional

Even at two minutes, the triage sentence at 1:30 stays in. A two minute pitch
that omits it is a two minute pitch that misrepresents the system.
