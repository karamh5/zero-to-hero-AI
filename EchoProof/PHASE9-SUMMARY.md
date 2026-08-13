# EchoProof - Phase 9 Summary

Ship. Root README entry, and `EchoProof/README.md`.

## What was written

**Root [README.md](../README.md)** gained one entry under Projects, matched to
the length and voice of the existing `wildsense/` entry. It names the honest
headline rather than the flattering one: detection sits at 35 percent, so this
is a triage layer rather than a release gate. A front door that oversells is a
front door the numbers inside contradict.

**[EchoProof/README.md](README.md)** puts the measured results in the second
section, above the quickstart and above the architecture. A reader who stops
after thirty seconds should leave knowing that citation precision is 0.750 and
that judge-human agreement failed its floor, not just that the thing exists.

## Every figure traced to its source

A README is the most copied document in a repository, so a wrong number in one
propagates. Each figure was read out of the artifact that produced it rather
than from memory or from a phase summary:

| Figure | Source | Value |
|---|---|---|
| Judge-human agreement | `labels/agreement.json` | 0.48, kappa 0.31, meets_floor False |
| Campaign pass@3 and pass^3 | `runs/campaign/campaign.json` | 1/5 and 1/5 of 5 graded |
| Campaign cost | `runs/campaign/campaign.json` | $0.82 for 18 calls |
| Latency worst and median | `demo/latency.json` | 140.33 s and 105.11 s |
| Failure drill | `demo/failure_drill.json` | 0 crashes, injection did not flip |
| Demo shortlist size | `demo/shortlist.json` | 4 rules |

## Verification

```
broken relative links   NONE
tests                   189 passed
regression baseline     PASS
em dashes in EchoProof/README.md   0
.env                    not tracked, ignored via EchoProof/.gitignore:1
API key material in trackable files   none
.venv, runs/, retrieval_cache, .npy   none tracked
```

Nothing under `engine/`, `core/`, `packs/` or `tests/` was touched. A
documentation phase that edits the system it documents has invalidated its own
numbers.

## Scope note

The brief lists slides and dry runs alongside this part of the timeline. PHASES.md
Phase 9 names exactly two deliverables and neither is a deck, so building one
would be scope expansion past the phase. `demo/RUN-SHEET.md` already carries the
narrative a deck would present, with measured timings and a failure table.

## Secret scan, the CLAUDE.md pre-push gate

gitleaks 8.30.1 installed via winget on request. Three scans were run.

| Scan | Scope | Result |
|---|---|---|
| `gitleaks git .` | 22 committed commits | **no leaks found** |
| `gitleaks dir .` | whole working tree | 3 findings, all in `EchoProof/.env` |
| `gitleaks git . --staged` | the 112 files git would commit | **no leaks found** |

The three working-tree findings are the live credentials in `EchoProof/.env`.
That file is matched by `EchoProof/.gitignore:1` and was confirmed absent from
the staged set, so it cannot reach a commit. `.env` was deliberately **not**
excluded from the scan configuration: "it is gitignored" is a claim worth
re-verifying rather than assuming, and a scan that hides the one file holding
real keys is a scan that proves nothing.

The staged scan is the one the gate actually requires, because it covers exactly
the diff a push would carry. It is clean.

The index was staged only to produce that diff and was reset afterwards, so the
repository is in the state it started in. **Nothing has been committed or
pushed**; that remains a separate decision.
