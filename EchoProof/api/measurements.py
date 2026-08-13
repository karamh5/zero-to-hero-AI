"""The measurement panel, assembled from artifacts and never hardcoded.

Every figure returned here traces to a file in this repository:

  detection / citation   computed from runs/fixtures-dev-v2 and -v3 scored.json
                         with the same counting rule scripts/score_fixtures.py
                         prints, at the operating ceiling recorded in the
                         campaign run's own retrieve.rule spans
  agreement              labels/agreement.json, written by score_agreement.py
  latency                demo/latency.json, written by measure_latency.py
  campaign               runs/campaign/campaign.json, written by run_campaign.py

Detection is returned as a range across the two scored runs because that is
what the measurement supports. The same 77 item set scored twice gave different
numbers with nothing between the runs to account for it, and collapsing that
into one figure would claim a precision the instrument does not have.

api/tests/test_measurements.py pins this module to the published numbers: if
the counting here ever drifts from what scripts/score_fixtures.py reported,
the test fails rather than the UI silently showing different figures.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT, RUNS_DIR
from core.contracts import Verdict

from api.runsvc import RunService

AGREEMENT_PATH = PROJECT_ROOT / "labels" / "agreement.json"
LATENCY_PATH = PROJECT_ROOT / "demo" / "latency.json"
RUN_SHEET_PATH = PROJECT_ROOT / "demo" / "RUN-SHEET.md"
CAMPAIGN_RUN = "campaign"
FIXTURE_RUNS = ("fixtures-dev-v2", "fixtures-dev-v3")

CONTRADICTED = Verdict.CONTRADICTED.value


def cites_correctly(
    expected: str | None, actual: str | None, separators: tuple[str, ...]
) -> bool:
    """Same rule as scripts/score_fixtures.py, with the boundary characters
    read from the pack manifest rather than assumed to be CFR parentheses."""
    if not expected or not actual:
        return False
    if actual == expected:
        return True
    return actual.startswith(expected) and actual[len(expected)] in "".join(separators)


def fixture_metrics(
    records: list[dict[str, Any]],
    ceiling: float,
    separators: tuple[str, ...],
) -> dict[str, Any]:
    """Detection, false positive rate and citation precision at one ceiling.

    Reapplies the ceiling arithmetically, exactly as score_fixtures.py does: a
    contradicted claim whose selected score falls below the ceiling becomes an
    abstention and is not a finding.
    """

    def is_finding(claim: dict[str, Any]) -> bool:
        return (
            claim["verdict"] == CONTRADICTED
            and float(claim["selected_score"]) >= ceiling
        )

    violations = [r for r in records if r["category"] == "seeded_violation"]
    hard_negatives = [r for r in records if r["category"] == "hard_negative"]

    detected = sum(1 for r in violations if any(is_finding(c) for c in r["claims"]))
    false_positives = sum(
        1 for r in hard_negatives if any(is_finding(c) for c in r["claims"])
    )
    cited = sum(
        1
        for r in violations
        if any(
            is_finding(c)
            and cites_correctly(r["expected_section_id"], c["section_id"], separators)
            for c in r["claims"]
        )
    )

    return {
        "violations": len(violations),
        "hard_negatives": len(hard_negatives),
        "detected": detected,
        "detection": round(detected / len(violations), 3) if violations else None,
        "false_positives": false_positives,
        "false_positive_rate": round(false_positives / len(hard_negatives), 3)
        if hard_negatives
        else None,
        "cited_correctly": cited,
        "citation_precision": round(cited / detected, 3) if detected else None,
    }


def operating_ceiling(service: RunService) -> float | None:
    """The ceiling the scored runs actually operated at.

    Read from the campaign run's recorded thresholds, which is where the 0.548
    operating point lives as data rather than as a number in a document.
    """
    loaded = service.load(CAMPAIGN_RUN)
    if loaded is None or loaded.data is None:
        return None
    ceiling = loaded.data.thresholds.get("ceiling")
    return float(ceiling) if ceiling is not None else None


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def proxy_overhead_documented() -> float | None:
    """The proxy overhead figure recorded in the demo run sheet.

    Parsed from the file rather than written into code, so the UI shows a
    number that traces to the repository or shows nothing. The live /metrics
    endpoint supersedes this whenever the proxy has real samples.
    """
    if not RUN_SHEET_PATH.exists():
        return None
    match = re.search(
        r"\|\s*Proxy overhead\s*\|\s*([0-9.]+)\s*ms",
        RUN_SHEET_PATH.read_text(encoding="utf-8"),
    )
    return float(match.group(1)) if match else None


def assemble(service: RunService) -> dict[str, Any]:
    """Everything the READING screen shows, with per-figure provenance."""
    out: dict[str, Any] = {}

    # Detection and citation as a range over the two scored runs.
    ceiling = operating_ceiling(service)
    runs: list[dict[str, Any]] = []
    if ceiling is not None:
        for run_id in FIXTURE_RUNS:
            records = service.artifact(run_id, "scored")
            if not isinstance(records, list):
                continue
            loaded = service.load(run_id)
            pack = service.pack(loaded.pack_id) if loaded and loaded.pack_id else None
            separators = pack.hierarchy_separators if pack else ("(", "#")
            metrics = fixture_metrics(records, ceiling, separators)
            metrics["run_id"] = run_id
            metrics["source"] = f"runs/{run_id}/scored.json"
            runs.append(metrics)

    detections = [r["detection"] for r in runs if r["detection"] is not None]
    citations = [
        r["citation_precision"] for r in runs if r["citation_precision"] is not None
    ]
    out["detection"] = {
        "runs": runs,
        "ceiling": ceiling,
        "ceiling_source": f"runs/{CAMPAIGN_RUN}/evidence.jsonl retrieve.rule thresholds",
        "low": min(detections) if detections else None,
        "high": max(detections) if detections else None,
        "citation_low": min(citations) if citations else None,
        "citation_high": max(citations) if citations else None,
        "note": (
            "Two runs of the same 77 item development split. Nothing changed "
            "between them that accounts for the difference; a single figure "
            "would overstate the precision of the measurement."
            if len(runs) == 2
            else "Range unavailable: fewer than two scored runs on disk."
        ),
    }

    agreement = _read_json(AGREEMENT_PATH)
    out["agreement"] = {
        "data": agreement,
        "source": "labels/agreement.json",
        "self_graded": True,
        "self_graded_note": (
            "The human baseline was labelled by the same system that built the "
            "judge, at the project owner's direction. Blind to verdicts, but "
            "not an independent human."
        ),
    }

    out["latency"] = {"data": _read_json(LATENCY_PATH), "source": "demo/latency.json"}

    out["proxy_overhead"] = {
        "documented_median_ms": proxy_overhead_documented(),
        "source": "demo/RUN-SHEET.md",
        "note": "Measured in Phase 2 by driving the proxy as a client would. "
        "The live /metrics endpoint reports current samples when the proxy "
        "has carried traffic in this session.",
    }

    campaign = service.artifact(CAMPAIGN_RUN, "campaign")
    campaign_summary: dict[str, Any] | None = None
    if isinstance(campaign, dict):
        graded = [s for s in campaign.get("scenarios", []) if not s.get("is_control")]
        controls = [s for s in campaign.get("scenarios", []) if s.get("is_control")]
        calls = campaign.get("runs_per_scenario", 0) * len(campaign.get("scenarios", []))
        campaign_summary = {
            "graded_scenarios": len(graded),
            "pass_at_3": sum(1 for s in graded if s.get("pass_at_3")),
            "pass_cubed": sum(1 for s in graded if s.get("pass_cubed")),
            "control_false_positive_calls": sum(
                int(s.get("false_positive_calls", 0)) for s in controls
            ),
            "control_calls": campaign.get("runs_per_scenario", 0) * len(controls),
            "calls": calls,
            "turns_per_call": campaign.get("turns_per_call"),
            "cost_usd": campaign.get("cost_usd"),
            "wall_clock_min": campaign.get("wall_clock_min"),
            "cache": campaign.get("cache"),
        }
    out["campaign"] = {"summary": campaign_summary, "source": f"runs/{CAMPAIGN_RUN}/campaign.json"}

    # Chain verification across every run on disk. Computed live, because the
    # claim is about the artifacts as they exist right now.
    chain: dict[str, bool] = {}
    for run_id in service.run_ids():
        loaded = service.load(run_id)
        if loaded is not None:
            chain[run_id] = loaded.chain_ok
    out["chain_verification"] = {
        "runs": chain,
        "all_verified": all(chain.values()) if chain else False,
    }

    return out
