"""Data contracts shared by every EchoProof module.

These are the only types that cross module boundaries. The engine produces and
consumes these; the packs supply the data that fills them. Nothing here knows
what industry EchoProof is running against, and nothing here may ever learn:
adding a vertical means adding pack files, not editing this module.

Keeping this file dependency-free is deliberate. It is the seam that lets the
retrieval backend, the model backend and the report renderer change
independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    """The five adjudication states. There is no sixth, and no pass/fail.

    Inherits from `str` so it serialises straight to JSON and compares cleanly
    against the exact strings written in CLAUDE.md.

    SUPPORTED                   -- the retrieved rule supports the claim.
    CONTRADICTED                -- the retrieved rule contradicts the claim.
    NO_GOVERNING_RULE           -- retrieval floor uncleared; nothing in the
                                   corpus plausibly governs this claim.
    RETRIEVAL_BELOW_CONFIDENCE  -- above the floor, below the ceiling. Something
                                   probably governs it, but not confidently
                                   enough to adjudicate.
    CONFLICTING_SECTIONS        -- two plausible candidates point different ways.

    The last three are abstentions. They are counted separately from
    supported/contradicted everywhere, because an abstention is a refusal to
    decide and reporting it as a decision would be a lie about coverage.
    """

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    NO_GOVERNING_RULE = "no_governing_rule"
    RETRIEVAL_BELOW_CONFIDENCE = "retrieval_below_confidence"
    CONFLICTING_SECTIONS = "conflicting_sections"

    @property
    def is_abstention(self) -> bool:
        return self in _ABSTENTIONS


_ABSTENTIONS = frozenset(
    {
        Verdict.NO_GOVERNING_RULE,
        Verdict.RETRIEVAL_BELOW_CONFIDENCE,
        Verdict.CONFLICTING_SECTIONS,
    }
)


class ClaimType(str, Enum):
    """The five claim classes the extractor may return.

    NUMERIC and DATE are the deterministic pair: SPEC section 4 requires them to
    be canonicalised and compared in code, never judged by the model.

    IMPLICIT is the weakest and highest-liability class, which is why SPEC
    section 3 requires recall to be measured per type rather than aggregated.
    An aggregate number hides a collapse in implicit recall behind strong
    numeric recall.
    """

    NUMERIC = "numeric"
    DATE = "date"
    COMMITMENT = "commitment"
    POLICY_STATEMENT = "policy_statement"
    IMPLICIT = "implicit"

    @property
    def is_deterministic(self) -> bool:
        """True when SPEC section 4 owns this claim type, not the judge."""
        return self in (ClaimType.NUMERIC, ClaimType.DATE)


class ObligationType(str, Enum):
    """How a policy section binds. Supplied by the pack, never inferred here."""

    REQUIREMENT = "requirement"
    PROHIBITION = "prohibition"
    PERMISSION = "permission"
    DEFINITION = "definition"


@dataclass(frozen=True)
class PolicySection:
    """One addressable unit of a client's policy corpus (SPEC section 1).

    `verbatim_text` is exactly what the source document says. It is never
    paraphrased, summarised or normalised, because it is the text quoted into
    the finding card and the text the judge is allowed to reason from.
    """

    section_id: str
    parent_section: str | None
    verbatim_text: str
    obligation_type: ObligationType
    cross_references: list[str] = field(default_factory=list)
    defined_terms: list[str] = field(default_factory=list)
    heading: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "parent_section": self.parent_section,
            "verbatim_text": self.verbatim_text,
            "obligation_type": self.obligation_type.value,
            "cross_references": list(self.cross_references),
            "defined_terms": list(self.defined_terms),
            "heading": self.heading,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicySection":
        return cls(
            section_id=data["section_id"],
            parent_section=data.get("parent_section"),
            verbatim_text=data["verbatim_text"],
            obligation_type=ObligationType(data["obligation_type"]),
            cross_references=list(data.get("cross_references", [])),
            defined_terms=list(data.get("defined_terms", [])),
            heading=data.get("heading", ""),
        )


@dataclass(frozen=True)
class Chunk:
    """A retrievable unit. Never spans a section boundary (SPEC section 5).

    `parent_heading` is carried into the embedded text on purpose: a paragraph
    reading "(2) Two business days" is meaningless out of context, and without
    its heading the dense half of the retriever has nothing to match against.
    """

    chunk_id: str
    section_id: str
    parent_heading: str
    text: str

    @property
    def embed_text(self) -> str:
        """The string actually indexed. Heading first, then the body."""
        return f"{self.parent_heading}\n{self.text}".strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "section_id": self.section_id,
            "parent_heading": self.parent_heading,
            "text": self.text,
        }


@dataclass(frozen=True)
class Claim:
    """One factual assertion located in a transcript by character offset.

    The extractor returns offsets, never restated text (CLAUDE.md decision 4).
    Two reasons: restated text cannot be verified against the transcript, and
    SPEC section 8's audio citation maps these offsets onto word tokens to slice
    the source audio. A paraphrase breaks both.

    `normalized_value` is populated for NUMERIC and DATE claims only, by
    engine/deterministic.py, and never by the model.
    """

    claim_id: str
    claim_type: ClaimType
    char_start: int
    char_end: int
    normalized_value: str | None = None
    # Question forms of the claim, used ONLY as retrieval queries.
    #
    # These are not the claim and must never be displayed as one, never quoted
    # on a finding card, and never shown to the judge. The claim remains the
    # span at [char_start, char_end).
    #
    # Plural, because one claim can violate several rules under different legal
    # theories and a single question commits to exactly one of them. A promise
    # to delete a credit report entry is both a credit-reporting question and a
    # false-representation question; asking only the first retrieved the
    # furnishing provisions and missed the prohibition on threatening action
    # that cannot be taken, which is the rule the claim actually engages.
    #
    # The cost is that retrieval stops being model-independent. CLAUDE.md
    # decision 2 is still honoured, because the judge sees only retrieved text,
    # but which rules get retrieved is now influenced by the extractor. That
    # belongs in the report's limitations rather than being left implicit.
    retrieval_questions: tuple[str, ...] = ()

    def text(self, transcript: str) -> str:
        """Slice the claim out of the transcript it was extracted from."""
        return transcript[self.char_start : self.char_end]

    def is_valid_span(self, transcript: str) -> bool:
        """True when the offsets actually address a non-empty span.

        Models do return offsets that are reversed, negative, or past the end of
        the string. Those claims are rejected rather than repaired, because a
        repaired offset is a guess about what the model meant.
        """
        return 0 <= self.char_start < self.char_end <= len(transcript)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_type": self.claim_type.value,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "normalized_value": self.normalized_value,
            "retrieval_questions": list(self.retrieval_questions),
        }


@dataclass(frozen=True)
class RetrievalCandidate:
    """One scored candidate section from a retrieval call."""

    section_id: str
    chunk_id: str
    text: str
    score: float
    bm25_rank: int | None = None
    dense_rank: int | None = None
    # The same context the chunk was indexed with. Carried so the reranker and
    # the judge read the provision under the same enclosing clause the embedding
    # model saw, rather than a bare enumerated fragment.
    heading: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "chunk_id": self.chunk_id,
            "score": round(self.score, 6),
            "bm25_rank": self.bm25_rank,
            "dense_rank": self.dense_rank,
        }


@dataclass(frozen=True)
class RetrievalResult:
    """The outcome of one retrieval call, including why it landed where it did.

    `cleared_floor` and `cleared_ceiling` are two independent booleans, not one
    confidence band. SPEC section 5 is explicit that merging them turns a
    retrieval bug into a false "no rule exists" claim, which is the most
    dangerous single output this system can produce: it tells a client they are
    unregulated in an area where they are not.
    """

    query: str
    candidates: list[RetrievalCandidate]
    selected_section_id: str | None
    cleared_floor: bool
    cleared_ceiling: bool
    is_conflicting: bool = False

    @property
    def top_score(self) -> float:
        return self.candidates[0].score if self.candidates else 0.0

    def shortlist(self, limit: int) -> list["RetrievalCandidate"]:
        """The best candidate per section, best first, capped at `limit`.

        Deduplicated by section because a long provision splits into several
        chunks, and offering the judge the same section three times would waste
        the shortlist on one candidate and crowd out genuine alternatives.

        This exists because rank 1 is unreliable while rank 25 is not: on the
        claim pairs, precision@1 is 0.429 while recall@25 is 0.911. The
        governing section is nearly always retrieved and rarely ranked first, so
        selection is a better-posed problem than ranking.
        """
        seen: set[str] = set()
        out: list[RetrievalCandidate] = []
        for candidate in self.candidates:
            if candidate.section_id in seen:
                continue
            seen.add(candidate.section_id)
            out.append(candidate)
            if len(out) >= limit:
                break
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "candidates": [c.to_dict() for c in self.candidates],
            "section_selected": self.selected_section_id,
            "cleared_floor": self.cleared_floor,
            "cleared_ceiling": self.cleared_ceiling,
            "is_conflicting": self.is_conflicting,
        }


@dataclass(frozen=True)
class Adjudication:
    """A verdict on one claim, with the provenance needed to reproduce it."""

    claim_id: str
    verdict: Verdict
    section_id: str | None
    rationale: str
    decided_by: str  # "deterministic" | "retrieval" | "model"

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "verdict": self.verdict.value,
            "section_id": self.section_id,
            "rationale": self.rationale,
            "decided_by": self.decided_by,
        }


@dataclass(frozen=True)
class Span:
    """One entry in the hash-chained evidence log (SPEC section 7).

    `entry_hash` covers `prev_hash`, so editing any earlier entry invalidates
    every hash after it. The chain logic lives in engine/evidence.py; this type
    is just the record shape.
    """

    span_type: str
    span_id: str
    payload: dict[str, Any]
    prev_hash: str
    entry_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_type": self.span_type,
            "span_id": self.span_id,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }
