# Delivery Artifacts

The paper trail an AI delivery produces. Templates, in the order they are
written.

An artifact is not documentation *about* the work; it is the mechanism by which
a stage is completed. A stage that produces no artifact did not happen — there is
nothing to review, nothing to hand over, and nothing to point at when the
decision is questioned six months later.

Every template below is deliberately short. Long documents are not read, and an
unread document provides no alignment.

---

## The full set

| # | Artifact | Written at | Owner | Read by |
|---|---|---|---|---|
| 1 | Problem statement | Stage 0 | Delivery lead | Sponsor |
| 2 | Success metrics and baselines | Stage 1 | Delivery lead + sponsor | Everyone |
| 3 | Data inventory | Stage 1 | Engineer | Data owners, security |
| 4 | Solution design | Stage 2 | Architect / engineer | Architecture board, security |
| 5 | Cost model | Stage 2 | Engineer | Sponsor, finance |
| 6 | Risk register | Stage 2, maintained | Delivery lead | Sponsor |
| 7 | Golden dataset | Stage 3 | Engineer + domain expert | Engineering |
| 8 | Evaluation report | Stage 5, repeated | Engineer | Sponsor, engineering |
| 9 | Decision record | Stage 6 | Sponsor | Everyone |
| 10 | Threat model | Stage 7 | Engineer + security | Security |
| 11 | Model card | Stage 7, maintained | Engineer | Compliance, auditors |
| 12 | Runbook | Stage 7 | Engineer | Operations |
| 13 | Pilot report | Stage 8 | Delivery lead | Sponsor |
| 14 | Handover pack | Stage 9 | Engineer | Operations |

---

## 1 · Problem statement

One page. If it does not fit on one page the problem is not understood yet.

```markdown
# [Name]

## Problem
[Who] currently spends [effort] doing [task], which costs [money/risk/delay],
because [root cause].

## Evidence
- [Measurement, count, or observation supporting the above]

## Current process
1. [Step] — [who] — [how long]
2. …

## Cost of doing nothing
[The status quo, quantified]

## Hypothesis
If [capability] existed, [who] could [outcome], improving [metric] by [estimate].

## Why this needs AI
[The task is language-shaped because … / it is not, and here is the cheaper
alternative]

## Kill criteria
This project stops if:
- [e.g. required data proves inaccessible]
- [e.g. accuracy on a representative sample falls below X]
- [e.g. cost per transaction exceeds Y]

## People
Sponsor: [name] · Domain expert: [name] · Data owner: [name] · Users: [group]
```

---

## 2 · Success metrics and baselines

The most consequential document in the delivery. Signed before building.

```markdown
# Success Metrics — [Name]

## Business metrics
| Metric | Baseline (measured) | Target | How measured | Owner |
|---|---|---|---|---|
| Avg handling time | 14 min (n=340, Jan) | < 9 min | Ticket system export | [name] |

## Technical metrics
| Metric | Target | Measured by |
|---|---|---|
| Answer accuracy (golden set) | ≥ 90% | Offline eval |
| Faithfulness | ≥ 0.85 | Offline eval |
| Retrieval recall | ≥ 0.90 | Offline eval |
| p95 latency | < 3s | Traces |
| Cost per query | < $0.02 | Usage metering |

## The link between them
[Business target] requires [technical target] because [reasoning].

## Explicitly out of scope
- [Capability deliberately excluded, and why]

## Signed
Sponsor: [name, date] · Domain expert: [name, date]
```

---

## 3 · Data inventory

```markdown
# Data Inventory — [Name]

| Source | Location | Format | Volume | Freshness | Owner | Sensitivity | Access status |
|---|---|---|---|---|---|---|---|
| Policy docs | SharePoint /policies | PDF (native) | ~4k docs | Quarterly | [name] | Internal | Approved |
| Claims manual | Shared drive | PDF (scanned) | 800 pp | Annual | [name] | Internal | Pending |

## Quality assessment
- [Known duplicates, superseded versions, contradictions]
- [Extraction difficulties: scans, tables, layout]

## Access dependencies
| Source | Blocked on | Requested | Expected |
|---|---|---|---|

## Sensitive data present
[PII / PHI / payment / client-confidential — and the handling requirement each
triggers]
```

---

## 4 · Solution design

The document an architecture board and a security architect both read.

```markdown
# Solution Design — [Name]

## Summary
[Three sentences: what is built, on what pattern, and why that pattern.]

## Architecture
[Diagram]

### Components
| Component | Responsibility | Technology | Why this choice |
|---|---|---|---|

## Data flow
[Diagram or numbered walkthrough of one request, end to end,
marking every trust and tenancy boundary crossed.]

## Model choice
| | Choice | Reasoning | Fallback |
|---|---|---|---|
| Primary | | | |
| Embedding | | | |
| Re-ranking | | | |

Deployment mode: [managed API / tenanted service / self-hosted] because [reason].
Version pinning: [policy]. Trigger for revisiting: [criterion].

## State and persistence
[What persists, where, for how long, and why]

## Failure behaviour
| Failure | System response |
|---|---|
| Retrieval returns nothing | |
| Model timeout | |
| Tool error | |
| Output fails validation | |
| Guard trips | |

## Latency budget
| Stage | Target | Notes |
|---|---|---|
| Total (p95) | | |

## Alternatives considered
| Option | Rejected because |
|---|---|

## Open questions
| Question | Owner | Needed by |
|---|---|---|
```

---

## 5 · Cost model

```markdown
# Cost Model — [Name]

## Per transaction
| Component | Unit | Volume/request | Unit cost | Cost |
|---|---|---|---|---|
| Input tokens | 1k tok | 4.2 | | |
| Output tokens | 1k tok | 0.5 | | |
| Embedding (query) | 1k tok | 0.05 | | |
| Re-ranking | call | 1 | | |
| **Total per request** | | | | **$0.0xx** |

## Monthly at projected volume
| Volume | Model calls | Infrastructure | Storage | Total |
|---|---|---|---|---|
| Pilot (500/day) | | | | |
| Full (8,000/day) | | | | |

## One-off
| Item | Cost |
|---|---|
| Initial embedding of corpus | |
| Re-indexing (per full rebuild) | |

## Sensitivity
| Change | Cost impact |
|---|---|
| Volume doubles | |
| Switch to a larger model | |
| Caching at 30% hit rate | |

## Comparison
Cost per transaction: $[x] · Value per transaction: $[y] · Ratio: [z]
```

---

## 6 · Risk register

Maintained, not written once.

```markdown
| # | Risk | Likelihood | Impact | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| 1 | Scanned manuals extract poorly | High | High | Vision-model extraction spike in week 2 | [name] | Open |
| 2 | Data access approval slips | Med | High | Requested week 1; escalation path agreed | [name] | Open |
```

---

## 7 · Golden dataset

A data file, not prose — but it needs a header describing itself.

```markdown
# Golden Dataset — [Name]

Version: [n] · Items: [n] · Last reviewed: [date] · Approved by: [expert]

## Composition
| Category | Count | Purpose |
|---|---|---|
| Common questions | 120 | Core coverage |
| Rare but critical | 30 | High-consequence cases |
| Multi-source | 25 | Cross-document reasoning |
| Unanswerable | 20 | Refusal behaviour |
| Out of scope | 15 | Scope discipline |
| Adversarial | 15 | Injection and extraction attempts |

## Provenance
[Where the questions came from]

## Held-out split
[n] items reserved and not used during tuning.

## Change log
| Date | Change | Reason |
|---|---|---|
```

Each item carries: id, question, expected answer, expected sources, category,
notes, and the date and author of the approval.

---

## 8 · Evaluation report

Repeated. The comparison against baseline is the point.

```markdown
# Evaluation — [Name], [date]

## Headline
[One sentence against the target.]

## Results
| Config | Accuracy | Faithfulness | Recall | Precision | p95 | $/query |
|---|---|---|---|---|---|---|
| Baseline (v1) | 0.62 | 0.71 | 0.68 | 0.55 | 2.1s | 0.008 |
| + tuned segmentation | 0.74 | 0.79 | 0.84 | 0.61 | 2.1s | 0.008 |
| + hybrid retrieval | 0.81 | 0.83 | 0.91 | 0.64 | 2.3s | 0.008 |
| **+ re-ranking (current)** | **0.88** | **0.89** | 0.91 | **0.86** | 2.9s | 0.011 |
| Target | 0.90 | 0.85 | 0.90 | — | < 3s | < 0.02 |

## By category
| Category | Accuracy | Note |
|---|---|---|

## What changed
| Change | Effect | Kept |
|---|---|---|

## Failures analysed
| Category | Count | Cause | Fix | Effort |
|---|---|---|---|---|

## Known limitations
- [Limitation, frequency, plan]

## Not measured
- [Explicit gaps]
```

---

## 9 · Decision record

Short, and the absence of it is why projects enter limbo.

```markdown
# Decision — [Name], [date]

**Decision:** Go / Go with reduced scope / Iterate / Stop
**Made by:** [name, role]

## Basis
[Results presented, in one paragraph]

## Conditions
- [What must be true for this to proceed]

## Scope agreed
In: [list] · Out: [list]

## Funded
[Effort and budget for the next stage]

## Next gate
[Date and criteria]
```

---

## 10 · Threat model

```markdown
# Threat Model — [Name]

## Trust boundaries
[Diagram: where untrusted input enters, where privilege is held]

## Assets
| Asset | Sensitivity | Exposure |
|---|---|---|

## Tool inventory
| Tool | Reads | Writes | Permission scope | Approval required |
|---|---|---|---|---|

## Threats
| # | Threat | Vector | Impact | Control | Residual risk |
|---|---|---|---|---|---|
| 1 | Prompt injection via retrieved document | Corpus content | Tool misuse | Read-only tools; approval on effects; content delimited and treated as data | Low |
| 2 | Cross-tenant retrieval | Index misconfiguration | Data exposure | Access-group filter at retrieval; automated isolation test | Low |
| 3 | PII in traces | Observability capture | Privacy breach | Redaction before export | Low |

## Tested
| Control | Test | Result |
|---|---|---|
```

---

## 11 · Model card

Maintained for the life of the system.

```markdown
# Model Card — [Name]

Version: [n] · Owner: [name] · Last reviewed: [date] · Next review: [date]

## Purpose
[What it does, for whom]

## Intended use
[Supported scenarios]

## Out of scope
[Explicitly unsupported and prohibited uses]

## Components
| Role | Model | Version | Deployment |
|---|---|---|---|

## Data
[Sources, provenance, refresh cadence, sensitivity]

## Evaluation
[Method, dataset size, current results, date]

## Limitations
| Limitation | Frequency | Mitigation |
|---|---|---|

## Performance by segment
[Where the system affects people: results broken out by relevant segment]

## Human oversight
[Which actions require approval, by whom]

## Monitoring
[What is watched, thresholds, who is alerted]
```

---

## 12 · Runbook

Written for someone woken at 3am who did not build it.

```markdown
# Runbook — [Name]

## What this system does
[Two sentences]

## Health
| Check | Where | Healthy looks like |
|---|---|---|

## Dashboards
[Links: traces, cost, quality trend, error rate]

## Alerts and responses
| Alert | Means | First action | Escalate to |
|---|---|---|---|
| Error rate > 5% | | Check provider status, then traces | |
| p95 > 6s | | Check retrieval latency span | |
| Cost > daily cap | | Cap engaged; investigate volume source | |
| Quality below floor | | Compare against last known-good config | |

## Common failures
### [Symptom]
Cause · Diagnosis · Fix

## Rollback
[Exact steps. Configuration and prompt reverts included — these are the more
common regression source than code.]

## Kill switch
[How to disable the feature without a deployment]

## Contacts
| Role | Name | Hours |
|---|---|---|
```

---

## 13 · Pilot report

```markdown
# Pilot Report — [Name]

Period: [dates] · Cohort: [n] users, [team]

## Outcome
[One sentence recommendation]

## Business result
| Metric | Baseline | Pilot | Change | Target |
|---|---|---|---|---|

## Adoption
| Week | Active users | Requests | Requests/user |
|---|---|---|---|
[Trend commentary — flat or declining use is the headline if present]

## Quality in production
| Metric | Value |
|---|---|
| Positive feedback rate | |
| Override / escalation rate | |
| Golden-set accuracy (production config) | |

## What users said
[Themes, with representative quotes, including from sceptics]

## Query distribution vs expectation
[What users actually asked, and how it differed]

## Incidents
| Date | Issue | Impact | Resolution |
|---|---|---|---|

## Backlog for rollout
| Item | Priority | Effort |
|---|---|---|

## Recommendation
[Roll out / extend / narrow / stop — with reasoning]
```

---

## 14 · Handover pack

The test of a handover is whether the original team could disappear.

```markdown
# Handover — [Name]

## Ownership
| Area | Team | Contact |
|---|---|---|

## Repositories
| Repo | Purpose | How to run locally |
|---|---|---|

## Environments
| Env | URL | Deploys from | Access |
|---|---|---|---|

## Included
- [ ] Architecture and reasoning ([solution design])
- [ ] Runbook
- [ ] Model card
- [ ] Golden dataset and how to run the evaluation
- [ ] Threat model and security sign-off
- [ ] Cost model and current spend
- [ ] Known limitations
- [ ] Backlog with context
- [ ] Access transferred: repos, cloud, secrets, dashboards, provider accounts

## Recurring obligations
| Task | Cadence | Owner |
|---|---|---|
| Golden-set evaluation | Weekly | |
| Cost review | Monthly | |
| Corpus refresh | Quarterly | |
| Model card review | Biannually | |

## Accepted
Receiving team: [name, date]
```
