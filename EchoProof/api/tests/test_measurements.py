"""Pin the measurement computations to the published numbers.

The READING screen quotes detection as 0.26 to 0.35 and citation precision as
0.75 to 0.83, produced by scripts/score_fixtures.py over the two scored
development runs at the operating ceiling of 0.548. If the counting in
api/measurements.py ever drifts from that rule, these tests fail rather than
the UI silently displaying different figures.

Skipped cleanly when the scored runs are not on disk (runs/ is git-ignored),
because on a fresh clone there is nothing to pin against.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.config import RUNS_DIR  # noqa: E402

from api.measurements import cites_correctly, fixture_metrics  # noqa: E402

SEPARATORS = ("(", "#")
OPERATING_CEILING = 0.548

PUBLISHED = {
    # LIMITATIONS.md section 2: 8 detections of 23 (0.348) and 6 (0.261),
    # citation 6/8 (0.750) and 5/6 (0.833).
    "fixtures-dev-v2": {"detection": 0.348, "citation_precision": 0.75},
    "fixtures-dev-v3": {"detection": 0.261, "citation_precision": 0.833},
}


def _scored(run_id: str) -> list[dict]:
    path = RUNS_DIR / run_id / "scored.json"
    if not path.exists():
        pytest.skip(f"{path} not on disk; runs/ is git-ignored")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("run_id", sorted(PUBLISHED))
def test_reproduces_published_numbers(run_id: str) -> None:
    metrics = fixture_metrics(_scored(run_id), OPERATING_CEILING, SEPARATORS)
    assert metrics["detection"] == pytest.approx(
        PUBLISHED[run_id]["detection"], abs=0.001
    )
    assert metrics["citation_precision"] == pytest.approx(
        PUBLISHED[run_id]["citation_precision"], abs=0.001
    )


def test_range_is_a_range() -> None:
    values = [
        fixture_metrics(_scored(run_id), OPERATING_CEILING, SEPARATORS)["detection"]
        for run_id in sorted(PUBLISHED)
    ]
    assert min(values) != max(values), (
        "the two scored runs are supposed to disagree; if they stopped "
        "disagreeing the range presentation needs rethinking, not deleting"
    )


def test_cites_correctly_boundary() -> None:
    # 1006.2 must not prefix-match 1006.22. Same rule as score_fixtures.py.
    assert cites_correctly("1006.2", "1006.2(b)", SEPARATORS)
    assert not cites_correctly("1006.2", "1006.22", SEPARATORS)
    assert cites_correctly("1006.6(d)(1)", "1006.6(d)(1)", SEPARATORS)
    assert not cites_correctly(None, "1006.2", SEPARATORS)
    assert not cites_correctly("1006.2", None, SEPARATORS)


def test_dotted_scheme_supported() -> None:
    # A corpus numbered CC-3.4.2 separates levels with dots; the rule must
    # follow the pack convention rather than assuming parentheses.
    assert cites_correctly("CC-3", "CC-3.1", (".",))
    assert not cites_correctly("CC-3", "CC-31", (".",))
