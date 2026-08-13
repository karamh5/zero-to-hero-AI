# EchoProof — SPEC.md
Read only the section(s) a phase names. Engineering only, no business content.

## §1 Data pack schemas
Policy pack (per section): section_id, parent_section, verbatim_text,
obligation_type (requirement|prohibition|permission|definition),
cross_references, defined_terms.
Scenario pack (per case): scenario_id, description, required_utterances
(text_or_meaning + timing_trigger), escalation_conditions, seeded_violation,
ground_truth {verdict, section_id} for fixtures.
Persona pack: persona_id, statutory_trigger
(cease_communication|attorney_representation|debt_dispute|third_party_contact),
behavior_spec, drift_validator_rules.
Criteria pack: severity_map, gate_thresholds, abstain_routing.
Rule: a new vertical means new pack files. Engine code changing to add a
vertical is a bug in the engine/pack boundary.

## §2 Pipeline
adapter -> claim extraction (§3) -> deterministic checks (§4) -> retrieval
(§5) -> judge (§6) -> evidence log (§7) -> [audio, §8] -> report (§9).
The judge only ever sees retrieved text. The extractor returns offsets, never
restated text, because §8's audio citation depends on offsets mapping to
word tokens.

## §3 Claim extraction
Tool-calling output per claim: claim_id, claim_type (numeric|date|commitment|
policy_statement|implicit), char_start, char_end, normalized_value (numeric/
date only). Measure recall per claim_type, not aggregate — implicit
commitments are weakest and highest-liability.

## §4 Deterministic checks
Canonicalize spoken/written numbers ("thirty-five", "$35.00") and dates
(relative phrases anchored to call date) before comparing in code. The model
never judges whether values match. Own unit test suite, kept independent.

## §5 Retrieval
Structure-aware chunking on section boundaries, parent heading kept with each
chunk. Hybrid BM25 + dense, fused. Rerank top 50 down to the governing
section. Local FAISS+BM25 behind a retriever interface (OpenSearch is the
Production swap). Two distinct confidence thresholds: a floor below which
nothing plausibly matches -> no_governing_rule, and a ceiling above the floor
but not confident enough -> retrieval_below_confidence. These must stay
separate — merging them turns a retrieval bug into a false "no rule exists"
claim. Gate metric: precision@1 against the ~40 hand-written query/section
pairs (extend, don't discard).

## §6 Judge
Input: claim (via offset) + retrieved rule text + criteria threshold. Output:
verdict + rationale + section_id. Routing: deterministic claims already
checked by §4 -> supported/contradicted directly, no model re-judgment.
Retrieval floor uncleared -> no_governing_rule. Ceiling uncleared ->
retrieval_below_confidence. Two plausible conflicting candidates ->
conflicting_sections. Otherwise rule strictly from provided text. Also
handles: missing required disclosure (presence-only for MVP; meaning/timing/
completeness/intelligibility designed-and-deferred, mark as such) and failed
escalation (a retrieval question, not a hardcoded scenario flag).

## §7 Evidence log and spans
Append-only, hash-chained; each entry's hash includes the previous entry's
hash. Spans: call.session (scenario_id, persona_id, agent_version,
policy_pack_version, seed), agent.turn (audio_ref, transcript, word_timings,
stt_confidence), extract.claims (prompt_hash, model, raw_response, claims),
check.deterministic (value_parsed, expected_value, result), retrieve.rule
(query, candidates+scores, section_selected), judge.rule (claim_in,
rule_text_in, verdict, rationale), finding.emit (severity, audio_clip_ref,
evidence_bundle_ref, chain_hash). Every finding pins policy version, document
hash, model version, prompt hash, retriever config, seed. Reproducibility =
same stored inputs regenerate the same verdict, verified by recomputed hash.

## §8 Audio evidence and citation
Nova-3 word-level timestamps + claim extractor char offsets map
deterministically to word tokens, which slice the source audio via
ffmpeg/pydub — a clip of the exact flagged sentence, not the whole call.
Word-level confidence below threshold on a numeric token -> abstain, not a
finding. Adjudication stays text-only; audio is bolted on after the verdict
exists, never an input to it.

## §9 Report generator
Self-contained HTML from the evidence log, no server, opens in a browser.
This is the defined UI deliverable for this PoC, treated as backend output.
Header (agent/policy version, run date, coverage, gate decision), summary
(counts by severity/verdict, abstains separate), finding card (verdict,
severity, highlighted transcript excerpt, audio play control, rule text +
section_id, integrity hash), expandable trace (claim, retrieval candidates,
section, verdict+rationale), fix-and-rerun view (before/after delta).
Hash-sealed at agent_version + policy_pack_version; changing either must
visibly break the seal.

## §10 Orchestration
Sequential runner: pick scenario+persona -> run call (proxy auto-captures,
not hand-fed) -> transcribe with timings -> validator checks persona stayed
on script (drifted calls are tagged invalid and retained, not discarded, then
re-run) -> judge walks each turn -> repeat same scenario+seed 3x (locked
scope: 6 scenarios x 3 runs) -> aggregate pass@3 and pass^3 per scenario,
findings sorted by severity, unsupported claims into a policy-gap list.

## §11 Evaluation and fixtures
50-item seeded-violation set, text-only, held-out split sealed before any run
and scored exactly once, examined only at the end. False positives counted
only against hard negatives (real judgment turns, greetings excluded).
Report a precision-recall curve, not a single accuracy number. Decision bands
at <=2% FP on hard negatives: >90% viable, 80-90% viable with human review,
70-80% retrieval is the bottleneck, <70% reconsider the corpus. Headline
validation: judge-human agreement on a 25-item blind subset, floor 85% — below
it, the report must state EchoProof is a triage layer, not a release gate.
Diagnostics per stage: citation precision@1, claim recall by type, abstain
rate/precision, reproducibility-by-hash.

## §12 Fix-and-rerun
Same scenario+seed re-run after a fix. Record which findings closed,
persisted, or are new. Same evidence-log format, same runner, called twice
with a diff step.
