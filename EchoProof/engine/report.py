"""Deployment Readiness Report (SPEC section 9).

One self-contained HTML file. No server, no login, no external asset of any
kind. It opens in a browser, it can be emailed to a compliance officer, and it
can be filed. That was chosen over a hosted dashboard deliberately: it costs a
fraction of the build, there is nothing to fail during a live demonstration, and
a compliance function files artifacts rather than logging into tools.

**Everything here is read from the evidence log.** Nothing is re-judged,
re-retrieved or recomputed. If a number appears in this report it came from a
span written when the decision was made, which is the difference between an
auditable artifact and a second opinion.

The chain is verified before rendering, because `EvidenceLog.read` verifies on
load. A tampered log raises rather than rendering.
"""

from __future__ import annotations

import base64
import html
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.hashing import hash_object, short
from engine.evidence import (
    SPAN_AGENT_TURN,
    SPAN_EXTRACT_CLAIMS,
    SPAN_FINDING_EMIT,
    SPAN_JUDGE_RULE,
    SPAN_RETRIEVE_RULE,
    EvidenceLog,
)

CONTRADICTED = "contradicted"
SUPPORTED = "supported"
NO_GOVERNING_RULE = "no_governing_rule"
ABSTENTIONS = {"no_governing_rule", "retrieval_below_confidence", "conflicting_sections"}

# Inline audio is what makes a clip playable in a file with no server. It also
# inflates the file, which is stated in the report's own limitations rather than
# discovered by whoever tries to email a hundred-call report.
MAX_INLINE_CLIP_BYTES = 4 * 1024 * 1024


@dataclass
class Finding:
    """One adjudicated claim, assembled from its spans."""

    claim_id: str
    turn_id: str
    verdict: str
    severity: str
    section_id: str | None
    rationale: str
    claim_text: str
    rule_text: str | None
    transcript: str
    char_start: int
    char_end: int
    candidates: list[dict[str, Any]] = field(default_factory=list)
    offered_section_ids: list[str] = field(default_factory=list)
    selected_score: float = 0.0
    model: str = ""
    prompt_hash: str = ""
    entry_hash: str = ""
    audio_clip_ref: str | None = None
    clip_path: Path | None = None

    @property
    def is_abstention(self) -> bool:
        return self.verdict in ABSTENTIONS


@dataclass
class ReportData:
    """Everything the renderer needs, extracted once from the log."""

    run_id: str
    chain_head: str
    agent_version: str
    policy_pack_version: str
    policy_citation: str
    findings: list[Finding]
    turns: dict[str, str]
    generated_at: str
    span_count: int
    retriever_config: dict[str, Any] = field(default_factory=dict)
    thresholds: dict[str, Any] = field(default_factory=dict)

    @property
    def violations(self) -> list[Finding]:
        return [f for f in self.findings if f.verdict == CONTRADICTED]

    @property
    def abstentions(self) -> list[Finding]:
        return [f for f in self.findings if f.is_abstention]

    @property
    def policy_gaps(self) -> list[Finding]:
        """Only floor failures. Established in Phase 1 and load bearing.

        A judge rejecting the sections it was shown is a retrieval failure and
        routes to human review. Only an uncleared retrieval floor, meaning
        nothing in the corpus was even plausible, asserts that the client's
        rulebook has a gap.
        """
        return [f for f in self.findings if f.verdict == NO_GOVERNING_RULE]

    def seal(self) -> str:
        """The hash seal from SPEC section 9.

        Covers the agent version, the policy pack version and the evidence chain
        head. Changing any of the three changes the seal, which is exactly the
        requirement that altering a version visibly breaks it.
        """
        return hash_object(
            {
                "agent_version": self.agent_version,
                "policy_pack_version": self.policy_pack_version,
                "chain_head": self.chain_head,
            }
        )


def extract_report_data(
    log: EvidenceLog,
    agent_version: str,
    policy_pack_version: str,
    policy_citation: str,
    clips_dir: Path | None = None,
) -> ReportData:
    """Assemble findings by joining spans on claim_id."""
    turns: dict[str, str] = {}
    claim_index: dict[str, dict[str, Any]] = {}
    retrievals: dict[str, dict[str, Any]] = {}
    emits: dict[str, dict[str, Any]] = {}

    for span in log.spans:
        payload = span.payload
        if span.span_type == SPAN_AGENT_TURN:
            turns[str(payload.get("turn_id"))] = str(payload.get("transcript", ""))
        elif span.span_type == SPAN_EXTRACT_CLAIMS:
            for claim in payload.get("claims", []):
                claim_index[str(claim["claim_id"])] = {
                    **claim,
                    "turn_id": str(payload.get("turn_id", "")),
                }
        elif span.span_type == SPAN_RETRIEVE_RULE:
            retrievals[str(payload.get("claim_id"))] = payload
        elif span.span_type == SPAN_FINDING_EMIT:
            emits[str(payload.get("claim_id"))] = payload

    findings: list[Finding] = []
    retriever_config: dict[str, Any] = {}
    thresholds: dict[str, Any] = {}

    for span in log.spans:
        if span.span_type != SPAN_JUDGE_RULE:
            continue
        payload = span.payload
        claim_id = str(payload.get("claim_id", ""))
        claim = claim_index.get(claim_id, {})
        turn_id = str(claim.get("turn_id", ""))
        retrieval = retrievals.get(claim_id, {})
        emit = emits.get(claim_id, {})

        retriever_config = retrieval.get("retriever_config", retriever_config)
        thresholds = retrieval.get("thresholds", thresholds)

        clip_path: Path | None = None
        if clips_dir is not None:
            candidate = clips_dir / f"{claim_id}.wav"
            if candidate.exists():
                clip_path = candidate

        findings.append(
            Finding(
                claim_id=claim_id,
                turn_id=turn_id,
                verdict=str(payload.get("verdict", "")),
                severity=str(payload.get("severity", "unclassified")),
                section_id=payload.get("section_id"),
                rationale=str(payload.get("rationale", "")),
                claim_text=str(payload.get("claim_in", "")),
                rule_text=payload.get("rule_text_in"),
                transcript=turns.get(turn_id, ""),
                char_start=int(claim.get("char_start", 0)),
                char_end=int(claim.get("char_end", 0)),
                candidates=list(retrieval.get("candidates", []))[:6],
                offered_section_ids=list(payload.get("offered_section_ids", [])),
                selected_score=float(payload.get("judge_selected_score", 0.0)),
                model=str(payload.get("model", "")),
                prompt_hash=str(payload.get("prompt_hash", "")),
                entry_hash=span.entry_hash,
                audio_clip_ref=emit.get("audio_clip_ref"),
                clip_path=clip_path,
            )
        )

    return ReportData(
        run_id=log.run_id,
        chain_head=log.head,
        agent_version=agent_version,
        policy_pack_version=policy_pack_version,
        policy_citation=policy_citation,
        findings=findings,
        turns=turns,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        span_count=len(log.spans),
        retriever_config=retriever_config,
        thresholds=thresholds,
    )


def gate_decision(data: ReportData, criteria: dict[str, Any]) -> tuple[str, str, str]:
    """Block, review or pass, from the client's own gate thresholds."""
    gates = criteria.get("gate_thresholds", {})
    block = gates.get("block_release", {})
    review = gates.get("review_required", {})

    counts: dict[str, int] = {}
    for finding in data.violations:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1

    for severity, limit in block.items():
        if counts.get(severity, 0) >= int(limit):
            return (
                "BLOCK RELEASE",
                "block",
                f"{counts.get(severity, 0)} {severity} finding(s) meets the "
                f"client's block threshold of {limit}.",
            )

    abstain_rate = (
        len(data.abstentions) / len(data.findings) if data.findings else 0.0
    )
    limit = float(review.get("abstain_rate", 1.0))
    if abstain_rate >= limit:
        return (
            "HUMAN REVIEW REQUIRED",
            "review",
            f"Abstention rate {abstain_rate:.0%} is at or above the client's "
            f"review threshold of {limit:.0%}.",
        )
    for severity, threshold in review.items():
        if severity == "abstain_rate":
            continue
        if counts.get(severity, 0) >= int(threshold):
            return (
                "HUMAN REVIEW REQUIRED",
                "review",
                f"{counts.get(severity, 0)} {severity} finding(s) meets the "
                f"review threshold of {threshold}.",
            )

    return ("NO BLOCKING FINDINGS", "pass", "No finding met a blocking threshold.")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _highlight(finding: Finding) -> str:
    """The claim highlighted inside its transcript, using the stored offsets.

    Sliced by offset rather than by searching for the claim text, because the
    offsets are the claim. Searching would reintroduce exactly the fuzzy
    matching the extractor was designed to avoid.
    """
    transcript = finding.transcript
    if not transcript:
        return f"<mark>{_esc(finding.claim_text)}</mark>"
    start = max(0, min(finding.char_start, len(transcript)))
    end = max(start, min(finding.char_end, len(transcript)))
    return (
        f"{_esc(transcript[:start])}"
        f"<mark>{_esc(transcript[start:end])}</mark>"
        f"{_esc(transcript[end:])}"
    )


def _audio_block(finding: Finding) -> str:
    if finding.clip_path is None or not finding.clip_path.exists():
        return '<p class="muted">No audio captured for this turn.</p>'
    raw = finding.clip_path.read_bytes()
    if len(raw) > MAX_INLINE_CLIP_BYTES:
        return (
            f'<p class="muted">Clip too large to inline '
            f'({len(raw) // 1024} KB). Reference: {_esc(finding.audio_clip_ref)}</p>'
        )
    encoded = base64.b64encode(raw).decode("ascii")
    return (
        f'<audio controls preload="none" src="data:audio/wav;base64,{encoded}"></audio>'
        f'<span class="muted clip-meta">{len(raw) // 1024} KB'
        f'{" &middot; " + _esc(short(finding.audio_clip_ref or "")) if finding.audio_clip_ref else ""}'
        "</span>"
    )


def _candidates_table(finding: Finding) -> str:
    if not finding.candidates:
        return '<p class="muted">No candidates recorded.</p>'
    rows = "".join(
        f"<tr><td><code>{_esc(c.get('section_id'))}</code></td>"
        f"<td class='num'>{float(c.get('score', 0)):.3f}</td>"
        f"<td class='num'>{_esc(c.get('bm25_rank'))}</td>"
        f"<td class='num'>{_esc(c.get('dense_rank'))}</td></tr>"
        for c in finding.candidates
    )
    return (
        "<table class='trace'><thead><tr><th>candidate section</th>"
        "<th>score</th><th>bm25 rank</th><th>dense rank</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _finding_card(finding: Finding, index: int) -> str:
    badge = "abstain" if finding.is_abstention else finding.verdict
    rule_block = (
        f"<blockquote>{_esc(finding.rule_text)}</blockquote>"
        if finding.rule_text
        else '<p class="muted">No rule text was passed to the judge for this claim.</p>'
    )
    return f"""
<article class="card {badge}">
  <header class="card-head">
    <span class="verdict {badge}">{_esc(finding.verdict.replace('_', ' '))}</span>
    <span class="sev sev-{_esc(finding.severity)}">{_esc(finding.severity)}</span>
    <span class="cite">{_esc(finding.section_id or 'no section cited')}</span>
    <span class="muted mono">{_esc(finding.claim_id)}</span>
  </header>

  <h4>What the agent said</h4>
  <p class="transcript">{_highlight(finding)}</p>

  <h4>Audio evidence</h4>
  <div class="audio">{_audio_block(finding)}</div>

  <h4>Governing rule</h4>
  {rule_block}

  <h4>Rationale</h4>
  <p>{_esc(finding.rationale)}</p>

  <details>
    <summary>Trace: how this verdict was reached</summary>
    <div class="trace-body">
      <p><strong>Claim offsets</strong>
         <code>[{finding.char_start}:{finding.char_end}]</code></p>
      <p><strong>Retrieval candidates offered to the judge</strong></p>
      {_candidates_table(finding)}
      <p><strong>Sections offered</strong>
         <code>{_esc(', '.join(finding.offered_section_ids) or 'none')}</code></p>
      <p><strong>Selected section score</strong>
         <code>{finding.selected_score:.3f}</code></p>
      <p><strong>Model</strong> <code>{_esc(finding.model)}</code>
         &middot; <strong>prompt hash</strong>
         <code>{_esc(short(finding.prompt_hash))}</code></p>
      <p><strong>Integrity hash</strong>
         <code>{_esc(short(finding.entry_hash, 24))}</code></p>
    </div>
  </details>
</article>
""".strip()


STYLE = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--muted:#6b6b66;--line:#e2e1dd;--card:#fff;
--crit:#a5252a;--high:#c0631b;--med:#8a7a1e;--low:#5a6a7a;--info:#6b6b66;
--pass:#2f6b40;--warn:#8a5a1e;--block:#a5252a;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:32px 20px 80px}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:19px;margin:36px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h4{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
margin:16px 0 4px}
.muted{color:var(--muted)}
.mono,code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12.5px}
table{border-collapse:collapse;width:100%;margin:8px 0}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);font-size:13.5px}
th{color:var(--muted);font-weight:600;font-size:11.5px;text-transform:uppercase;
letter-spacing:.05em}
td.num{text-align:right;font-family:ui-monospace,Consolas,monospace}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;
margin:16px 0}
.meta div{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px 12px}
.meta dt{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.meta dd{margin:2px 0 0;font-size:14px;word-break:break-all}
.gate{padding:14px 16px;border-radius:6px;border:1px solid var(--line);margin:18px 0;
background:var(--card);border-left-width:5px}
.gate.block{border-left-color:var(--block)}
.gate.review{border-left-color:var(--warn)}
.gate.pass{border-left-color:var(--pass)}
.gate strong{font-size:16px;display:block;margin-bottom:2px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:16px 18px;margin:14px 0;border-left-width:5px}
.card.contradicted{border-left-color:var(--crit)}
.card.supported{border-left-color:var(--pass)}
.card.abstain{border-left-color:var(--muted)}
.card-head{display:flex;flex-wrap:wrap;gap:10px;align-items:center;
padding-bottom:10px;border-bottom:1px solid var(--line)}
.verdict{font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
.verdict.contradicted{color:var(--crit)}.verdict.supported{color:var(--pass)}
.verdict.abstain{color:var(--muted)}
.sev{font-size:11px;text-transform:uppercase;letter-spacing:.05em;padding:2px 7px;
border-radius:10px;border:1px solid var(--line);color:var(--muted)}
.sev-critical{color:var(--crit);border-color:var(--crit)}
.sev-high{color:var(--high);border-color:var(--high)}
.sev-medium{color:var(--med);border-color:var(--med)}
.cite{font-family:ui-monospace,Consolas,monospace;font-size:13px;font-weight:600}
.transcript{background:#f4f4f1;border:1px solid var(--line);border-radius:5px;
padding:10px 12px;line-height:1.7}
mark{background:#ffe9a8;padding:1px 2px;border-radius:2px;font-weight:600}
blockquote{margin:6px 0;padding:10px 14px;border-left:3px solid var(--line);
background:#f7f7f4;font-size:14px}
audio{width:100%;max-width:420px;vertical-align:middle}
.clip-meta{margin-left:10px;font-size:12px}
details{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}
summary{cursor:pointer;font-size:13px;color:var(--muted);font-weight:600}
.trace-body{margin-top:10px;padding-left:2px}
.limitations li{margin-bottom:7px}
.seal{background:var(--card);border:1px solid var(--line);border-radius:6px;
padding:12px 14px;font-size:13px}
footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--line);
color:var(--muted);font-size:12.5px}
@media (prefers-color-scheme:dark){
:root{--bg:#16161a;--fg:#e9e9e4;--muted:#9a9a94;--line:#33333a;--card:#1e1e23}
.transcript{background:#232329}blockquote{background:#232329}
mark{background:#5c4a12;color:#ffe9a8}}
"""


def render_campaign_section(campaign: dict[str, Any] | None) -> str:
    """Per-scenario pass@3 and pass^3 (SPEC section 10).

    Both are shown because the gap between them is the finding. pass@3 says the
    seeded violation was caught at least once in three runs; pass^3 says it was
    caught every time. A tool that catches a violation one run in three is not a
    release gate, and publishing only pass@3 would conceal precisely that.
    """
    if not campaign:
        return ""

    rows = []
    for scenario in campaign.get("scenarios", []):
        flags = "".join("Y" if c else "n" for c in scenario.get("caught", [])) or "-"
        control = " (control)" if scenario.get("is_control") else ""
        if scenario.get("is_control"):
            outcome = (
                f"{scenario.get('false_positive_calls', 0)} false positive call(s)"
            )
        else:
            outcome = (
                f"pass@3 {'yes' if scenario.get('pass_at_3') else 'no'}, "
                f"pass^3 {'yes' if scenario.get('pass_cubed') else 'no'}"
            )
        rows.append(
            f"<tr><td><code>{_esc(scenario.get('scenario_id'))}</code>{control}</td>"
            f"<td><code>{_esc(scenario.get('persona_id'))}</code></td>"
            f"<td><code>{_esc(scenario.get('expected_section_id') or '-')}</code></td>"
            f"<td class='mono'>{_esc(flags)}</td>"
            f"<td>{_esc(outcome)}</td>"
            f"<td class='num'>{scenario.get('drifted', 0)}</td></tr>"
        )

    graded = [s for s in campaign.get("scenarios", []) if not s.get("is_control")]
    at3 = sum(1 for s in graded if s.get("pass_at_3"))
    cubed = sum(1 for s in graded if s.get("pass_cubed"))

    return f"""
<h2>Campaign coverage</h2>
<p>{len(campaign.get('scenarios', []))} scenarios, each run
{campaign.get('runs_per_scenario', 0)} times.
Caught column reads left to right by run: Y caught, n missed.</p>
<table><thead><tr><th>scenario</th><th>persona</th><th>expected section</th>
<th>caught</th><th>outcome</th><th>drifted</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p><strong>pass@3 {at3}/{len(graded)}</strong> &middot;
<strong>pass^3 {cubed}/{len(graded)}</strong> across scenarios carrying a seeded
violation. pass@3 counts a violation caught in at least one run; pass^3 requires
it in every run. The distance between them is run to run instability, and it is
reported rather than averaged away.</p>
<p class="muted">Drifted calls are retained rather than discarded. A persona
that leaves its specification invalidates the scenario under test, but the trace
still carries diagnostic value.</p>
""".strip()


def render_rerun_section(rerun: dict[str, Any] | None) -> str:
    """Fix-and-rerun before and after (SPEC sections 9 and 12).

    Shows the agent's actual turns on both sides, not just the counts. A count
    dropping from one to zero proves nothing on its own; seeing that the agent
    stopped pressing for payment and closed the call is what makes the delta
    mean something to a reviewer.
    """
    if not rerun:
        return ""

    def turns(key: str) -> str:
        return "".join(
            f"<li>{_esc(t)}</li>" for t in rerun.get(key, [])
        ) or "<li class='muted'>no turns recorded</li>"

    def keys(key: str) -> str:
        items = rerun.get(key, [])
        if not items:
            return "<span class='muted'>none</span>"
        return " ".join(
            f"<code>{_esc(k.get('section_id'))}</code>" for k in items
        )

    improved = rerun.get("improved")
    verdict_line = (
        "The fix closed the finding and introduced nothing new."
        if improved
        else "The fix did not close cleanly. See persisted and new below."
    )

    return f"""
<h2>Fix and re-run</h2>
<p>Scenario <code>{_esc(rerun.get('scenario_id'))}</code> re-run with the same
seed after a change to the agent. Only the agent changed: same persona, same
judge, same thresholds, same policy pack.</p>
<div class="gate {'pass' if improved else 'review'}">
  <strong>{'Fix verified' if improved else 'Fix incomplete'}</strong>
  <span class="muted">{_esc(verdict_line)}</span>
</div>
<table><thead><tr><th></th><th>before</th><th>after</th></tr></thead>
<tbody>
<tr><td>findings</td><td class="num">{rerun.get('before_count', 0)}</td>
    <td class="num">{rerun.get('after_count', 0)}</td></tr>
</tbody></table>
<p><strong>Closed</strong> {keys('closed')} &middot;
   <strong>Persisted</strong> {keys('persisted')} &middot;
   <strong>New</strong> {keys('new')}</p>
<h4>Agent turns before the fix</h4>
<ul class="turns">{turns('before_agent_turns')}</ul>
<h4>Agent turns after the fix</h4>
<ul class="turns">{turns('after_agent_turns')}</ul>
<p class="muted">Findings are tracked across runs by the rule they cite, not by
claim identifier. A fix changes what the agent says, so claim identifiers move,
and keying on them would report every issue as closed and new at once.</p>
""".strip()


def render_agreement_section(agreement: dict[str, Any] | None) -> str:
    """Judge-to-human agreement (SPEC section 11).

    When the baseline was not established this says so plainly. Substituting a
    number produced by the system under test would defeat the entire purpose of
    the metric.
    """
    if not agreement:
        return """
<h2>Judge to human agreement</h2>
<p><strong>Not established.</strong> SPEC section 11 requires agreement against
a human labeller on a blind subset, with a floor of 85 percent. No human
labelling has been returned, and a baseline produced by the system under test
cannot validate that system. This metric is absent rather than estimated.</p>
""".strip()

    meets = agreement.get("meets_floor")
    return f"""
<h2>Judge to human agreement</h2>
<div class="gate {'pass' if meets else 'review'}">
  <strong>Raw agreement {float(agreement.get('raw_agreement', 0)):.1%}
  against a {float(agreement.get('floor', 0.85)):.0%} floor</strong>
  <span class="muted">{_esc(agreement.get('positioning', ''))}</span>
</div>
<table><thead><tr><th>measure</th><th>value</th></tr></thead><tbody>
<tr><td>items labelled blind</td><td class="num">{agreement.get('total', 0)}</td></tr>
<tr><td>agreements</td><td class="num">{agreement.get('matched', 0)}</td></tr>
<tr><td>raw agreement</td>
    <td class="num">{float(agreement.get('raw_agreement', 0)):.3f}</td></tr>
<tr><td>Cohen's kappa</td>
    <td class="num">{float(agreement.get('cohens_kappa', 0)):.3f}</td></tr>
</tbody></table>
<p class="muted">Kappa is reported alongside raw agreement because the verdict
distribution is skewed. A labeller answering the same verdict every time would
score high raw agreement while carrying no information, and kappa is what
exposes that.</p>
""".strip()


def render_html(
    data: ReportData,
    criteria: dict[str, Any],
    limitations: list[str],
    campaign: dict[str, Any] | None = None,
    rerun: dict[str, Any] | None = None,
    agreement: dict[str, Any] | None = None,
) -> str:
    """Render the whole report to a single string."""
    label, css_class, reason = gate_decision(data, criteria)

    severity_counts: dict[str, int] = {}
    for finding in data.violations:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
    verdict_counts: dict[str, int] = {}
    for finding in data.findings:
        verdict_counts[finding.verdict] = verdict_counts.get(finding.verdict, 0) + 1

    sev_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td class='num'>{v}</td></tr>"
        for k, v in sorted(severity_counts.items())
    ) or "<tr><td colspan='2' class='muted'>No violations.</td></tr>"

    verdict_rows = "".join(
        f"<tr><td>{_esc(k.replace('_', ' '))}</td><td class='num'>{v}</td>"
        f"<td>{'abstention' if k in ABSTENTIONS else 'decision'}</td></tr>"
        for k, v in sorted(verdict_counts.items())
    )

    violations_html = "".join(
        _finding_card(f, i) for i, f in enumerate(data.violations, start=1)
    ) or '<p class="muted">No violations were emitted in this run.</p>'

    abstentions_html = "".join(
        _finding_card(f, i) for i, f in enumerate(data.abstentions, start=1)
    ) or '<p class="muted">No abstentions.</p>'

    gaps = data.policy_gaps
    if gaps:
        gap_items = "".join(
            f"<li><code>{_esc(f.claim_id)}</code> {_esc(f.claim_text[:150])}</li>"
            for f in gaps
        )
        gaps_html = (
            "<p>Claims where no section in the corpus cleared the retrieval "
            "floor. These are candidates for a rulebook gap, not violations.</p>"
            f"<ul>{gap_items}</ul>"
        )
    else:
        gaps_html = (
            '<p class="muted">No claim reached the policy gap list. Only an '
            "uncleared retrieval floor routes here; a judge rejecting the "
            "sections it was shown is a retrieval failure and goes to human "
            "review instead.</p>"
        )

    limitation_items = "".join(f"<li>{_esc(item)}</li>" for item in limitations)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EchoProof Deployment Readiness Report - {_esc(data.run_id)}</title>
<style>{STYLE}</style></head><body><div class="wrap">

<h1>Deployment Readiness Report</h1>
<p class="muted">EchoProof compliance assurance &middot; run
<code>{_esc(data.run_id)}</code> &middot; generated {_esc(data.generated_at)}</p>

<div class="meta">
  <div><dt>Agent version</dt><dd class="mono">{_esc(data.agent_version)}</dd></div>
  <div><dt>Policy corpus</dt><dd>{_esc(data.policy_citation)}</dd></div>
  <div><dt>Policy pack version</dt>
       <dd class="mono">{_esc(short(data.policy_pack_version, 20))}</dd></div>
  <div><dt>Claims adjudicated</dt><dd>{len(data.findings)}</dd></div>
  <div><dt>Turns covered</dt><dd>{len(data.turns)}</dd></div>
  <div><dt>Evidence spans</dt><dd>{data.span_count}</dd></div>
</div>

<div class="gate {css_class}">
  <strong>Gate decision: {_esc(label)}</strong>
  <span class="muted">{_esc(reason)}</span>
</div>

<h2>Summary</h2>
<p>{len(data.violations)} violation(s) and {len(data.abstentions)} abstention(s)
across {len(data.findings)} adjudicated claims. Abstentions are counted
separately throughout: an abstention is a refusal to decide, and reporting one
as a finding would overstate what was detected.</p>

<table><thead><tr><th>severity</th><th>violations</th></tr></thead>
<tbody>{sev_rows}</tbody></table>

<table><thead><tr><th>verdict</th><th>count</th><th>kind</th></tr></thead>
<tbody>{verdict_rows}</tbody></table>

{render_campaign_section(campaign)}

<h2>Findings</h2>
{violations_html}

<h2>Abstentions</h2>
<p class="muted">Claims the system declined to decide. Each routes to human
review rather than being forced to a verdict.</p>
{abstentions_html}

{render_rerun_section(rerun)}

{render_agreement_section(agreement)}

<h2>Policy gap list</h2>
{gaps_html}

<h2>Known limitations</h2>
<ul class="limitations">{limitation_items}</ul>

<h2>Integrity</h2>
<div class="seal">
<p><strong>Report seal</strong> <code>{_esc(data.seal())}</code></p>
<p><strong>Evidence chain head</strong>
   <code>{_esc(data.chain_head)}</code></p>
<p class="muted">The seal covers the agent version, the policy pack version and
the evidence chain head. Changing any of the three changes the seal. Every
finding above carries the hash of the log entry recording its decision, and the
chain was verified before this report was rendered.</p>
<p class="muted mono">retriever: {_esc(json.dumps(data.retriever_config))}</p>
<p class="muted mono">thresholds: {_esc(json.dumps(data.thresholds))}</p>
</div>

<footer>Generated by EchoProof from evidence log
<code>{_esc(data.run_id)}</code>. Nothing in this report was recomputed at
render time; every value was read from a span written when the decision was
made. This file is self contained and references no external resource.</footer>

</div></body></html>"""
