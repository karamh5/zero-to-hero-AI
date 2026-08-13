"""One agent turn, end to end (SPEC section 2).

adapter -> claim extraction -> deterministic checks -> retrieval -> judge ->
evidence log. Every stage writes its span before the next stage runs, so a run
that crashes halfway still leaves an auditable partial trace rather than
nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any

from core.contracts import Claim, ClaimType, Verdict
from engine.deterministic import (
    CheckResult,
    DateParseError,
    NumberParseError,
    normalize_date,
    normalize_number,
)
from core.hashing import hash_text
from engine.evidence import (
    SPAN_AGENT_TURN,
    SPAN_CHECK_DETERMINISTIC,
    SPAN_EXTRACT_CLAIMS,
    SPAN_JUDGE_RULE,
    SPAN_RETRIEVE_RULE,
    EvidenceLog,
)
from engine.extract import extract_claims
from engine.judge import Judgement, judge_claim, severity_for
from engine.retrieval.base import RetrievalConfig, Retriever, merge
from models.client import ModelClient


DEFAULT_QUERY_TEMPLATE = "{claim}"


def _normalise(
    claims: list[Claim],
    transcript: str,
    call_date: date | None,
    log: EvidenceLog | None,
    turn_id: str,
) -> list[Claim]:
    """Canonicalise every numeric and date claim in code, and record the result.

    This populates `normalized_value`, which SPEC section 3 defines for exactly
    these two claim types, and emits a check.deterministic span per SPEC section
    7. The model is never asked what a number or a date means.

    A value that will not parse is recorded as unparseable and left for the
    judge. It is not an error and it is certainly not a mismatch: an amount that
    could not be read is not an amount that was wrong, and reporting it as wrong
    would fabricate a finding.
    """
    out: list[Claim] = []
    for claim in claims:
        if not claim.claim_type.is_deterministic:
            out.append(claim)
            continue

        text = claim.text(transcript)
        parsed: str | None = None
        detail = ""
        try:
            if claim.claim_type is ClaimType.NUMERIC:
                parsed = str(normalize_number(text))
            elif call_date is not None:
                parsed = normalize_date(text, call_date).isoformat()
            else:
                detail = "no call_date anchor supplied, relative dates unresolvable"
        except (NumberParseError, DateParseError) as exc:
            detail = str(exc)

        if log is not None:
            log.append(
                SPAN_CHECK_DETERMINISTIC,
                {
                    "turn_id": turn_id,
                    "claim_id": claim.claim_id,
                    "claim_type": claim.claim_type.value,
                    "value_parsed": parsed,
                    "expected_value": None,
                    "result": CheckResult.MATCH.value
                    if parsed is not None
                    else CheckResult.UNPARSEABLE.value,
                    "detail": detail,
                },
            )
        out.append(replace(claim, normalized_value=parsed))
    return out


def build_retrieval_query(claim_text: str, criteria: dict[str, Any] | None) -> str:
    """Frame a claim as a retrieval query using the pack's template.

    The template is pack data rather than engine logic. Which register retrieves
    best against a corpus is a property of that corpus, and hardcoding a phrasing
    here would put a client-specific assumption inside the engine.

    Falls back to the raw claim when no template is supplied, so the engine still
    runs against a pack that does not define one.
    """
    template = DEFAULT_QUERY_TEMPLATE
    if criteria:
        template = str(
            criteria.get("retrieval", {}).get("query_template", DEFAULT_QUERY_TEMPLATE)
        )
    if "{claim}" not in template:
        return claim_text
    return template.format(claim=claim_text)


@dataclass(frozen=True)
class TurnResult:
    """Everything one turn produced."""

    turn_id: str
    transcript: str
    claims: list[Claim]
    judgements: list[Judgement]
    rejected_claims: list[dict[str, Any]]
    cost_usd: float
    total_tokens: int

    @property
    def findings(self) -> list[Judgement]:
        """Judgements that assert something went wrong.

        Abstentions are excluded. They are reported separately everywhere,
        because counting an abstention as a finding overstates what the system
        actually detected.
        """
        return [
            j for j in self.judgements
            if j.adjudication.verdict is Verdict.CONTRADICTED
        ]

    @property
    def abstentions(self) -> list[Judgement]:
        return [j for j in self.judgements if j.adjudication.verdict.is_abstention]


def adjudicate_turn(
    client: ModelClient,
    retriever: Retriever,
    config: RetrievalConfig,
    transcript: str,
    turn_id: str = "turn",
    call_date: date | None = None,
    expected_values: dict[str, Decimal | date | str] | None = None,
    log: EvidenceLog | None = None,
    criteria: dict[str, Any] | None = None,
    section_obligations: dict[str, str] | None = None,
    audio_ref: str | None = None,
) -> TurnResult:
    """Run one agent turn through the full pipeline."""
    expected_values = expected_values or {}
    cost = 0.0
    tokens = 0

    # The turn itself, recorded before anything is derived from it. Previously
    # only the proxy and audio paths emitted this, so a fixture run stored claim
    # offsets with no transcript for them to index into, and the report could
    # not show a claim highlighted in context. Emitting it here means every
    # entry point produces a complete log.
    if log is not None:
        log.append(
            SPAN_AGENT_TURN,
            {
                "turn_id": turn_id,
                "transcript": transcript,
                "transcript_hash": hash_text(transcript),
                "audio_ref": audio_ref,
                "call_date": call_date.isoformat() if call_date else None,
                "word_timings": None,
                "stt_confidence": None,
            },
        )

    extraction = extract_claims(client, transcript, turn_id=turn_id)
    cost += extraction.call.estimated_cost_usd
    tokens += extraction.call.total_tokens

    if log is not None:
        log.append(SPAN_EXTRACT_CLAIMS, {"turn_id": turn_id, **extraction.to_dict()})

    # Deterministic normalisation, before any judging. CLAUDE.md decision 3
    # requires money and dates to be canonicalised and compared in code, and the
    # first scored run showed this path never executing: every numeric and date
    # claim reached the model with normalized_value still unset. The module was
    # unit tested and dead in the live pipeline at the same time, which is the
    # most misleading state a safety-critical component can be in.
    claims = _normalise(extraction.claims, transcript, call_date, log, turn_id)

    judgements: list[Judgement] = []
    for claim in claims:
        claim_text = claim.text(transcript)

        # The extractor's question forms are the retrieval queries when present.
        # The claim itself stays the offset span and is what the judge is shown.
        questions = list(claim.retrieval_questions) or [claim_text]
        retrieval = merge(
            [
                retriever.retrieve(build_retrieval_query(q, criteria), config)
                for q in questions
            ],
            config,
        )
        if log is not None:
            log.append(
                SPAN_RETRIEVE_RULE,
                {
                    "claim_id": claim.claim_id,
                    # Only the top candidates are stored. The full 50 would
                    # dominate the log without changing what can be audited.
                    **{
                        **retrieval.to_dict(),
                        "candidates": [c.to_dict() for c in retrieval.candidates[:10]],
                    },
                    "retriever_config": retriever.config_fingerprint(),
                    "thresholds": config.to_dict(),
                },
            )

        judgement = judge_claim(
            client=client,
            claim=claim,
            transcript=transcript,
            retrieval=retrieval,
            expected_value=expected_values.get(claim.claim_id),
            call_date=call_date,
            shortlist_size=config.judge_candidates,
            ceiling=config.ceiling,
        )
        if judgement.call is not None:
            cost += judgement.call.estimated_cost_usd
            tokens += judgement.call.total_tokens

        if log is not None:
            obligation = (section_obligations or {}).get(
                judgement.adjudication.section_id or ""
            )
            payload = {"claim_id": claim.claim_id, **judgement.to_dict()}
            if criteria is not None:
                payload["severity"] = severity_for(
                    judgement.adjudication.verdict, obligation, criteria
                )
            log.append(SPAN_JUDGE_RULE, payload)

        judgements.append(judgement)

    return TurnResult(
        turn_id=turn_id,
        transcript=transcript,
        claims=claims,
        judgements=judgements,
        rejected_claims=extraction.rejected,
        cost_usd=round(cost, 6),
        total_tokens=tokens,
    )
