# Stakeholders

Who is involved in an enterprise AI delivery, what each of them actually wants,
what they will block on, and how the same system gets described differently to
each of them.

Technical failure is a minority cause of AI projects dying. The majority die
because someone with veto authority was engaged too late, or because the
delivery was described in language that meant nothing to the person paying for
it.

---

## The cast

### Business sponsor

**Owns the budget and the outcome.** Their year gets worse if this fails.

| | |
|---|---|
| **Wants** | A number that improves — cost down, cycle time down, capacity up, risk down. |
| **Fears** | Spending on something that never ships; being publicly associated with an embarrassing AI failure. |
| **Speaks in** | Money, headcount hours, customer impact, quarters. |
| **Blocks on** | Unclear value, cost surprises, missed commitments. |
| **Engage at** | Stage 0, and every week thereafter in writing. |

They do not want to hear about retrieval strategies. They want: *"Support agents
spend 14 minutes per ticket looking things up. In the pilot that dropped to 6.
Across 400 tickets a day that is 53 hours a week."* The architecture is the
appendix.

### End users

**The people who will or will not use it.** The most under-consulted group and
the one that decides whether the project produced value.

| | |
|---|---|
| **Wants** | To do their job faster without a new thing to learn or a new tab to keep open. |
| **Fears** | Being replaced; being blamed for the system's mistakes; being made slower by mandated tooling. |
| **Speaks in** | Concrete tasks, specific annoyances, "it doesn't understand when I ask about X". |
| **Blocks on** | Nothing formally — they simply stop using it, which is fatal and slow to notice. |
| **Engage at** | Stage 1 (shadowing), Stage 6 (reaction), Stage 8 (pilot cohort). |

The job-impact question is present in every room whether or not anyone asks it.
Addressing it directly and honestly is more effective than leaving it to spread
informally.

### Domain expert / subject-matter expert

**The person who can say whether an answer is correct.** Without one, evaluation
degenerates into the engineer's opinion.

| | |
|---|---|
| **Wants** | The system to be right, and to not have their expertise misrepresented. |
| **Fears** | Being asked for open-ended time they do not have; the system confidently contradicting them in front of others. |
| **Speaks in** | Cases, exceptions, "that's true except when…". |
| **Blocks on** | Golden-set sign-off — a real gate at Stage 3. |
| **Engage at** | Stage 1 through Stage 8, continuously. Their time is the scarcest resource in the project. |

Their contribution should be scheduled and bounded — "four hours a week for
three weeks to build and review the evaluation set" — rather than requested ad
hoc, which is how expert involvement quietly evaporates.

### Data owner

**Controls access to the corpus or the database.** Frequently the critical path,
and almost never the bottleneck anyone plans for.

| | |
|---|---|
| **Wants** | To not be responsible for a data leak. |
| **Fears** | Data leaving its boundary; access granted broadly and never revoked. |
| **Speaks in** | Classification levels, retention, approvals. |
| **Blocks on** | Access requests, and the process behind them is measured in weeks. |
| **Engage at** | Stage 1, so that Stage 3 is not waiting on paperwork. |

### Security

**Reviews the design and can stop the deployment.** Cheap to consult early,
expensive to surprise late.

| | |
|---|---|
| **Wants** | Data flows they understand, least-privilege access, no unreviewed egress, an audit trail. |
| **Fears** | An agent with broad write permissions; content sent to an unapproved third-party endpoint; prompt injection reaching a tool that can act. |
| **Speaks in** | Threat models, blast radius, controls, evidence. |
| **Blocks on** | Stage 7 sign-off — a hard gate. |
| **Engage at** | Stage 1 (notification), Stage 2 (data-flow review), Stage 7 (formal review). |

Bringing a data-flow diagram to security at Stage 2 and asking "what would you
need to see to approve this?" converts an adversarial gate into a specification.

### Compliance / legal / privacy

**Owns regulatory exposure.** In finance, healthcare, insurance, and the public
sector this function frequently determines the architecture.

| | |
|---|---|
| **Wants** | Defensibility: every decision explainable, every action logged, personal data handled lawfully, regulated advice not given by a machine. |
| **Fears** | An unexplainable automated decision affecting a customer; personal data in a place it should not be; a regulator asking a question with no answer. |
| **Speaks in** | Obligations, retention, data residency, right to explanation, records. |
| **Blocks on** | Deployment approval; sometimes the model provider or hosting region. |
| **Engage at** | Stage 1 for constraints, Stage 7 for approval. |

### Platform / infrastructure / SRE

**Runs it after handover.** They inherit whatever is built.

| | |
|---|---|
| **Wants** | Something standard, containerised, observable, and documented — not a bespoke artefact only its author understands. |
| **Fears** | Being paged at 3am for a system with no runbook. |
| **Speaks in** | SLOs, deployment pipelines, monitoring, capacity, on-call. |
| **Blocks on** | Handover acceptance at Stage 9. |
| **Engage at** | Stage 2 (so the design fits the platform), Stage 7, Stage 9. |

### Architecture review board

Present in larger enterprises. Approves the design against organisational
standards — approved services, approved models, integration patterns, reference
architectures.

Engaged at Stage 2. Their objections are almost always about consistency with
existing standards rather than about the merit of the design, which means the
right preparation is knowing what the standards are before the meeting.

### Finance / procurement

Owns the vendor relationship and the spend. Cares about cost per transaction,
contract terms, data-processing agreements, and lock-in.

Engaged at Stage 2 (cost model) and Stage 6 (projected spend). A cost surprise
at Stage 9 damages credibility disproportionately, because it is entirely
preventable with a model built at Stage 2.

### Delivery lead / engineering manager

Owns the plan, the estimate, and the communication. In smaller teams this is the
same person building the system, which makes deliberate separation of the two
roles — building versus reporting — a useful discipline.

### The engineer

Owns the system being correct, measured, and maintainable. The distinguishing
behaviour at this level is not tool knowledge; it is the habit of attaching a
before-and-after number to every claim, and of naming the limitations before
someone else finds them.

---

## Engagement map

| Stage | Sponsor | Users | Domain expert | Data owner | Security | Compliance | Platform | Finance |
|---|---|---|---|---|---|---|---|---|
| 0 Intake | **decides** | consulted | consulted | — | — | — | — | informed |
| 1 Discovery | approves | **primary** | **primary** | **primary** | informed | consulted | informed | — |
| 2 Design | approves cost | — | consulted | consulted | **reviews** | consulted | **reviews** | consulted |
| 3 Data | informed | — | **signs off** | **approves** | informed | consulted | supports | — |
| 4 Build | informed | — | consulted | — | — | — | — | — |
| 5 Evaluate | informed | — | **adjudicates** | — | — | — | — | — |
| 6 Gate | **decides** | reacts | consulted | — | flags | flags | consulted | consulted |
| 7 Hardening | informed | — | — | consulted | **approves** | **approves** | **primary** | — |
| 8 Pilot | monitors | **primary** | supports | — | monitors | monitors | supports | monitors |
| 9 Production | approves | **all** | — | — | informed | informed | **accepts** | **monitors** |
| 10 Operate | reviews | reports | triages | — | periodic | periodic | **owns** | reviews |

Bold marks where the stage cannot proceed without that party.

---

## Translating the same result

One pilot outcome, described five ways. The underlying facts are identical; the
selection is not.

**To the sponsor**
> Agents resolved tickets 40% faster with the assistant. At current volume that
> is about 50 hours a week. Cost is roughly $1,400 a month at full rollout. Two
> of the twelve pilot users still prefer the old process and we know why.

**To end users**
> It drafts the answer and cites the policy page it came from, so the check is a
> glance instead of a search. It is reliable on policy and coverage questions.
> It is not reliable on pricing exceptions — those still need the pricing team,
> and it will tell you so rather than guess.

**To security**
> Retrieval is filtered by the requesting user's access group before any content
> reaches the model, so a user cannot surface a document they could not open
> directly. All content is treated as untrusted input and delimited. The agent
> has three read-only tools and no write path. Every request is logged with
> user, query, retrieved sources, and response.

**To compliance**
> Every answer carries citations to the source document and section. Full audit
> log retained for seven years. The system refuses regulated-advice questions
> and routes them to a licensed advisor; that refusal path is in the test suite
> with 30 cases. No personal data is sent to the model provider; the deployment
> is tenanted within our own subscription.

**To the platform team**
> Containerised, deploys through the standard pipeline, exposes health and
> readiness endpoints, emits traces to the existing collector. Runbook covers
> the five failure modes we have seen. Rollback is a configuration revert and has
> been tested. Golden-set evaluation runs as a pipeline stage and fails the build
> below threshold.

---

## Practical rules

**Identify the veto holders at Stage 0.** Anyone who can stop the project should
be known by name before design starts. Discovering a veto at Stage 7 costs
weeks.

**Ask blockers what they need to approve.** Security, compliance, and
architecture review all have criteria. Requesting the criteria in advance turns
a gate into a checklist.

**Give bad news early and specifically.** "Retrieval accuracy on the technical
manuals is 62% against a 85% target; the cause is table extraction and the fix
is roughly a week" preserves credibility. The same information delivered at the
demo destroys it.

**Write down every decision that changes scope**, with who made it and when.
Memory of verbal agreements diverges, reliably and in good faith.

**Assume every stakeholder is busy and none has read the previous update.** Lead
every communication with the conclusion.
