# EchoProof - Phases 6 and 7 Summary

Pack swap and limitations, then demo prep. SPEC sections 1, 9 and 10.

## Phase 6: the engine/pack boundary held, after two real defects were fixed

CLAUDE.md's central architectural claim is that the engine contains no field,
constant or branch that knows which industry it is running in. Nothing had
tested it, because every run until now used one corpus.

**Grepping the engine before building found two format assumptions**, both
about Regulation F's identifier shape:

- `root_section()` computed a provision root by splitting on `(` and `#`. Under
  a corpus numbered `CC-3.1` there is no such character, so every identifier
  became its own root and the conflict detection that compares roots silently
  stopped working.
- The campaign's `caught()` check required `(` or `#` as a boundary character,
  which scored a correct citation as a miss under any other convention.

Both are exactly the defect SPEC section 1 names. Both are fixed by reading
`section_id_scheme.hierarchy_separators` from the policy manifest rather than by
adding a second hardcoded case, because the separator is a property of the
client's drafting conventions and therefore pack data.

**Verified claim rather than assertion:** scanning every executable line in
`engine/` and `core/` for `1006.`, `CFR`, `debt collector`, `Regulation F` or
`CC-` returns zero hits outside comments and docstrings.

### The swap runs

```
pack        synth_telecom      sections 15      separators ('.',)
seeded violations 5 | detected 5 | cited correctly 5 | false positives 1
```

A telecom customer-contact standard, not debt collection, numbered `CC-3.1`
rather than `1006.14(b)(1)`, adjudicated by the same engine with no change
beyond the two boundary fixes.

**These numbers are not evidence that EchoProof is more accurate than the
Regulation F results say.** The synthetic corpus has 15 sections against 303, a
candidate pool twenty times smaller, and its rules are plain modern prose that
closely mirrors the claim language. Retrieval on it is a far easier problem. The
swap demonstrates portability of the engine, not accuracy of the system.

### On the Regulation F regression check

`reg_f` re-run on six fixtures after the boundary fix produced 0 findings. In
the Phase 1 v2 run at the same ceiling, one of those six was detected.

**I cannot claim the fix left results unchanged.** What is established: unit
tests prove `root_section` and `is_within` behave identically for CFR
identifiers under the defaults, and `policy_pack_version` is unchanged at
`9dbe4ac3cf50d31a`. A one fixture swing is consistent with the run to run model
variance already documented in Phases 3 and 4, but it is not proof of no
regression, and it is not being reported as such.

`LIMITATIONS.md` consolidates every measured limitation, each pointing at a
number a run in this repository produced.

## Phase 7: demo prep, constrained by measurement rather than preference

### Latency, measured by stage

| Stage | Median | Worst |
|---|---|---|
| Extraction | 5.2 s | 6.5 s |
| Retrieval | 91.1 s | 125.1 s |
| Judge | 8.8 s | 20.8 s |
| **Total per turn** | **105 s** | **140 s** |
| Stack startup, one time | | 20 s |

Retrieval dominates: four claims, three questions each, roughly seven seconds of
cross-encoder reranking per query. One warm-cache run completed in 26 seconds,
but a live demo cannot rely on that: the observer picks live and the agent
replies live, so the claims are new and the cache is cold. The rehearsal
measured a 0 percent hit rate.

This is why the fix-and-rerun clip plays during the wait rather than after it,
which is what the brief anticipated.

### The shortlist is a query, not a preference

`scripts/pick_demo_scenario.py` mines all eleven recorded evidence logs and
ranks rules by how many separate runs produced a finding citing them. Ranking on
distinct runs first, then raw count, because a rule caught once in each of three
runs is a far safer stage bet than one caught three times inside a single
transcript that happened to go well.

| Rule | Findings | Runs |
|---|---|---|
| 1006.18(b)(3) arrest threats | 5 | 4 |
| 1006.6(d)(1) third party disclosure | 6 | 3 |
| 1006.10(b)(1) identification on location calls | 6 | 3 |
| 1006.6(b)(1)(i) unusual time or place | 6 | 3 |

The observer still chooses. The choice is genuinely theirs and is not made in
advance, but it is drawn from rules with a recorded track record rather than
from the open field, because at 34.8 percent detection an open field fails
roughly two times in three. The slide says the shortlist came from measured runs.

### The rehearsal

```
[0:00.0] observer selected 1006.18(b)(3)
[0:01.9] call complete
[0:01.9] adjudicating, play the fix-and-rerun clip now
[2:37.6] adjudication complete: 4 claim(s), 2 finding(s)

FINDING   contradicted
SECTION   1006.18(b)(3)   <- the rule the observer picked
RULE      A debt collector must not represent or imply that nonpayment of any
          debt will result in the arrest or imprisonment of any person ...
HASH      c1a83dbf4b5f27a242869750c17b2982

total elapsed 158s (2.6 min) | within four minutes True | rule caught True
```

Full sequence, start to finish, no manual intervention, inside the four minute
budget, citing the rule the observer picked with the matching rule text.

### The run sheet

`demo/RUN-SHEET.md` carries the minute by minute sequence, and a failure table
covering the things this project has actually hit: provider rate limiting, a
scenario producing no finding, a cold reranker, a wrong citation, a network drop.

Two entries are worth repeating here.

**The numbers slide is marked not skippable.** A room that leaves believing this
is a release gate is a worse outcome than a demo that visibly fails: the first
produces a pilot that collapses on contact with real calls, the second produces
a conversation.

**"No finding emitted" has a scripted response.** Say immediately that this is
what a 34.8 percent detection rate looks like, then cut to the backup. Do not
re-run live.

## Artifacts

| Path | Contents |
|---|---|
| `packs/policy/synth_telecom/` | 15 rule synthetic corpus, dotted identifiers |
| `fixtures/synth_telecom.jsonl` | 8 fixtures against it |
| `scripts/swap_demo.py` | Adjudicate against any pack |
| `LIMITATIONS.md` | Every measured limitation, consolidated |
| `demo/RUN-SHEET.md` | Stage sequence, timings, failure table |
| `demo/shortlist.json` | Four rules with their recorded hit counts |
| `demo/latency.json` | Stage timings behind the table above |
| `demo/backup/` | Fix-and-rerun clip, 35 s, replayed from a real run |
| `scripts/run_demo.py` | The whole live segment in one command |

Test suite: 120 passing, including tests that no shortlist entry lacks recorded
evidence and that the clip fits inside the measured dead time.
