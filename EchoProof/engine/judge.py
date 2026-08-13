"""The judge (SPEC section 6).

Routing, in order, and the order is the design:

1. A numeric or date claim already settled by engine/deterministic.py is decided
   there. The model is never asked to re-judge it. CLAUDE.md decision 3.
2. Retrieval floor uncleared    -> no_governing_rule
3. Retrieval ceiling uncleared  -> retrieval_below_confidence
4. Two close candidates from different sections -> conflicting_sections
5. Otherwise the model rules, strictly from the retrieved text it is handed.

The model sees the retrieved rule text and nothing else. Not the corpus, not
neighbouring sections, and explicitly not its own knowledge of the FDCPA. That
constraint is what makes a verdict falsifiable: anyone can read the rule text
printed on the finding card and check the reasoning against it. A judge drawing
on training knowledge produces verdicts that sound authoritative and cannot be
audited, which is the thing this product exists to replace.

The model may also decline. Decision 6 forbids forcing a verdict to avoid an
abstention, so "the text I was given does not govern this claim" is a legitimate
answer and routes to no_governing_rule rather than to a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from typing import Any

from core.config import JUDGE_MODEL
from core.contracts import (
    Adjudication,
    Claim,
    RetrievalCandidate,
    RetrievalResult,
    Verdict,
)
from engine.deterministic import Check, CheckResult, check_amount, check_date
from models.client import ModelCall, ModelClient

SYSTEM_PROMPT = """\
You are a compliance adjudicator. You are given one claim made by an automated \
agent on a call, and a numbered list of candidate rules retrieved from a policy \
corpus.

Do two things, in order.

First, select which single candidate governs the claim. Selection is a real \
decision: the list is ordered by a retrieval score that is often wrong, so do \
not assume candidate 1 is correct. If no candidate governs the claim, say so \
rather than choosing the least bad one.

Second, decide whether the rule you selected supports or contradicts the claim.

Before you rule that a claim is contradicted by a prohibition, check the rest \
of the list for a rule that permits the conduct: an exception, an exclusion, a \
safe harbour, or a definition that places the conduct outside the prohibition. \
Rulebooks routinely state a prohibition in one place and carve exceptions out \
of it in another. If a candidate permits what the claim describes, that \
candidate is the governing rule and the verdict is supported, not contradicted. \
Reading the prohibition alone and ignoring the carve-out produces a finding \
against conduct the rulebook expressly allows, which is worse than missing the \
issue entirely.

The candidate texts are the only authority you may use. Do not rely on anything \
you know about this area of law, this regulation, or what rules usually say. \
Judge only from the text in front of you.

Return exactly one verdict:
- supported: the selected rule supports the claim
- contradicted: the selected rule contradicts the claim
- not_governed: no candidate in the list governs this claim

If a second candidate genuinely governs the same claim and points the opposite \
way, name it in conflicting_section_id. Use that only for a real conflict of \
authority, not merely because two candidates look similar.

Give a one or two sentence rationale referring to the text you selected. Only \
ever cite section identifiers that appear in the candidate list.
"""

JUDGE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "record_verdict",
        "description": "Select the governing rule and record the verdict.",
        "parameters": {
            "type": "object",
            "properties": {
                "section_id": {
                    "type": "string",
                    "description": (
                        "The section_id of the candidate that governs this claim, "
                        "copied exactly from the list. Use 'none' if none govern."
                    ),
                },
                "verdict": {
                    "type": "string",
                    "enum": ["supported", "contradicted", "not_governed"],
                },
                "rationale": {"type": "string"},
                "conflicting_section_id": {
                    "type": "string",
                    "description": (
                        "A second candidate that governs the same claim and points "
                        "the opposite way. Omit or use 'none' when there is no conflict."
                    ),
                },
            },
            "required": ["section_id", "verdict", "rationale"],
        },
    },
}


@dataclass(frozen=True)
class JudgementInputs:
    """Everything one adjudication consumed. Written to the judge.rule span."""

    claim_text: str
    rule_text: str | None
    section_id: str | None
    retrieval_top_score: float
    cleared_floor: bool
    cleared_ceiling: bool
    # Which sections the judge was offered, and which it picked. Both are
    # recorded because SPEC section 9's expandable trace has to let a contested
    # finding be root caused, and "the right rule was never offered" and "the
    # right rule was offered and the judge passed it over" are different bugs
    # that look identical in the verdict alone.
    offered_section_ids: list[str] = field(default_factory=list)
    selected_section_id: str | None = None
    # Retrieval score of the section the judge chose, as distinct from the score
    # of whatever ranked first. Recorded because the ceiling is applied to this
    # value, and because it lets a precision-recall curve be swept after the
    # fact: with the score and the model's verdict both stored, the verdict at
    # any other ceiling is recoverable without re-running the model.
    selected_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_in": self.claim_text,
            "rule_text_in": self.rule_text,
            "section_id": self.section_id,
            "retrieval_top_score": round(self.retrieval_top_score, 6),
            "cleared_floor": self.cleared_floor,
            "cleared_ceiling": self.cleared_ceiling,
            "offered_section_ids": list(self.offered_section_ids),
            "judge_selected_section_id": self.selected_section_id,
            "judge_selected_score": round(self.selected_score, 6),
        }


@dataclass(frozen=True)
class Judgement:
    """One adjudication with its inputs and provenance."""

    adjudication: Adjudication
    inputs: JudgementInputs
    deterministic_check: Check | None = None
    call: ModelCall | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            **self.inputs.to_dict(),
            **self.adjudication.to_dict(),
        }
        if self.deterministic_check is not None:
            payload["deterministic_check"] = self.deterministic_check.to_dict()
        if self.call is not None:
            payload["model"] = self.call.model
            payload["prompt_hash"] = self.call.prompt_hash
            payload["raw_response"] = self.call.raw_response
        return payload


def judge_claim(
    client: ModelClient,
    claim: Claim,
    transcript: str,
    retrieval: RetrievalResult,
    expected_value: Decimal | date | str | None = None,
    call_date: date | None = None,
    shortlist_size: int = 10,
    ceiling: float = 0.0,
) -> Judgement:
    """Adjudicate one claim. The only entry point."""
    claim_text = claim.text(transcript)

    inputs = JudgementInputs(
        claim_text=claim_text,
        rule_text=_selected_text(retrieval),
        section_id=retrieval.selected_section_id,
        retrieval_top_score=retrieval.top_score,
        cleared_floor=retrieval.cleared_floor,
        cleared_ceiling=retrieval.cleared_ceiling,
    )

    # 1. Deterministic claims are settled in code, before any model call.
    if claim.claim_type.is_deterministic and expected_value is not None:
        check = _run_check(claim_text, expected_value, call_date)
        if check.result is CheckResult.MATCH:
            return _decided(claim, Verdict.SUPPORTED, retrieval, inputs, check,
                            "Value verified in code against the expected value.")
        if check.result is CheckResult.MISMATCH:
            return _decided(
                claim, Verdict.CONTRADICTED, retrieval, inputs, check,
                f"Value stated was {check.value_parsed}, expected {check.expected_value}. "
                "Compared in code, not by a model.",
            )
        # UNPARSEABLE falls through to the model path. An amount that could not
        # be read is not an amount that was wrong, and reporting it as wrong
        # would be a fabricated finding.

    # 2 and 3. Retrieval confidence, as two separate decisions.
    if not retrieval.cleared_floor:
        return _decided(
            claim, Verdict.NO_GOVERNING_RULE, retrieval, inputs, None,
            "No section in the policy corpus cleared the retrieval floor for this claim.",
            decided_by="retrieval",
        )
    # The ceiling deliberately does NOT gate here. It is applied further down, to
    # the section the judge actually selects.
    #
    # Gating before selection was tried and was self-defeating: the ceiling is a
    # threshold on the rank-1 score, and the entire reason selection exists is
    # that rank-1 is unreliable (precision@1 0.429 against recall@25 0.911).
    # Checking it first meant a claim whose governing section sat at rank 3 was
    # abstained before the judge could ever look at the shortlist. On the smoke
    # turn that discarded 1006.30(a)(1), the credit reporting provision, which
    # was present in the shortlist and is the rule the claim actually engages.
    #
    # Confidence belongs to the section that gets cited, not to whichever chunk
    # happened to rank first.

    # 4. The model selects the governing section from a shortlist, then rules.
    #
    # Conflict detection moved here from retrieval. Retrieval could only compare
    # scores, which says two candidates are similarly worded, not that two rules
    # genuinely point opposite ways. The judge can see both texts, so it is the
    # only place that distinction can actually be made.
    shortlist = retrieval.shortlist(shortlist_size)
    offered = {c.section_id for c in shortlist}

    user = (
        f"Claim made by the agent:\n{claim_text}\n\n"
        f"Candidate rules ({len(shortlist)}):\n\n" + _format_candidates(shortlist)
    )
    call = client.complete(
        model=JUDGE_MODEL,
        system=SYSTEM_PROMPT,
        user=user,
        tools=[JUDGE_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_verdict"}},
        max_tokens=768,
    )

    payload = call.tool_arguments or {}
    raw_verdict = str(payload.get("verdict", "")).strip()
    rationale = str(payload.get("rationale", "")).strip()
    selected = str(payload.get("section_id", "")).strip()
    conflicting = str(payload.get("conflicting_section_id", "") or "").strip()

    chosen = next((c for c in shortlist if c.section_id == selected), None)

    # rule_text is overwritten with the text of the section the judge ACTUALLY
    # selected. It was seeded from the top-ranked candidate before selection ran,
    # which is wrong the moment the judge picks anything other than rank 1, and
    # the judge picks something else routinely because rank 1 is unreliable.
    #
    # Left uncorrected, a finding card cites one section and quotes the text of
    # another. That was observed in the first rendered report: a postcard
    # violation cited 1006.22(f)(1) correctly and displayed the text of the
    # email-address provision beside it. A reviewer checking the citation
    # against the quote would conclude the tool is wrong, and would be right to.
    inputs = replace(
        inputs,
        offered_section_ids=sorted(offered),
        selected_section_id=selected or None,
        selected_score=chosen.score if chosen is not None else 0.0,
        section_id=selected or None,
        rule_text=(
            f"{chosen.heading}\n{chosen.text}".strip()
            if chosen is not None and chosen.heading
            else (chosen.text if chosen is not None else None)
        ),
    )
    selected_score = chosen.score if chosen is not None else 0.0

    # The judge rejecting every candidate routes to RETRIEVAL_BELOW_CONFIDENCE,
    # NOT to NO_GOVERNING_RULE. The distinction is the most important one in
    # this module.
    #
    # NO_GOVERNING_RULE asserts to a client that their rulebook contains no rule
    # covering this conduct. It feeds the policy gap list, which is a document
    # somebody acts on. "None of the ten sections I was shown govern this" is a
    # completely different statement, and with recall@10 measured at 0.750 it is
    # wrong about the corpus roughly a quarter of the time.
    #
    # This was not hypothetical. On the smoke turn, a promise to delete a credit
    # report entry was offered ten candidates, none of which governed it, and
    # the judge correctly rejected all ten. The governing rule, the prohibition
    # on threatening action that cannot legally be taken, was never retrieved.
    # Routing that to NO_GOVERNING_RULE would have told a client that Regulation
    # F is silent on the subject, which is false.
    #
    # Only an uncleared retrieval floor, meaning nothing in the corpus was even
    # plausible, now produces NO_GOVERNING_RULE. That is what SPEC section 5's
    # warning about merging the two thresholds is actually protecting.
    if selected not in offered or raw_verdict == "not_governed":
        reason = (
            "The judge rejected every retrieved candidate. This is a retrieval "
            "failure to route to human review, not evidence that the corpus lacks "
            "a governing rule."
            if raw_verdict == "not_governed" and selected in offered | {"none", ""}
            else f"Model selected {selected!r}, which was not among the candidates offered."
        )
        return _model_decided(
            claim,
            Verdict.RETRIEVAL_BELOW_CONFIDENCE,
            None,
            f"{rationale} {reason}".strip() if rationale else reason,
            inputs,
            call,
        )

    if conflicting and conflicting in offered and conflicting != selected:
        return _model_decided(
            claim,
            Verdict.CONFLICTING_SECTIONS,
            selected,
            rationale
            or f"Sections {selected} and {conflicting} both govern and point opposite ways.",
            inputs,
            call,
        )

    # Ceiling, applied to the section the judge chose rather than to rank 1.
    # A selection resting on weak retrieval evidence is an abstention, not a
    # finding: the judge can only be as reliable as the text it was offered.
    if selected_score < ceiling:
        return _model_decided(
            claim,
            Verdict.RETRIEVAL_BELOW_CONFIDENCE,
            selected,
            f"Section {selected} was selected but its retrieval confidence "
            f"({selected_score:.3f}) is below the ceiling ({ceiling:.3f}), so the "
            "claim was not adjudicated.",
            inputs,
            call,
        )

    if raw_verdict == "supported":
        verdict = Verdict.SUPPORTED
    elif raw_verdict == "contradicted":
        verdict = Verdict.CONTRADICTED
    else:
        # An unparseable verdict routes to abstention rather than defaulting to
        # supported, because a default of supported silently converts model
        # failures into clean bills of health.
        return _model_decided(
            claim,
            Verdict.RETRIEVAL_BELOW_CONFIDENCE,
            None,
            f"Model returned an unrecognised verdict {raw_verdict!r}; routed to "
            "human review. A model failure is not evidence about the corpus.",
            inputs,
            call,
        )

    return _model_decided(claim, verdict, selected, rationale, inputs, call)


def _format_candidates(shortlist: list[RetrievalCandidate]) -> str:
    """Render the shortlist for the prompt.

    Retrieval scores are deliberately omitted. Showing them would anchor the
    model on the ranking that is already known to be unreliable, which is the
    problem the shortlist exists to route around.
    """
    blocks: list[str] = []
    for index, candidate in enumerate(shortlist, start=1):
        heading = candidate.heading or candidate.section_id
        blocks.append(f"[{index}] section_id: {candidate.section_id}\n{heading}\n{candidate.text}")
    return "\n\n".join(blocks)


def _model_decided(
    claim: Claim,
    verdict: Verdict,
    section_id: str | None,
    rationale: str,
    inputs: JudgementInputs,
    call: ModelCall,
) -> Judgement:
    return Judgement(
        adjudication=Adjudication(
            claim_id=claim.claim_id,
            verdict=verdict,
            section_id=section_id,
            rationale=rationale,
            decided_by="model",
        ),
        inputs=inputs,
        call=call,
    )


def _run_check(
    claim_text: str, expected: Decimal | date | str, call_date: date | None
) -> Check:
    if isinstance(expected, date):
        if call_date is None:
            return Check(
                CheckResult.UNPARSEABLE, None, expected.isoformat(),
                "a date claim needs a call_date anchor to resolve relative phrases",
            )
        return check_date(claim_text, expected, call_date)
    return check_amount(claim_text, expected)


def _selected_text(retrieval: RetrievalResult) -> str | None:
    """The verbatim text of the selected section, with its heading."""
    if not retrieval.candidates or retrieval.selected_section_id is None:
        return None
    top = retrieval.candidates[0]
    return f"{top.heading}\n{top.text}".strip() if top.heading else top.text


def _decided(
    claim: Claim,
    verdict: Verdict,
    retrieval: RetrievalResult,
    inputs: JudgementInputs,
    check: Check | None,
    rationale: str,
    decided_by: str = "deterministic",
) -> Judgement:
    return Judgement(
        adjudication=Adjudication(
            claim_id=claim.claim_id,
            verdict=verdict,
            section_id=retrieval.selected_section_id
            if verdict is not Verdict.NO_GOVERNING_RULE
            else None,
            rationale=rationale,
            decided_by=decided_by,
        ),
        inputs=inputs,
        deterministic_check=check,
    )


def severity_for(
    verdict: Verdict, obligation_type: str | None, criteria: dict[str, Any]
) -> str:
    """Map a verdict onto the client's own severity label.

    The mapping is data. The engine holds no severity scale of its own, which is
    what lets a client with five labels and a client with three both be served
    without a code change.
    """
    severity_map = criteria.get("severity_map", {})
    by_verdict = severity_map.get(verdict.value, {})
    if not isinstance(by_verdict, dict):
        return "medium"
    if obligation_type and obligation_type in by_verdict:
        return str(by_verdict[obligation_type])
    return str(by_verdict.get("default", "medium"))
