"""Fix-and-rerun diff (SPEC section 12).

Same scenario, same seed, run before and after a fix. Findings are classified
into closed, persisted and new.

The classification key is deliberately (section_id, verdict) rather than
claim_id. Claim identifiers are positional: they encode which turn and which
claim index a finding came from, and a fix changes what the agent says, so the
same underlying issue lands on a different claim_id in the second run. Keying on
claim_id would report every finding as closed and every finding as new
simultaneously, which is worse than useless because it looks like a perfect fix.

What a client is asking is "is that compliance issue gone", and a compliance
issue is identified by the rule it breaches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FindingKey:
    """The identity of a compliance issue across runs."""

    section_id: str
    verdict: str

    def to_dict(self) -> dict[str, str]:
        return {"section_id": self.section_id, "verdict": self.verdict}


@dataclass
class RerunDelta:
    """What changed between a before run and an after run."""

    scenario_id: str
    seed: int
    before_count: int = 0
    after_count: int = 0
    closed: list[FindingKey] = field(default_factory=list)
    persisted: list[FindingKey] = field(default_factory=list)
    new: list[FindingKey] = field(default_factory=list)

    @property
    def improved(self) -> bool:
        """A fix worked when something closed and nothing new appeared.

        Requiring no new findings matters. A change that closes one issue while
        introducing another has not fixed the agent, and reporting it as an
        improvement because the count fell would hide a regression.
        """
        return bool(self.closed) and not self.new

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "before_count": self.before_count,
            "after_count": self.after_count,
            "closed": [k.to_dict() for k in self.closed],
            "persisted": [k.to_dict() for k in self.persisted],
            "new": [k.to_dict() for k in self.new],
            "improved": self.improved,
        }


def keys_from_findings(findings: list[dict[str, Any]]) -> set[FindingKey]:
    """Reduce a run's findings to the set of compliance issues it raised."""
    keys: set[FindingKey] = set()
    for finding in findings:
        section_id = finding.get("section_id")
        verdict = finding.get("verdict")
        if not section_id or not verdict:
            # A finding with no cited section cannot be tracked across runs.
            # Dropping it is correct: an untraceable finding would otherwise
            # appear as closed on every rerun regardless of what happened.
            continue
        keys.add(FindingKey(section_id=str(section_id), verdict=str(verdict)))
    return keys


def diff_runs(
    scenario_id: str,
    seed: int,
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> RerunDelta:
    """Classify findings into closed, persisted and new."""
    before_keys = keys_from_findings(before)
    after_keys = keys_from_findings(after)

    return RerunDelta(
        scenario_id=scenario_id,
        seed=seed,
        before_count=len(before),
        after_count=len(after),
        closed=sorted(before_keys - after_keys, key=lambda k: k.section_id),
        persisted=sorted(before_keys & after_keys, key=lambda k: k.section_id),
        new=sorted(after_keys - before_keys, key=lambda k: k.section_id),
    )
