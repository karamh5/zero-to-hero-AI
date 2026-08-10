# Career Reference

Role definitions in the applied-AI market, what genuinely separates adjacent
titles, which skills have the longest half-life, and how the delivery pathway
maps onto the work.

---

## The roles

Job titles in this field are inconsistent between companies. What follows are the
underlying jobs; the title on the posting varies.

### AI Engineer / Applied AI Engineer

**Builds products on top of language models.** Retrieval systems, agents,
evaluation harnesses, backends, and enough frontend to ship an interface. The
model is a rented component; the engineering is everything around it —
orchestration, grounding, structure, latency, safety, and measurement.

Day to day: designing retrieval pipelines, writing and evaluating prompts,
wiring tools to agents, building eval harnesses, debugging traces, tuning
latency and cost, integrating with enterprise systems.

Core competencies: strong general software engineering, retrieval architecture,
agent control flow, evaluation discipline, API and backend work, observability.

### ML Engineer

**Trains and deploys models.** Data pipelines, feature engineering, training
loops, fine-tuning, serving infrastructure, and the operational lifecycle of a
model the organisation owns.

Day to day: dataset curation, training runs, benchmark design, hyperparameter
work, model serving, drift monitoring.

Core competencies: deeper mathematics and statistics, a training framework, GPU
and distributed-training practicalities, experiment tracking, model operations.

**The distinction that matters:** an AI Engineer's uncertainty is *"will this
system behave reliably?"*; an ML Engineer's is *"will this model learn the
thing?"*. Both write a lot of ordinary software.

### LLM Engineer

A specialisation within applied AI concentrating on retrieval quality,
fine-tuning, evaluation, and enterprise architecture. Currently one of the
tightest supply-demand ratios in the market, because the combination of
production retrieval depth and genuine evaluation discipline is rarer than either
alone.

### AI Platform Engineer

**Builds the internal tooling other engineers use to build AI.** Model gateways,
prompt registries, shared evaluation infrastructure, tracing platforms,
guardrail services, cost attribution.

Prominent in banks, telecoms, insurers, and large software organisations — places
with enough AI teams that letting each solve observability, routing, and
governance separately is untenable. The work is closer to platform engineering
than to modelling.

### Solutions Engineer / Forward-Deployed Engineer

**Builds proofs of concept with clients.** Deep customer contact, rapid
prototyping, and the translation of a business problem into a technical one and
back again. Effectively [the delivery pathway](ai-product-delivery.md) as a
full-time job, run repeatedly against different clients.

Distinguishing skills: scoping under ambiguity, communicating to non-technical
stakeholders, and knowing what to leave out. Common in AI consulting and at
product companies with complex enterprise deployments.

### AI Voice Systems Engineer

Specialisation around real-time spoken interaction: streaming transcription,
interruption handling, latency budgets measured in tens of milliseconds, and
telephony integration. A distinct discipline because latency engineering
dominates every other consideration. Growing quickly in contact-centre and field
operations settings.

### MLOps / LLMOps Engineer

The operational lifecycle. **MLOps** covers models the organisation trains: data
versioning, training pipelines, model registries, drift monitoring. **LLMOps**
covers prompt-orchestrated systems: prompt versioning, tracing, evaluation
pipelines, cost governance, routing. Most applied work in enterprises is the
second.

### AI Quality Engineer

A title that did not exist a few years ago. Owns evaluation as a discipline —
golden datasets, judge calibration, regression pipelines, production quality
monitoring. Its emergence reflects the market realising that shipping what cannot
be measured does not work.

---

## Comparison

| | AI Engineer | ML Engineer | Platform | Solutions / FDE |
|---|---|---|---|---|
| **Primary output** | A working AI product | A trained, served model | Tooling other teams use | A proof of concept and a decision |
| **Optimises for** | Reliability and user outcome | Model performance | Developer leverage | Speed to demonstrated value |
| **Depth needed in** | Retrieval, agents, evals, backend | Training, data, serving | Infra, APIs, observability | Breadth plus communication |
| **Maths intensity** | Low to moderate | High | Low | Low |
| **Stakeholder contact** | Moderate | Low | Low (internal) | Very high |
| **Typical employer** | Product companies, consultancies | Model-centric companies, research-adjacent | Large enterprises | Consultancies, enterprise SaaS |

---

## Choosing between them

The choice is best made from experience rather than from job descriptions. The
useful signal is which work is energising rather than merely tolerable:

**Toward applied AI engineering** — enjoying orchestration, product behaviour,
retrieval quality, user-facing latency, system architecture, and the puzzle of
making an unreliable component reliable.

**Toward ML engineering** — enjoying dataset curation, training runs, benchmark
design, GPU wrangling, and the puzzle of making a model learn something it
currently does not.

The two overlap enough that the first two years of either keeps the other open.
What does not stay open is a portfolio of half-finished breadth. **One complete,
measured, deployed system is worth more than three impressive-sounding
prototypes**, because the complete one can be discussed for an hour under
questioning and the prototypes cannot.

---

## Skills by half-life

Not all knowledge in this field ages at the same rate. Investment is best
weighted toward the top of this table.

| Half-life | Skills |
|---|---|
| **Decade+** | Software engineering fundamentals · systems design · debugging method · SQL and data modelling · statistics and the precision/recall trade-off · clear written communication · knowing when *not* to use a model |
| **Several years** | Evaluation methodology · retrieval architecture · agent control flow and state design · latency and cost engineering · security posture for AI systems · cloud fundamentals |
| **A few years** | Specific orchestration frameworks · specific vector stores · specific observability platforms · fine-tuning tooling · integration protocols |
| **Months** | Model names, context limits, pricing, leaderboard positions, the current best provider |

The common error is investing at the bottom of the table because it is the most
visible. Frameworks are learned in a week by anyone with the layer above them;
the reverse is not true.

---

## The capabilities that actually differentiate

Ranked by how rarely they appear together.

**1 · Evaluation discipline.** The habit of attaching a before-and-after number
to every claim. Rare, immediately visible in an interview, and the single
strongest signal of production experience. "It seemed better" and "faithfulness
went from 0.71 to 0.89 and here is the table" are not the same sentence.

**2 · Production retrieval depth.** Basic retrieval is commodity knowledge. What
is paid for is the ability to diagnose *why* retrieval is failing — extraction,
segmentation, exact-match blindness, ranking, position sensitivity — and to fix
the specific cause rather than trying things.

**3 · Agent reliability engineering.** Understanding that reliability comes from
constraining a model inside an explicit, observable workflow, and being able to
explain why a controlled state machine outperforms a single ambitious prompt.

**4 · Knowing when not to use a language model.** Recommending gradient-boosted
trees, a database query, or plain code where those are better is senior
judgement, and it is unusual enough to be memorable.

**5 · Latency intuition.** Understanding where time goes in a pipeline and which
stages can be overlapped — most sharply demonstrated in voice systems, where
streaming every stage collapses perceived response time by an order of magnitude
without reducing total work.

**6 · Security posture.** Being able to describe prompt injection accurately,
state honestly that it is unsolved, and explain a layered design that survives a
successful attempt.

**7 · Stakeholder translation.** Describing one result correctly to a sponsor, a
user, a security reviewer, and an operations team. Covered in
[stakeholders.md](stakeholders.md), and it is what separates an engineer who can
be sent to a client from one who cannot.

---

## Where the pathway maps onto the role

The delivery pathway is not consulting-specific. The stages are present in
product work too, compressed and renamed.

| Stage | In consulting | In a product company |
|---|---|---|
| 0–1 Intake, discovery | Client workshops, scoping | Product discovery, user research |
| 2 Design | Solution design, architecture review | Technical design document |
| 3 Data | Client data access and preparation | Corpus and eval-set construction |
| 4–5 Build, evaluate | PoC sprint | Feature build behind a flag |
| 6 Gate | Client demo and decision | Internal review and launch decision |
| 7 Hardening | Productionisation phase | Launch readiness review |
| 8 Pilot | Client pilot | Staged rollout |
| 9–10 Production, operate | Managed service or handover | Ongoing ownership |

An engineer who has run the full pathway once has the vocabulary for both
contexts. An engineer who has only built demos has the vocabulary for neither.

---

## Working practices that compound

**Attach numbers to claims.** Every improvement, every regression, every
estimate.

**Own the problem, not the ticket.** A ticket is not "the code that was
requested" but "the problem behind it, solved" — including tests, documentation,
and updating the record so the next person understands the decision.

**Estimate as a range with a review point**, then actually revise it early.
Silently missing an estimate is the failure; flagging drift on day one is
professionalism.

**Escalate blockers in hours.** The cost of a blocker is linear in how long it
is concealed.

**Write things down where they can be found.** Decisions on the ticket or in the
design document, not in a chat thread.

**Read failures rather than only metrics.** Sitting with fifty failed cases and
categorising them produces better decisions per hour than any other activity in
an AI project.

**Small, reviewable changes.** Nothing merged that its author cannot explain.

**Propose one specific, measured improvement.** The format that works, in any
organisation: *"I noticed [measured problem]. I would like to try [specific fix].
Roughly [estimate]. Worth it?"* It is concrete, it is bounded, and it converts an
engineer from someone who completes assigned work into someone who improves the
system — which is the distinction that decides promotions and return offers
alike.
