"""The retriever interface and the confidence policy that sits above it.

Nothing above this module may import FAISS, BM25, or any other backend. This is
the seam the Production OpenSearch swap lands on: a new backend implements
`Retriever` and the judge does not change.

The threshold policy lives here rather than in a backend because it is a
correctness rule, not an implementation detail. SPEC section 5 requires two
distinct thresholds and warns that merging them turns a retrieval bug into a
false "no rule exists" claim. That is the single most dangerous output this
system can produce: telling a client no regulation governs an area where one
does. The two values are therefore separate fields, validated to be different,
and the code that consumes them cannot collapse them by accident.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.contracts import Chunk, RetrievalCandidate, RetrievalResult


class ThresholdError(ValueError):
    """Raised when the floor and ceiling are not a valid separated pair."""


@dataclass(frozen=True)
class RetrievalConfig:
    """Confidence policy for turning candidates into a retrieval outcome.

    floor    below this, nothing in the corpus plausibly governs the claim, and
             the verdict is no_governing_rule.
    ceiling  above the floor but below this, something probably governs it but
             not confidently enough to adjudicate, and the verdict is
             retrieval_below_confidence.

    conflict_margin  how close the runner-up has to be, in confidence, before
             two candidates from different sections count as genuinely
             competing rather than one clear winner.
    """

    floor: float
    ceiling: float
    conflict_margin: float = 0.02
    top_k: int = 50
    # Depth pulled from EACH first-stage retriever before fusion, and the cap on
    # how many fused candidates the reranker scores.
    #
    # Both are set to 50, matching top_k, because widening them was tried and
    # measured worse. The reasoning for widening was that pulling 50 from BM25
    # and 50 from dense produces a union of up to 100, and cutting it back to 50
    # discards candidates the reranker never sees. That is true, and it still
    # made things worse: at first_stage_k 100 and rerank_k 150, precision@1 fell
    # from 0.464 to 0.429 and recall@50 from 0.893 to 0.804 on the same pairs.
    #
    # The explanation is the finding that matters. Widening only helps when the
    # reranker can discriminate. On claim-shaped queries against this corpus it
    # cannot: cross-encoder scores cluster at 0.50, which is sigmoid(0), meaning
    # no signal. Feeding it more candidates therefore adds noise that displaces
    # true positives out of the top 50. The narrow pool was doing useful
    # filtering work that the reranker could not do for itself.
    #
    # Kept as fields rather than reverted to constants so the pool depth stays
    # measurable when the ranking problem above is addressed.
    first_stage_k: int = 50
    rerank_k: int = 50
    # How many distinct sections the judge is offered to select among.
    #
    # Set from the recall curve rather than by taste: recall@10 is 0.750 and
    # recall@25 is 0.911, so a shortlist of 10 puts the governing section in
    # front of the judge three quarters of the time against a rank-1 hit rate of
    # 0.429. Larger shortlists keep improving recall but cost prompt tokens and
    # give the judge more chances to pick a plausible wrong section.
    judge_candidates: int = 10

    def __post_init__(self) -> None:
        if not 0.0 <= self.floor < self.ceiling <= 1.0:
            raise ThresholdError(
                f"floor ({self.floor}) must be below ceiling ({self.ceiling}) "
                "and both within [0, 1]. They are two separate decisions and "
                "collapsing them would report a retrieval miss as a confident "
                "finding that no rule exists."
            )

    def to_dict(self) -> dict[str, float | int]:
        return {
            "floor": self.floor,
            "ceiling": self.ceiling,
            "conflict_margin": self.conflict_margin,
            "top_k": self.top_k,
            "first_stage_k": self.first_stage_k,
            "rerank_k": self.rerank_k,
            "judge_candidates": self.judge_candidates,
        }


# Separators used when a pack does not declare its own. These are Regulation F's
# conventions and they are the fallback, not the rule.
DEFAULT_HIERARCHY_SEPARATORS = ("(", "#")


def root_section(
    section_id: str, separators: tuple[str, ...] | list[str] | None = None
) -> str:
    """The root provision an identifier belongs to.

    1006.14(b)(1) -> 1006.14 under Regulation F's parenthetical convention.
    CC-3.1 -> CC-3 under a dotted convention.

    The separators are pack data, declared in the policy manifest as
    `section_id_scheme.hierarchy_separators`. Hardcoding them here was a real
    engine/pack boundary defect: a corpus numbered CC-3.4.2 contains neither
    "(" nor "#", so every identifier was its own root and the conflict detection
    that compares roots silently stopped working. SPEC section 1 calls engine
    code changing to accommodate a corpus a bug in the boundary, so the fix is
    to read the convention rather than to add a second hardcoded case.
    """
    separators = separators or DEFAULT_HIERARCHY_SEPARATORS
    root = section_id
    for separator in separators:
        root = root.split(separator)[0]
    # The chunk suffix is engine-generated rather than corpus-specific, so it is
    # always stripped regardless of what the pack declares.
    return root.split("#")[0]


def is_within(
    expected: str, actual: str, separators: tuple[str, ...] | list[str] | None = None
) -> bool:
    """Whether `actual` cites `expected` or something inside it.

    A more specific paragraph inside the expected provision counts as a hit; an
    unrelated identifier that merely starts with the same characters does not.
    That boundary check is what stops 1006.2 matching 1006.22, and it needs the
    pack's separators for the same reason `root_section` does.
    """
    if not expected or not actual:
        return False
    if actual == expected:
        return True
    if not actual.startswith(expected):
        return False
    boundary = actual[len(expected)]
    allowed = tuple(separators or DEFAULT_HIERARCHY_SEPARATORS) + ("#",)
    return boundary in allowed


def adjudicate(
    query: str, candidates: list[RetrievalCandidate], config: RetrievalConfig
) -> RetrievalResult:
    """Apply the confidence policy to a ranked candidate list.

    Backend-agnostic on purpose: every retriever produces the same shaped
    outcome, so the judge's routing in SPEC section 6 works identically against
    a local index and against OpenSearch.
    """
    if not candidates:
        return RetrievalResult(
            query=query,
            candidates=[],
            selected_section_id=None,
            cleared_floor=False,
            cleared_ceiling=False,
        )

    top = candidates[0]
    cleared_floor = top.score >= config.floor
    cleared_ceiling = top.score >= config.ceiling

    # Conflict is only meaningful once the ceiling is cleared. Two equally weak
    # candidates are a retrieval failure, not a genuine conflict of authority,
    # and reporting them as conflicting_sections would dress up a miss as a
    # nuanced legal question.
    is_conflicting = False
    if cleared_ceiling and len(candidates) > 1:
        runner_up = candidates[1]
        different_section = root_section(runner_up.section_id) != root_section(
            top.section_id
        )
        close = (top.score - runner_up.score) <= config.conflict_margin
        is_conflicting = different_section and close

    return RetrievalResult(
        query=query,
        candidates=candidates,
        selected_section_id=top.section_id if cleared_floor else None,
        cleared_floor=cleared_floor,
        cleared_ceiling=cleared_ceiling,
        is_conflicting=is_conflicting,
    )


def merge(
    results: list[RetrievalResult], config: RetrievalConfig
) -> RetrievalResult:
    """Combine several retrievals of the same claim into one candidate pool.

    One claim can be governed by rules under different legal theories, so the
    extractor asks several questions about it and each is retrieved separately.
    Their candidate pools are unioned here and re-adjudicated as one.

    A chunk keeps its BEST score across the questions. That is the right rule
    because each question is a different way of asking about the same claim: a
    chunk scoring 0.72 for one framing and 0.50 for another is a strong match
    found by the framing that fit, not a mediocre match on average. Averaging
    would penalise a rule precisely because the other questions were about
    something else.
    """
    if not results:
        return RetrievalResult(
            query="",
            candidates=[],
            selected_section_id=None,
            cleared_floor=False,
            cleared_ceiling=False,
        )
    if len(results) == 1:
        return results[0]

    best: dict[str, RetrievalCandidate] = {}
    for result in results:
        for candidate in result.candidates:
            existing = best.get(candidate.chunk_id)
            if existing is None or candidate.score > existing.score:
                best[candidate.chunk_id] = candidate

    merged = sorted(best.values(), key=lambda c: (-c.score, c.chunk_id))
    combined_query = " | ".join(r.query for r in results)
    return adjudicate(combined_query, merged, config)


class Retriever(ABC):
    """One retrieval backend.

    Implementations rank chunks. They do not decide verdicts and they do not
    know what a verdict is.
    """

    @abstractmethod
    def index(self, chunks: list[Chunk]) -> None:
        """Build or load the index over these chunks."""

    @abstractmethod
    def search(self, query: str, config: RetrievalConfig) -> list[RetrievalCandidate]:
        """Return candidates ranked best first, with calibrated `score`."""

    @abstractmethod
    def config_fingerprint(self) -> dict[str, object]:
        """Identity of this retriever's configuration.

        Pinned into every retrieve.rule span so a stored run can be reproduced.
        SPEC section 7 requires the retriever config to be part of what a
        finding pins, alongside model and prompt hashes.
        """

    def retrieve(self, query: str, config: RetrievalConfig) -> RetrievalResult:
        """Search, then apply the shared confidence policy."""
        candidates = self.search(query, config)
        return adjudicate(query, candidates, config)
