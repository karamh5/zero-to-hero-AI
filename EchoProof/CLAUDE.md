# EchoProof — CLAUDE.md
Persistent project constitution, loaded every session. Task instructions live
in PHASES.md; component detail lives in SPEC.md. Do not duplicate either here.

## What this is
A pre-deployment compliance assurance layer for enterprise voice AI agents. A
single OpenAI-compatible proxy sits in front of a client's voice agent's LLM
call. It extracts factual claims, retrieves the governing rule from a
client-supplied policy corpus, and issues a five-state verdict with an exact
citation, an audio clip, and a hash-chained evidence entry. Output is a
self-contained Deployment Readiness Report (HTML).

Current PoC corpus: Regulation F (12 CFR 1006 / FDCPA), debt collection
compliance. Chosen for stable section numbers and explicit, timed disclosures.

## Fixed engine, swappable data — never violate this boundary
Engine: adapter -> claim extraction -> deterministic checks -> retrieval ->
judge -> evidence log -> report. The engine has NO field, constant, or branch
that knows which industry it is running in. Everything client-specific is one
of four data packs (schemas in SPEC.md §1): policy pack, scenario pack,
persona pack, criteria pack. If you find yourself hardcoding a Regulation-F
rule or an industry assumption into engine code instead of a pack file, stop
and flag it.

## Non-negotiable decisions — do not re-litigate these
1. Retrieval is built and measured BEFORE the judge is tuned.
2. The judge sees ONLY the retrieved rule text passed to it that call. Never
   its own training knowledge, never the full corpus.
3. Money and dates are verified deterministically in code after canonical
   normalization. The model never compares numbers or dates.
4. Claim extraction uses tool-calling returning CHARACTER OFFSETS into the
   transcript. Never restated or paraphrased claim text.
5. Verdicts are exactly one of five states (below). Never pass/fail, never a
   sixth state.
6. Low-confidence or ambiguous cases route to abstention. Never force a
   verdict to avoid an abstain.
7. Every model call, retrieval call, and finding writes a span to the
   hash-chained evidence log (SPEC §7) before the feature is done.
8. One model interface (OpenAI SDK, OpenAI-compatible base_url). MVP = Mistral,
   temperature=0. Production = AWS Bedrock. The swap is a base_url + model
   string change only.
9. Whichever backend produced a scored run's numbers stays the backend for
   that run. No silent swap after fixtures are scored.
10. The 50-item fixture set has a held-out split. Never read, log, or optimize
    against it unless a phase explicitly says the held-out run has arrived.
11. Evidence artifacts are content-addressed hashed files on disk. Supabase
    holds run/findings metadata only, never evidence content.
12. Disclosed limitations beat hidden ones. Anything cut or simplified gets a
    one-line note saying so.

## Verdict states (exact strings)
supported | contradicted | no_governing_rule | retrieval_below_confidence | conflicting_sections

## Claim types (exact strings)
numeric | date | commitment | policy_statement | implicit

## Stack — MVP now vs. Production later
| Layer | MVP (build this) | Production (design for, don't build) |
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
committed — the repo is public.

## Never do these without asking first
Touch anything UI/dashboard/demo-facing (the HTML report in SPEC §9 is the one
named exception). Expand scope beyond the current phase. Introduce a decision
that contradicts this file — flag it instead. Mark a phase done without
running its real verification. Read the held-out split early. Swap backend
mid-evaluation.

Never run `git push` without first running a secret scanner (gitleaks or
truffleHog) against the diff and confirming a clean result. If the scanner is
not installed, stop and ask before installing it or pushing. The repo is public
and a key that reaches a commit has to be rotated, so this gate is not optional
and not a formality.
