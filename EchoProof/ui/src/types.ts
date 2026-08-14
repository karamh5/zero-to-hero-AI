/** Shapes served by api/ (see EchoProof/api/runsvc.py). Nothing here is
 * invented client-side; absent fields stay absent rather than defaulted. */

export const VERDICTS = [
  "supported",
  "contradicted",
  "no_governing_rule",
  "retrieval_below_confidence",
  "conflicting_sections",
] as const;

export type Verdict = (typeof VERDICTS)[number];

export const ABSTENTIONS: ReadonlySet<Verdict> = new Set([
  "no_governing_rule",
  "retrieval_below_confidence",
  "conflicting_sections",
]);

export interface Candidate {
  section_id: string;
  chunk_id: string;
  score: number;
  bm25_rank: number | null;
  dense_rank: number | null;
}

export interface Finding {
  claim_id: string;
  turn_id: string;
  verdict: Verdict;
  is_abstention: boolean;
  severity: string;
  section_id: string | null;
  rationale: string;
  claim_text: string;
  rule_text: string | null;
  char_start: number;
  char_end: number;
  candidates: Candidate[];
  offered_section_ids: string[];
  selected_score: number;
  model: string;
  prompt_hash: string;
  entry_hash: string;
  audio_clip_ref: string | null;
  has_clip: boolean;
  transcript?: string;
}

export interface RunSummary {
  run_id: string;
  /** The name whoever ran the assessment chose. Empty for runs made before
   * titles existed; the bench shows the identifier for those. */
  title: string;
  conversation_id: string | null;
  created_at: string | null;
  chain_ok: boolean;
  chain_error: string | null;
  seal_state: "intact" | "broken" | "unsealed" | "unverifiable";
  pack_id: string | null;
  agent_version: string;
  artifacts: {
    campaign: boolean;
    rerun: boolean;
    swap: boolean;
    scored: boolean;
    report: boolean;
  };
  clip_count: number;
  span_count: number;
  chain_head: string | null;
  turns: number;
  claims: number;
  violations: number;
  abstentions: number;
  supported: number;
  verdict_counts: Record<string, number>;
  deterministic_decisions?: number;
  policy_gaps?: number;
}

export interface CampaignScenario {
  scenario_id: string;
  persona_id: string;
  expected_section_id: string | null;
  is_control: boolean;
  caught: boolean[];
  pass_at_3: boolean;
  pass_cubed: boolean;
  drifted: number;
  false_positive_calls: number;
}

export interface Campaign {
  run_id: string;
  runs_per_scenario: number;
  turns_per_call: number;
  scenarios: CampaignScenario[];
  policy_gaps: unknown[];
  cache: { hits: number; misses: number; hit_rate: number };
  cost_usd: number;
  wall_clock_min: number;
}

export interface RerunDelta {
  scenario_id: string;
  seed: number;
  before_count: number;
  after_count: number;
  closed: { section_id: string; verdict: string }[];
  persisted: { section_id: string; verdict: string }[];
  new: { section_id: string; verdict: string }[];
  improved: boolean;
  before_agent_turns?: string[];
  after_agent_turns?: string[];
  before_findings?: { claim_id: string; section_id: string; verdict: string; rationale: string }[];
  after_findings?: unknown[];
}

export interface RunDetail extends RunSummary {
  gate: { label: string; kind: "block" | "review" | "pass"; reason: string } | null;
  retriever_config: Record<string, unknown>;
  thresholds: Record<string, number>;
  policy_gap_claims: Finding[];
  campaign: Campaign | null;
  rerun: RerunDelta | null;
  swap: { pack: string; results: unknown[] } | null;
}

export interface Span {
  span_type: string;
  span_id: string;
  payload: Record<string, unknown>;
  prev_hash: string;
  entry_hash: string;
}

export interface WordTiming {
  text: string;
  start: number;
  end: number;
  char_start: number;
  char_end: number;
  confidence: number;
}

export interface ClaimDetail {
  run_id: string;
  finding: Finding;
  turn: Span | null;
  turn_audio: Span | null;
  extract: Span | null;
  deterministic: Span[];
  retrieval: Span | null;
  judge: Span | null;
  emit: Span | null;
}

export interface PolicySection {
  section_id: string;
  parent_section: string | null;
  verbatim_text: string;
  obligation_type: "requirement" | "prohibition" | "permission" | "definition";
  cross_references: string[];
  defined_terms: string[];
  heading: string;
}

export interface CorpusDetail {
  pack_id: string;
  manifest: Record<string, unknown> & {
    label?: string;
    citation?: string;
    record_count?: number;
  };
  hierarchy_separators: string[];
  sections: PolicySection[];
  coverage: Record<string, { retrieved: number; cited: number }>;
  coverage_run: string | null;
}

export interface FixtureMetrics {
  run_id: string;
  source: string;
  violations: number;
  hard_negatives: number;
  detected: number;
  detection: number | null;
  false_positives: number;
  false_positive_rate: number | null;
  cited_correctly: number;
  citation_precision: number | null;
}

export interface Measurements {
  detection: {
    runs: FixtureMetrics[];
    ceiling: number | null;
    ceiling_source: string;
    low: number | null;
    high: number | null;
    citation_low: number | null;
    citation_high: number | null;
    note: string;
  };
  agreement: {
    data: {
      total: number;
      matched: number;
      raw_agreement: number;
      cohens_kappa: number;
      floor: number;
      meets_floor: boolean;
      positioning: string;
      by_verdict: Record<string, { agreed: number; disagreed: number }>;
      disagreements: { claim_id: string; judge: string; human: string }[];
    } | null;
    source: string;
    self_graded: boolean;
    self_graded_note: string;
  };
  latency: {
    data: {
      samples: { extract: number; retrieve: number; judge: number; claims: number; total: number }[];
      startup_seconds: number;
      median_total: number;
      worst_total: number;
      cache: { hits: number; misses: number; hit_rate: number };
    } | null;
    source: string;
  };
  proxy_overhead: {
    documented_median_ms: number | null;
    source: string;
    note: string;
  };
  campaign: {
    summary: {
      graded_scenarios: number;
      pass_at_3: number;
      pass_cubed: number;
      control_false_positive_calls: number;
      control_calls: number;
      calls: number;
      turns_per_call: number | null;
      cost_usd: number | null;
      wall_clock_min: number | null;
      cache: { hits: number; misses: number; hit_rate: number } | null;
    } | null;
    source: string;
  };
  chain_verification: { runs: Record<string, boolean>; all_verified: boolean };
}

export interface Criteria {
  criteria_id: string;
  severity_labels: string[];
  severity_map: Record<string, Record<string, string>>;
  gate_thresholds: Record<string, unknown> & {
    judge_human_agreement_floor?: number;
    below_agreement_floor_statement?: string;
  };
  abstain_routing: Record<string, string>;
}

export interface Availability {
  available: boolean;
  reason: string | null;
  stack_state: "cold" | "loading" | "ready" | "failed";
  stack_error: string | null;
  model_key_present: boolean;
  deepgram_key_present: boolean;
  queued: number;
}

export interface JobInfo {
  job_id: string;
  run_id: string;
  title?: string;
  conversation_id?: string | null;
  pack_id?: string | null;
  status: "queued" | "loading_stack" | "running" | "done" | "failed";
  error: string | null;
  result: {
    run_id: string;
    title?: string;
    claims: number;
    findings: number;
    supported?: number;
    abstentions: number;
    agent_turns?: number;
    customer_turns_skipped?: number;
    verdicts: { claim_id: string; verdict: Verdict; section_id: string | null; decided_by: string }[];
    cost_usd: number;
  } | null;
  event_count: number;
}

export interface ProgressEvent {
  seq: number;
  at: number;
  stage: string;
  detail: Record<string, unknown>;
}

export interface ConversationTurn {
  role: string;
  text: string;
  audio_ref?: string | null;
}

export interface PreparedConversation {
  conversation_id: string;
  title: string;
  summary: string;
  authored_category: string | null;
  turns: ConversationTurn[];
  agent_turns: number;
  customer_turns: number;
  has_deterministic: boolean;
  verified: boolean;
  observed_outcome: string | null;
  verdict_counts: Record<string, number>;
  findings: { claim_id: string; section_id: string | null; verdict: string }[];
  claims: number | null;
  verified_at: string | null;
  run_id: string | null;
  matches_authored: boolean | null;
}

export interface ConversationGroup {
  category: string;
  label: string;
  conversations: PreparedConversation[];
}

export interface ConversationPack {
  pack_id: string;
  count: number;
  verified_count: number;
  groups: ConversationGroup[];
  policy_label?: string;
  policy_citation?: string | null;
  provisions?: number | null;
}
