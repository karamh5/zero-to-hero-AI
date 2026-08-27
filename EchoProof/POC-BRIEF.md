# EchoProof
## A Compliance Assurance Layer for Enterprise Voice AI

**Status:** PoC complete, demonstrated August 2026.
**Author:** Karam Hammouda, AI Launchpad Summer 2026.

This brief defines the scope, results, customer pipeline, architecture, data
strategy and roadmap for EchoProof, a pre-deployment compliance assurance layer
for enterprise voice AI agents.

---

## 1. PoC Overview

**Industry.** Financial services, launching in collections and consumer lending.
The engine is industry agnostic. The go to market is not.

**Use case.** Before a voice agent takes real calls, someone has to answer
whether it says, omits, or commits to anything that violates the law or the
company's own policy. Today that answer comes from a person listening to sample
calls, or from a testing platform scoring against a generic rubric that has
never read the client's policy documents.

**What EchoProof does.** It reads a transcript of a conversation the agent has
already had, extracts every factual claim and commitment the agent made,
retrieves the one governing provision from the client's own policy corpus, and
issues a verdict carrying that exact section identifier. Money and dates are
verified in code rather than by a model.

> **Read this twice, because it is the single most misunderstood point.**
> EchoProof does not place calls. It does not sit in the live call path, and it
> never speaks to a customer. Test conversations are produced the way the client
> already produces them, or generated from the client's scenarios and personas.
> EchoProof automates the **judging** step, not the calling step.

**What comes out.** A Deployment Readiness Report where every finding carries
the transcript excerpt, the audio clip of that exact sentence, the retrieved
rule text, the section number, and an integrity hash.

### End user archetype

- Chief Compliance Officer and compliance operations, the economic buyer
- Risk and model governance owners who need a filable artifact, not a dashboard
- Contact centre and voice engineering teams running a release gate
- Delivery teams attaching a readiness gate to voice engagements
- IT and InfoSec, who approve but do not buy

### Core capability

| Capability | State |
|---|---|
| Citation grounded judge, verdict pinned to an exact section and document version | Built |
| Deterministic money and date verification, executed in code ahead of any model call | Built |
| Five state verdict with routed abstention | Built |
| Hash chained, append only evidence log | Built |
| Audio evidence citation down to the exact sentence | Built |
| Deployment Readiness Report as a self contained, emailable artifact | Built |
| Fix and re-run regression loop, with the delta recorded when a finding closes | Built |
| Four statutory trigger caller personas with drift validators | Built |
| Required disclosure detection | Presence only. Meaning, placement, completeness and intelligibility are designed and deferred |
| Escalation correctness | Designed, not built |
| Policy gap list from abstentions | Designed. Requires retrieval floor recalibration before it produces meaningful output |

The five verdict states are `supported`, `contradicted`, `no_governing_rule`,
`retrieval_below_confidence` and `conflicting_sections`. Keeping
`no_governing_rule` separate from `retrieval_below_confidence` matters, because
merging them turns a retrieval miss into a false claim that the client's rulebook
has a gap.

### Market and opportunity

The exposure is concrete rather than projected. Under FDCPA 1692k, statutory
damages attach per action, with class exposure capped at the lesser of $500,000
or one percent of net worth. Regulation F attaches required disclosures with
timing constraints to individual calls. That is a compliance budget that already
exists rather than one that has to be created.

The broader market is roughly $3.5B in 2026, with forecasts near $35B by 2033.
Every one of those deployments is a governance sign off waiting to happen.

The near term commercial driver is **deal cycle compression**. Enterprises
currently build their own test harness during technical validation, which stalls
voice deals for months. A ready made, neutral harness shortens that cycle.

### Market trend and insight

- **OpenAI launched Presence in July 2026**, which validates the category and
  confirms the buyer exists. It is OpenAI only and cannot certify a cascaded
  stack, which is the majority of enterprise voice deployments and the white
  space here.
- **Existing voice testing platforms score behaviour against generic rubrics.**
  None of them read the client's policy documents, so none can produce a section
  identifier as evidence.
- **Deepgram applied engineering confirmed** no customer they are aware of runs
  a compliance layer around their agent's LLM. Deepgram has since expressed
  interest in positioning EchoProof as an official third party service to their
  customer base.
- **Validated internally as a compliance layer under AgentVerse**, where the
  assurance layer makes the voice agent more sellable and the voice agent creates
  demand for the assurance layer.
- **The most underrated competition is tooling already inside the client's
  bill**, specifically Bedrock Evaluations and Azure AI Foundry, plus the
  client's own platform team, who will build a partial version in a quarter.
  Deal cycle compression is the argument against both.

---

## 2. Results

Metric definitions, denominators, the labelling protocol and the held out split
were frozen before any run. The held out split was sealed, scored once, and
examined only at the end.

### What the PoC demonstrated

| Result | Value |
|---|---|
| Citation precision, the rule cited is the governing one | **0.75 to 0.83** |
| False positives on the compliant control scenario, three runs | **Zero** |
| Pack swap to a different industry's standard | **5 of 5 seeded violations detected and cited, no engine change** |
| Evidence chain verification | **Passes on every run** |
| Fix and re-run | **Closes a finding and records the delta** |
| Measured campaign cost | **$0.82 for an 18 call campaign**, roughly $23 per 100 calls |
| Proxy overhead | **0.129 ms** against a 50 ms budget |

Citation precision is the diagnostic that matters most commercially, because a
correct verdict citing the wrong section has failed at the thing being sold.
Zero false positives on the compliant control matters just as much: the system
does not invent violations.

### Positioning, stated plainly

**EchoProof is a triage layer that routes to human review. It is not an
unattended release gate.** Every item arrives with the governing rule already
quoted beside it, so a reviewer confirms or overturns in seconds rather than
minutes, across every turn rather than a one to five percent sample. Raising it
to an unattended gate is a roadmap objective, and the reviewed-decision loop in
section 6 is the mechanism for getting there.

The full per stage measurement set, including where the system is weakest and
why, is maintained in `LIMITATIONS.md` in the repository. It is written for
engineers and reviewers rather than for buyers, and it is deliberately complete.

### Business metrics to validate in pilot

- Deal cycle compression, measured as time from technical validation to
  production sign off against the baseline of a client building their own harness
- Human review time per report, the buyer's real return metric
- Findings caught before go live rather than after
- Attach rate to existing voice engagements
- Willingness to pay. Pricing hypotheses, **unvalidated**: $60k to $90k as a
  pre-production gate attached to an existing engagement, $90k to $150k
  standalone, $150k to $250k per year for continuous assurance

---

## 3. Customer Pipeline

**Company A. US collections or consumer lending operator.**
$500M to $10B revenue, agency, debt buyer, or bank collections division. United
States. Deal hypothesis $90k to $250k. Voice agents scoped or piloted. Any
cascaded stack. Qualifier: a named compliance budget owner and section numbered
policy documents, which examiners already require.

**Company B. Banking and financial services voice engagement.**
Enterprise, existing AgentVerse or contact centre pursuit. US and Europe. Deal
hypothesis $60k to $90k attached as a pre-production gate. High AI readiness.
AWS Bedrock with a partner speech layer.

**Company C. European telecom running a cascaded voice stack.**
Enterprise, Europe. $60k to $150k initial engagement. Third party STT, Bedrock
inference, third party TTS, which is the architecture single vendor tooling
cannot certify.

**Key stakeholders.** Chief Compliance Officer and compliance operations own the
budget. CIO, CTO and risk owners determine whether it is fundable at all.
General Counsel determines whether the artifact is safe to generate. InfoSec
approves the deployment model, which is why running inside the client's own
account matters.

---

## 4. Technology Architecture

### Fixed engine, swappable data

The engine is adapter, extractor, deterministic checks, retriever, judge,
evidence log, aggregator and report. It contains no field that knows which
industry it is running in. Everything client specific lives in four data packs.

| Pack | Contents |
|---|---|
| **Policy** | The client's documents and sections, with stable section identifiers, verbatim text, obligation type, cross references and defined terms |
| **Scenario** | Test cases, including required utterances, escalation obligations, and ground truth for seeded violations |
| **Persona** | How the caller behaves and which statutory trigger fires, kept separate from the scenario so any persona can run any scenario |
| **Criteria** | The client's own severity map, gate thresholds and abstain routing, which is what keeps a hardcoded standard out of the engine |

Expanding into a new industry means writing new data files rather than
rebuilding the product. The pack swap demonstration proves this by loading a
corpus with different section numbering conventions with no engine change.

### The pipeline

A transcript arrives. A claim extractor returns each claim as a **verbatim quote
resolved to character offsets** in code, never as restated text. Deterministic
checks run on money and dates ahead of retrieval. Retrieval pulls the governing
section. The judge rules from the retrieved text alone. The finding is written to
a hash chained evidence log with an audio clip attached. The report is generated.

Two constraints carry the product:

1. **The judge only ever sees the retrieved rule text**, never the rest of the
   corpus and never its own training knowledge. That makes every verdict
   falsifiable by reading that text, and it makes a wrong verdict attributable to
   either retrieval or judgment rather than unattributable.
2. **The extractor returns offsets rather than restated text**, which makes the
   audio citation deterministic instead of a fuzzy match that would fail hardest
   on the hedged turns that matter most.

### The attachment point

EchoProof presents a **standardized endpoint** that any agent stack already
speaks. Two routes:

| Route | Purpose |
|---|---|
| `POST /v1/chat/completions` | Compatible passthrough, captures the turn as it passes |
| `POST /v1/transcripts` | Accepts a turn directly, which is what makes a **speech to speech stack assessable at all**, since there is no text model call to sit in front of |

Adjudication runs on a worker thread. The response goes back to the caller
unmodified and is never delayed, so a capture failure cannot become a request
failure. That is enforced by tests.

Avoid the phrase "OpenAI compatible proxy" with buyers. It reliably causes people
to conclude they must be running OpenAI agents, which is the opposite of the
claim being made.

### MVP and production

Same pipeline, same interfaces, cheaper backends. Every substitution is a
configuration change rather than a rewrite.

| Layer | MVP, built | Production, designed |
|---|---|---|
| Models | Mistral through a compatible endpoint, single model interface, temperature 0 | Bedrock, tiered routing. NVIDIA NIM for in-VPC serving |
| Retrieval | Local FAISS and BM25 behind the retriever interface | OpenSearch hybrid plus rerank |
| Orchestration | Sequential Python runner | LangGraph campaign runner |
| Evidence store | Content addressed files on disk, same hash chain | S3, object lock, KMS signed |
| Run and findings data | Supabase | Postgres with pgvector |
| Observability | Spans written locally and rendered into the report | OTel spans to the client's collector |
| Speech | Nova-3 on recorded audio, word level timestamps | Nova-3 streaming, Aura-2 persona voices |
| Deployment | Local | Client VPC, infrastructure as code |

The model backend that produced the reported numbers is the same backend used in
the demonstration. No swap after fixtures are scored.

### Where NVIDIA fits

- **NIM.** In-VPC serving of the extractor and judge for clients who will not
  send policy text or call content to a hosted model. A procurement unlock rather
  than a performance optimisation.
- **NeMo Guardrails.** Complementary rather than competing. Guardrails try to
  prevent the agent saying the wrong thing at runtime. EchoProof adjudicates what
  it actually said, with a section attached, before release.
- **NeMo.** Synthetic data generation for expanding the fixture and scenario sets
  beyond the hand authored set.

### Key technical requirements

- AWS native, client VPC deployment
- Proxy overhead under 50 ms against a voice loop budget of roughly 800 ms, with
  the judge running out of band so the tool is never a production availability
  dependency
- 100 call campaign per release cycle, roughly 25 agent turns per call
- No production data required in pre-deployment mode, RBAC on findings, full
  decision traceability, hash chained evidence
- Audio capture with text adjudication

### Out of scope, permanently rather than deferred

- Speech to text and text to speech quality. Commoditised, and not independently
  verifiable without cross referencing another speech vendor.
- Background noise and acoustic testing. Solved at the model layer and shipped by
  every competing platform.
- **Real time blocking in the decision path.** Retrieval plus reranking plus
  judgment is measured in seconds. A voice turn budget is measured in
  milliseconds. It cannot sit on the speech path, and accepting it would take on
  production SLA liability where the first dropped call attributable to the tool
  loses the account. Section 6 describes the latency honest alternatives.
- Indemnification of missed violations.

**Healthcare is no longer out of scope.** It was excluded in the original brief.
Demand surfaced directly in the August review, both for insurance and for NHS
style triage, where decisions follow a strict questionnaire and policy set and
auditability is the requirement rather than a feature. The engine is already
industry agnostic; entering healthcare is a policy pack, a HIPAA posture review,
and a deployment model conversation.

---

## 5. User Interface

**Deployment Readiness Report.** A self contained HTML file generated from the
evidence log. No server, no login, nothing to deploy. It opens in a browser and
can be emailed to a compliance officer or attached to a risk review.

- **Header.** Agent version, policy pack version, run date, coverage statement,
  gate decision
- **Summary.** Finding counts by severity and verdict state, with abstentions
  broken out separately from violations
- **Finding card.** Verdict, severity, the claim highlighted in its transcript
  excerpt, a play control on the audio clip of that exact sentence, the retrieved
  rule text with its section identifier, and the integrity hash
- **Expandable trace.** The claim extracted, the retrieval candidates with
  scores, the section selected, and the verdict with rationale. This is what
  allows a contested finding to be root caused, since agent error, retrieval
  error and judge error look identical in the output and completely different
  underneath
- **Fix and re-run view.** The same scenario before and after, with the delta

Chosen over a hosted dashboard deliberately. It costs a fraction of the build
time, there is nothing to fail during a live demonstration, and it produces an
artifact a compliance officer can file rather than a dashboard they log into.

**Run console.** A thin operator surface for launching an assessment, selecting
scenarios and personas, watching findings arrive, and triggering a re-run. Built
on the same evidence log. Operator convenience rather than the deliverable.

**What happens to a finding.** Findings are triaged and grouped by root cause,
since one prompt defect usually produces many findings. A human reviewer
confirms, overturns or reclassifies, and every override is captured as structured
data. The agent vendor may dispute a finding, and the dispute attaches to the
evidence bundle rather than replacing it. Remediation is delivered with the
retrieved rule text, which is what makes a finding actionable rather than
alarming. The fixed scenario re-runs and the delta is recorded. The report is
hash sealed at a stated agent version and policy version, and changing either
voids it.

---

## 6. Roadmap

The product today diagnoses. The arc ahead is diagnose, repair, compound.

### Horizon 1. Diagnose. Live today.

Find the violation, cite the rule that governs it, seal the evidence.
Deliberately narrow to compliance against a client's own rulebook, because
general agent testing is already well served and compliance with a cited
provision is the part nobody filled.

### Horizon 2. Repair. Next.

- **Hunt the failure rather than sample it.** Search thousands of conversation
  paths for the ones that break, instead of testing a scripted handful.
- **Fix and prove.** Do not just flag the bad line. Rewrite the agent's
  instructions to remove that whole class of problem, then re-run everything to
  prove the fix held and nothing else broke. **The verification half of this loop
  already exists** in fix-and-rerun; what is missing is fix generation.
- **Automated policy ingestion.** The largest single post-PoC investment, roughly
  three to four engineer months, covering document parsing, section extraction,
  cross reference graph construction and version diffing. It attacks onboarding
  cost, time to value, and the leading disqualification reason at the same time.
- **Behavioural expansion.** Conduct under pressure, accents, interruptions,
  authentication flow. This is where it plugs into Agent V.

### Horizon 3. Compound. Then.

- **Every fix becomes a permanent test case**, so each client makes the next
  client's launch safer and the regression suite grows on its own.
- **Agents born compliant.** The rulebook generates the guardrails and the
  scaffolding, so an agent starts compliant instead of being tested into
  compliance.
- **Reviewed-decision loop.** Every human confirmation and overturn is labelled
  data, calibrating the judge to this client's reading of this rule. This is the
  mechanism that raises the system from triage toward an unattended gate.
- **Latency honest live assurance.** Not real time blocking. Two viable forms:
  gate the *consequence* rather than the sentence, validating before a payment
  plan, promise to pay or disclosure commitment is recorded; and run the full
  judge asynchronously alongside production traffic for a continuous compliance
  record with no added call latency.

### Adjacent opportunities raised in review

- **Human agent QA.** The input is a transcript and the engine does not know
  whether a model or a person produced it, so recorded human calls adjudicate
  identically. This turns EchoProof into a coaching and compliance record for
  frontline contact centre agents. Raised by the insurance and healthcare side,
  and it needs no architectural change.
- **Deepgram third party service.** Deepgram has expressed interest in offering
  EchoProof to their customer base as a way to de-risk deployments.
- **BPS alignment.** Voice solutions sit largely with BPS, and the AI Native
  Contact Center work is the natural internal channel.

---

## 7. Data Strategy

- **Primary corpus.** 12 CFR Part 1006, Regulation F, and the FDCPA. Public,
  authoritative, section numbered, dense with cross references and defined terms,
  with an explicit required disclosure regime carrying timing constraints. Using
  real public text removes the objection that the test was invented and then
  passed.
- **Synthetic control corpus.** Ten to fifteen rules using deliberately different
  section numbering conventions. Isolates retrieval failure from document
  structure failure, and supplies the pack swap demonstration.
- **Fixture set.** Hand authored seeded violations with a held out split defined
  before any run and authored off the engineering critical path.
- **Synthetic callers.** Four statutory trigger personas: cease communication
  request, attorney representation claim, debt dispute, and third party contact.
  Each is seeded and carries a drift validator. A persona that improvises outside
  its specification produces a call tagged invalid and retained rather than
  discarded, because the trace still carries diagnostic value.
- **No client data.** Pre-deployment scope means no production call content,
  which keeps the InfoSec review short.
- **Known dependency.** The citation promise assumes client documents carry
  stable section identifiers. Regulation F is clean because it is a federal
  register document, and real corporate policies often are not. Where they are
  not, structuring the corpus is a scoped data engineering step during
  onboarding, and it is exactly what automated policy ingestion is designed to
  remove.

---

## 8. Risks and Open Items

| Risk | Mitigation |
|---|---|
| Retrieval quality caps the entire product | Retrieval built and measured before the judge, with a gate check. Weak citation precision is fixed before any judge tuning. |
| Fixtures are single authored | The held out split is the only control against self tuning. Sealed, scored once, examined at the end. A second independent labeller is the next step and is a real gap today. |
| Real client policies lack section identifiers | Scoped data engineering during onboarding. Automated policy ingestion is the top roadmap item. |
| Client side model validation extends the sales cycle | A bank will treat the judge as a model used in a control capacity, which under SR 11-7 likely requires independent validation by their model risk team before production use. Shipping a validation documentation package shortens that step without removing it. Any pilot timeline that ignores it is wrong. |
| Report is discoverable in litigation | Privilege and filability are mutually exclusive. The default is the filable artifact, since that is what makes it a release gate. A privileged alternative is contracted through the client's outside counsel. The client selects at engagement start. |
| Speech to speech removes the intermediate transcript | **Resolved.** The transcript ingest path is built and tested. |
| Compound obligations can be failed by compliant text | A rule requiring two things in one sentence is split into two claims and each half is judged against the whole rule. Structural rather than a tuning problem. Fixing it means evaluating multi element obligations at turn level, which is designed and not built. |
| Throughput on the cross encoder | A hardware line item rather than a research problem. ONNX or GPU execution is the first production fix. |

---

## 9. What Changed Since the Original Brief

Recorded so the delta is legible rather than silent.

1. **The product ingests transcripts. It does not place calls.** The original
   brief described synthetic callers placing calls into the client's agent. That
   framing caused repeated confusion in review and has been corrected throughout.
2. **Speech to speech is handled, not a risk.** The transcript ingest path was
   built and verified during the PoC.
3. **Cost came in far below estimate.** Projected at $100 to $300 per 100 call
   campaign; measured at roughly $23.
4. **Healthcare moved from out of scope to demand led.**
5. **Deepgram third party service and human agent QA** were added as
   opportunities surfaced in review.
6. **A roadmap was added.** The original brief had a timeline but no product arc.
7. **Real time blocking is now explicitly and permanently out of scope**, with
   latency honest alternatives named in its place.
8. **Capability claims are marked built, presence only, or designed and not
   built**, rather than listed uniformly as features.
