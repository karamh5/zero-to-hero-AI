"""Judge-to-human agreement (SPEC section 11).

Raw agreement and Cohen's kappa, reported together.

Kappa is not decoration here. The verdict distribution is severely skewed: the
campaign produced 140 abstentions against 8 violations, so a labeller who wrote
`retrieval_below_confidence` on every line would score high raw agreement while
carrying no information at all. Kappa corrects for agreement expected by chance
and is the number that says whether the two labellers are actually tracking the
same thing.

Both are reported because raw agreement is what SPEC section 11's 85 percent
floor is stated against, and substituting kappa for it silently would be
changing the acceptance criterion after the fact.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgreementResult:
    """Agreement between the judge and a human labeller."""

    total: int
    matched: int
    kappa: float
    floor: float
    by_verdict: dict[str, dict[str, int]] = field(default_factory=dict)
    disagreements: list[dict[str, str]] = field(default_factory=list)

    @property
    def raw_agreement(self) -> float:
        return self.matched / self.total if self.total else 0.0

    @property
    def meets_floor(self) -> bool:
        return self.raw_agreement >= self.floor

    @property
    def positioning(self) -> str:
        """What the report is required to say, given the number."""
        if self.meets_floor:
            return (
                "Judge-human agreement meets the stated floor. The detection "
                "numbers remain the constraint on how EchoProof is positioned."
            )
        return (
            "Judge-human agreement is below the stated floor. EchoProof is a "
            "triage layer routing to human review, not a release gate."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "matched": self.matched,
            "raw_agreement": round(self.raw_agreement, 4),
            "cohens_kappa": round(self.kappa, 4),
            "floor": self.floor,
            "meets_floor": self.meets_floor,
            "positioning": self.positioning,
            "by_verdict": self.by_verdict,
            "disagreements": self.disagreements,
        }


def cohens_kappa(pairs: list[tuple[str, str]]) -> float:
    """Cohen's kappa over (judge, human) label pairs.

    Returns 1.0 when both labellers agree on everything AND only one label was
    ever used. That case is degenerate rather than perfect, and it is called out
    in the report rather than presented as a strong result.
    """
    if not pairs:
        return 0.0

    n = len(pairs)
    observed = sum(1 for a, b in pairs if a == b) / n

    judge_counts = Counter(a for a, _ in pairs)
    human_counts = Counter(b for _, b in pairs)
    labels = set(judge_counts) | set(human_counts)
    expected = sum(
        (judge_counts[label] / n) * (human_counts[label] / n) for label in labels
    )

    if expected >= 1.0:
        # Both labellers used exactly one identical label. Chance agreement is
        # total, so kappa is undefined; reporting 1.0 would overstate it.
        return 0.0
    return (observed - expected) / (1.0 - expected)


def score_agreement(
    judge_labels: dict[str, str],
    human_labels: dict[str, str],
    floor: float = 0.85,
) -> AgreementResult:
    """Compare the judge's verdicts against a human's, on shared items only."""
    shared = sorted(set(judge_labels) & set(human_labels))
    pairs = [(judge_labels[k], human_labels[k]) for k in shared]

    by_verdict: dict[str, dict[str, int]] = {}
    disagreements: list[dict[str, str]] = []

    for claim_id in shared:
        judged = judge_labels[claim_id]
        human = human_labels[claim_id]
        bucket = by_verdict.setdefault(judged, {"agreed": 0, "disagreed": 0})
        if judged == human:
            bucket["agreed"] += 1
        else:
            bucket["disagreed"] += 1
            disagreements.append(
                {"claim_id": claim_id, "judge": judged, "human": human}
            )

    return AgreementResult(
        total=len(pairs),
        matched=sum(1 for a, b in pairs if a == b),
        kappa=cohens_kappa(pairs),
        floor=floor,
        by_verdict=by_verdict,
        disagreements=disagreements,
    )
