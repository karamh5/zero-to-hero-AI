# Risk and Governance

Everything that stands between a system that produces good answers and a system
an organisation is willing to put in front of customers.

None of this improves quality. All of it determines whether the system ships.
It is also, consistently, the most underestimated stage of an AI delivery — a
proof of concept built in three weeks routinely takes another two to three
months to satisfy what follows.

---

## Why AI governance is heavier than software governance

Three properties drive every control in this document.

| Property | Consequence |
|---|---|
| **Non-deterministic** | The same input can produce different outputs. Testing cannot enumerate behaviour, so controls must be structural rather than case-by-case. |
| **Fails fluently** | A wrong answer arrives with the same confidence and polish as a right one. There is no stack trace, no error page, no signal to the user that anything went wrong. |
| **Instructions and data share a channel** | The model reads its instructions and its input through the same interface, which means content it retrieves can attempt to instruct it. This has no equivalent in conventional software. |

A conventional bug produces an error. An AI failure produces a plausible,
well-formatted, incorrect answer that a user acts on. That is the whole reason
this document exists.

---

## Security

### Identity and access

- **Authentication** integrated with the organisation's identity provider. Real
  users, real sessions, no shared service accounts standing in for people.
- **Authorisation** by role, enforced server-side. The client is not a security
  boundary.
- **Permission-aware retrieval** — the system must never surface content the
  requesting user could not open directly. Enforced *at retrieval time* by
  filtering on the access metadata attached during ingestion, not by filtering
  the answer afterwards. Filtering after generation means the content already
  reached the model and may already be paraphrased into the response.
- **Tenant isolation** in multi-client deployments: a hard boundary, with an
  automated test that proves one tenant's query cannot reach another's data. The
  test is the artifact security actually wants to see.

### Prompt injection

**The field's foremost unsolved security problem**, and the one most likely to be
asked about in a review.

Malicious instructions hidden inside content the system reads — a retrieved
document, a web page, an email, a support ticket, a filename, a code comment,
even text rendered invisibly. The model cannot reliably distinguish instructions
placed there by the operator from instructions embedded in data, because both
arrive as text.

The attack matters in direct proportion to what the system can *do*. An injection
against a read-only assistant produces a wrong answer. An injection against an
agent with write access to a ticketing system, an email client, or a database
produces an incident.

**Mitigations, all partial, applied in layers:**

| Control | Effect |
|---|---|
| Treat all retrieved and user-supplied content as untrusted **data**, never instruction | Framing that makes the rest of the controls coherent |
| Explicit delimiting of injected content | Reduces, does not eliminate, instruction confusion |
| Tool allow-lists per context | Bounds what a successful injection can reach |
| Least privilege on every tool | The primary structural control — see below |
| Human approval on any external effect | The only reliable control for high-consequence actions |
| Output scanning before display or action | Catches leaked instructions and exfiltration attempts |
| Never placing secrets in prompts or system instructions | Removes the highest-value target |
| Isolating untrusted content from privileged capability in separate steps | Limits the blast radius by design rather than by detection |

The honest position, and the correct one to state in a review: prompt injection
is **not solved**, so systems are designed such that a successful injection is
survivable. That is a design posture, not a filter.

### Least privilege, enforced in code

The single most important control in agentic systems.

A model cannot be instructed into safety. Prompt-level restrictions — "never
delete anything" — are guidance, not enforcement, and adversarial input routinely
defeats them. The enforcement point is the executing program: if a tool does not
exist in the current context, or the credential it uses lacks the permission, no
sequence of tokens can produce the action.

In practice: read-only by default; write operations scoped to specific records
and specific fields; destructive operations either absent or behind human
approval; separate credentials per tool with minimum scope; and an explicit
inventory of every action the system can take, reviewed by security.

### Secrets and data handling

Secrets in a managed vault, injected as environment variables, rotated,
never in code, configuration files, prompts, logs, or traces. Trace and log
redaction configured before production, since observability tooling captures
inputs and outputs by design and will happily store personal data indefinitely.

**Data residency and provider boundaries.** Enterprises consume frontier models
through tenanted services within their own cloud subscription rather than public
endpoints, specifically so that content does not leave the tenant and is not
retained or used for training. Where a public endpoint must be used, the terms
covering retention and training are a compliance artifact, not a footnote.

---

## Guardrails

Programmatic checks on the way in and the way out, independent of the model.

### Input guards

| Guard | Purpose |
|---|---|
| Injection detection | Flags known instruction-override patterns |
| PII detection and redaction | Prevents personal data reaching the model or the logs unnecessarily |
| Topic and scope filtering | Rejects out-of-scope requests before spending a model call |
| Abuse and toxicity filtering | Policy compliance |
| Size and rate limits | Cost control and denial-of-service protection |

### Output guards

| Guard | Purpose |
|---|---|
| Schema validation | The output is parseable and complete before anything downstream consumes it |
| Grounding check | Every claim follows from the retrieved evidence |
| Citation enforcement | Answers without valid, verifiable sources are rejected rather than shown |
| Secret and PII leak detection | Nothing sensitive is returned |
| Policy compliance | Regulated domains: no advice the organisation is not licensed to give |
| Confidence gating | Low-confidence responses route to a human instead of being displayed |

### Fallback behaviour

Every guard needs a defined, tested response when it trips: a graceful refusal
with a route to a human, a retry with a modified prompt, or an escalation.
**Failing closed is a feature; failing open is an incident.** The refusal path
belongs in the test suite with as many cases as the happy path, because a system
that over-refuses is unusable and one that under-refuses is dangerous, and only
tests distinguish them.

---

## Human-in-the-loop

The mechanism by which risky automation ships at all. The posture is chosen per
*action*, not per system.

| Posture | Applies when | Cost |
|---|---|---|
| **Fully automated** | Low consequence, high volume, reversible, well-measured | Lowest; requires the highest quality bar |
| **Human approves before execution** | Any external effect — sending, paying, modifying a record, contacting a customer | Adds latency and headcount; converts an unacceptable error rate into an acceptable one |
| **Human performs, system assists** | High consequence or high ambiguity; the system drafts, the person decides | Highest; also the fastest route to deployment in regulated settings |
| **Escalation on uncertainty** | Hybrid — automated when confident, routed when not | Requires a calibrated confidence signal, which is non-trivial |

Approval steps impose an architectural requirement: workflow state must persist
across a pause of arbitrary length and survive a restart. Designing for that at
Stage 2 is cheap; retrofitting it is not.

**Automation bias** is the failure mode of human-in-the-loop. Reviewers presented
with a confident, well-formatted recommendation approve it without genuine
scrutiny, and the control becomes ceremonial. Countermeasures: show the
supporting evidence rather than only the conclusion, surface uncertainty
explicitly, sample-audit approvals against ground truth, and rotate reviewers.

---

## Audit and explainability

### The audit log

An immutable, append-only record. In regulated sectors this is not negotiable,
and its absence blocks deployment outright.

Per request: timestamp, user identity, the input, the retrieved sources with
identifiers and versions, the model and version invoked, the parameters used,
every tool called with its arguments and result, the final output, every guard
that triggered, any human approval with identity and timestamp, and the outcome.

Retention per the organisation's policy — frequently years. Written to storage
the application cannot modify. Queryable, because its purpose is answering
"what happened on the fourteenth?" under time pressure.

### Explainability

Different from interpretability. Nobody is explaining the model's internals; the
requirement is that **every output can be traced to the evidence and steps that
produced it**.

- **Citations surfaced to the user**, not buried in a log — the mechanism by
  which a user can verify rather than trust.
- **The reasoning path** available for multi-step systems: which tools ran, in
  what order, with what results.
- **A stated scope**: what the system is authorised to answer and what it is not,
  visible in the interface rather than only in documentation.

---

## Compliance

### Common obligations

| Obligation | Practical effect |
|---|---|
| **Data residency** | Model and storage must be in a specified region; constrains provider and deployment choice |
| **Retention and deletion** | Personal data must be deletable on request — including from the vector index, the cache, and the trace store, which are routinely forgotten |
| **Purpose limitation** | Data collected for one purpose cannot be repurposed as training or retrieval material without a basis |
| **Right to explanation** | Automated decisions affecting a person must be explainable and appealable |
| **Sector rules** | Financial advice, medical guidance, and legal opinion have licensing requirements a system cannot satisfy — hence hard refusal paths |
| **Record keeping** | Audit logs retained for a defined statutory period |

Emerging AI-specific regulation generally scales obligation with risk: systems
affecting people's rights, livelihood, or safety carry documentation,
human-oversight, and monitoring requirements that low-risk internal tooling does
not. The practical planning assumption is that **anything customer-facing or
decision-affecting will attract documentation and oversight obligations**, and
that building the audit trail and the model card from Stage 7 is far cheaper than
reconstructing them under review.

### The model card

A standing document describing the deployed system. Requested by review boards,
auditors, and incoming engineers alike.

Purpose and intended use · out-of-scope uses · model and version, with the
criteria for changing it · data sources and their provenance · evaluation
methodology and current results · known limitations and failure modes ·
performance across relevant population segments · human oversight arrangements ·
monitoring in place · owner and review date.

---

## Fairness

Where a system affects people — hiring, credit, claims, prioritisation of
service, eligibility — differential performance across groups is a governance
issue rather than an engineering curiosity.

The obligations are concrete: evaluate performance by segment rather than in
aggregate, since an 85% average can conceal 95% for one group and 60% for
another; document differences found and what was done about them; provide an
appeal route to a human for anyone affected; and state plainly what the system is
not authorised to decide.

---

## Reliability as a risk control

Availability is a governance concern once a system is embedded in a workflow.

Timeouts on every external call. Retries with exponential backoff for transient
failures and rate limits. Circuit breakers, so a failing dependency degrades one
feature rather than the whole system. Graceful degradation — a fallback model, a
cached response, or an honest unavailable message, never a hung request. Rate
limits per user and per tenant. **Cost caps that actually stop spending**, since
a runaway loop against a metered API is a financial incident. Idempotency on
anything retryable, so a retry does not duplicate an effect.

---

## Incident response

AI incidents are a recognised category: a harmful or incorrect output at scale, a
data exposure, a successful injection, a cost runaway, a quality collapse after a
silent model update.

The response plan needs: detection (what alerts, on what threshold), a kill
switch (feature flag or traffic cut, tested), rollback (configuration and prompt
reverts, which are the more common cause of regression than code), a
communication path, an evidence trail — the audit log — and a post-incident
review whose output includes a new golden-set entry so the same failure is caught
automatically thereafter.

---

## The review gates

| Review | Owner | Wants to see | Typical lead time |
|---|---|---|---|
| **Architecture review** | Architecture board | Design conformance to organisational standards | 1–2 weeks |
| **Security review** | Security | Data-flow diagram, threat model, controls, tool inventory, isolation test | 2–6 weeks |
| **Privacy assessment** | Privacy officer | What personal data is processed, on what basis, where it is stored, how it is deleted | 2–4 weeks |
| **Compliance review** | Compliance / legal | Regulatory mapping, refusal paths, audit and retention, explainability | 2–6 weeks |
| **Operational readiness** | Platform / SRE | Runbook, monitoring, SLOs, rollback, on-call ownership | 1–2 weeks |

These run partly in parallel, and their lead times are the reason Stage 7 is
measured in months rather than weeks. The single most effective preparation is to
**ask each reviewer at Stage 2 what they will need to approve**, and build the
evidence alongside the system rather than assembling it retrospectively.
