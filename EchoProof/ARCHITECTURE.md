# EchoProof, architecture and design decisions

The standing design record for this project. Phase plans live in PHASES.md and
component detail lives in SPEC.md, so neither is duplicated here.

## What this is
A pre-deployment compliance assurance layer for enterprise voice AI agents. A
single OpenAI-compatible proxy sits in front of a client's voice agent's LLM
call. It extracts factual claims, retrieves the governing rule from a
client-supplied policy corpus, and issues a five-state verdict with an exact
citation, an audio clip, and a hash-chained evidence entry. Output is a
self-contained Deployment Readiness Report (HTML).

Current PoC corpus: Regulation F (12 CFR 1006 / FDCPA), debt collection
compliance. Chosen for stable section numbers and explicit, timed disclosures.

## Fixed engine, swappable data
This boundary is load bearing and is not violated.

Engine: adapter -> claim extraction -> deterministic checks -> retrieval ->
judge -> evidence log -> report. The engine has NO field, constant, or branch
that knows which industry it is running in. Everything client-specific is one
of four data packs (schemas in SPEC.md section 1): policy pack, scenario pack,
persona pack, criteria pack.

A Regulation F rule or an industry assumption appearing in engine code rather
than in a pack file is a defect, not a shortcut.

## Settled decisions
These are decided. They are cited by number in code comments throughout the
codebase, so the numbering is stable.

1. Retrieval is built and measured BEFORE the judge is tuned.
2. The judge sees ONLY the retrieved rule text passed to it that call. Never
   its own training knowledge, never the full corpus.
3. Money and dates are verified deterministically in code after canonical
   normalization. The model never compares numbers or dates.
4. Claim extraction uses tool-calling returning CHARACTER OFFSETS into the
   transcript. Never restated or paraphrased claim text.
5. Verdicts are exactly one of five states (below). Never pass/fail, never a
   sixth state.
6. Low-confidence or ambiguous cases route to abstention. A verdict is never
   forced in order to avoid an abstention.
7. Every model call, retrieval call, and finding writes a span to the
   hash-chained evidence log (SPEC section 7) before the feature is done.
8. One model interface (OpenAI SDK, OpenAI-compatible base_url). MVP = Mistral,
   temperature=0. Production = AWS Bedrock. The swap is a base_url + model
   string change only.
9. Whichever backend produced a scored run's numbers stays the backend for
   that run. No silent swap after fixtures are scored.
10. The fixture set has a held-out split. It is not read, logged, or optimized
    against until the phase that scores it.
11. Evidence artifacts are content-addressed hashed files on disk. Supabase
    holds run/findings metadata only, never evidence content.
12. Disclosed limitations beat hidden ones. Anything cut or simplified gets a
    one-line note saying so.

## Verdict states (exact strings)
supported | contradicted | no_governing_rule | retrieval_below_confidence | conflicting_sections

## Claim types (exact strings)
numeric | date | commitment | policy_statement | implicit

## Stack, MVP now vs. production later
| Layer | MVP (built) | Production (designed for) |
|---|---|---|
| Models | Mistral via OpenAI SDK | AWS Bedrock, tiered routing |
| Retrieval | Local FAISS + BM25, one retriever interface | OpenSearch, hybrid + rerank |
| Orchestration | Sequential Python runner | LangGraph campaign runner |
| Evidence store | Content-addressed files, hash chain | S3, object lock, KMS-signed |
| Run/findings data | Supabase | Postgres + pgvector |
| Observability | Local spans rendered into report | OTel spans to client collector |
| Speech | Nova-3 on recorded audio | Nova-3 streaming |

## Conventions
Python 3.11+, type hints everywhere, no bare except. No em dashes anywhere in
code, comments, or docs. Secrets only via .env, never hardcoded, never
committed.

## Engineering gates
Scope stays inside the current phase. A change that contradicts a settled
decision above gets raised rather than merged quietly. A phase is not done
until its stated verification has actually been run, and the held-out split
stays sealed until the phase that scores it. The evaluation backend is not
swapped mid-evaluation.

Anything UI, dashboard or demo-facing is out of scope by default. The HTML
report in SPEC section 9 is the one named exception, because it is a defined
backend deliverable.

`git push` is gated on a secret scanner run (gitleaks or truffleHog) against
the diff, with a clean result confirmed first. A key that reaches a commit has
to be rotated, so this gate is not a formality.
