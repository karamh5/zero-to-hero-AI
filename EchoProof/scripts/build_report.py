"""Render a run's evidence log into a Deployment Readiness Report.

Run:
    python scripts/build_report.py --run-id demo-campaign
    python scripts/build_report.py --run-id demo-campaign --verify
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import PROJECT_ROOT, RUNS_DIR  # noqa: E402
from core.packs import load_criteria, load_policy_pack  # noqa: E402
from engine.evidence import EvidenceLog  # noqa: E402
from engine.report import extract_report_data, gate_decision, render_html  # noqa: E402

AGENT_VERSION = "harbor-recovery-agent@0.1.0"

# Read from the phase summaries rather than written fresh, so the report cannot
# claim a cleaner picture than the measurements support.
LIMITATIONS = [
    "Detection rate is 34.8 percent at a 2 percent false positive rate on hard "
    "negatives, measured on the development split. Under SPEC section 11 that "
    "is the below-70-percent band. EchoProof is a triage layer that routes to "
    "human review, not a release gate.",
    "Citation precision at that operating point is 75 percent: three findings "
    "in four cite the correct governing paragraph.",
    "Ground truth for the fixture set was authored by the same system that "
    "built the judge. Measured on retrieval pairs, that authorship advantage "
    "was worth roughly 0.31 precision at rank 1. The held-out split is the only "
    "control and it remains sealed.",
    "Retrieval is not model independent. The extractor generates the retrieval "
    "questions, and 41 percent of them introduced rule vocabulary absent from "
    "the claim. Part of retrieval performance is the model recognising "
    "Regulation F and will not transfer to a private corpus.",
    "Required utterance detection is presence only. Semantic equivalence, "
    "placement, completeness and intelligibility are designed and deferred.",
    "Deterministic verification normalises money and dates in code but does not "
    "yet compare them against expected values, so the comparison half of that "
    "guarantee is not exercised.",
    "The numeric confidence rule fires only when speech-to-text renders numbers "
    "as digits. Verbatim transcription is deliberately preferred, and it "
    "renders spoken amounts as words, so the rule has narrower coverage than "
    "the specification implies.",
    "Audio was synthesized rather than captured from live calls, so disfluency, "
    "interruption and overlap are unexercised. The speech-to-text degradation "
    "delta is designed and deferred.",
    "Audio clips are embedded in this file as base64. That is acceptable at PoC "
    "scale and will not scale to a 100 call campaign, where clips belong in "
    "object storage and are referenced by digest.",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Deployment Readiness Report.")
    parser.add_argument("--run-id", default="demo-campaign")
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--agent-version", default=AGENT_VERSION)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="recompute the seal and report whether it still matches",
    )
    parser.add_argument(
        "--policy-version-override",
        default=None,
        help="pretend the policy pack changed, to show the seal breaking",
    )
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    log_path = run_dir / "evidence.jsonl"
    if not log_path.exists():
        print(f"no evidence log at {log_path}")
        return 1

    # read() verifies the chain, so a tampered log raises here rather than
    # rendering into a report that looks authoritative.
    log = EvidenceLog.read(log_path)
    pack = load_policy_pack(args.pack)
    criteria = load_criteria("criteria")

    policy_version = args.policy_version_override or pack.version
    data = extract_report_data(
        log=log,
        agent_version=args.agent_version,
        policy_pack_version=policy_version,
        policy_citation=pack.citation,
        clips_dir=run_dir / "clips",
    )

    if args.verify:
        stored_path = run_dir / "report.seal"
        seal = data.seal()
        print(f"run                  {args.run_id}")
        print(f"chain verifies       {log.verify()}")
        print(f"agent_version        {data.agent_version}")
        print(f"policy_pack_version  {policy_version[:24]}")
        print(f"computed seal        {seal}")
        if stored_path.exists():
            stored = stored_path.read_text(encoding="utf-8").strip()
            print(f"stored seal          {stored}")
            print(f"SEAL {'INTACT' if stored == seal else 'BROKEN'}")
            return 0 if stored == seal else 2
        print("no stored seal to compare against")
        return 0

    # A campaign summary is included when the run produced one. Absent for
    # single-turn runs, and no placeholder is rendered: an empty section implying
    # a missing feature reads worse than its absence.
    campaign_path = run_dir / "campaign.json"
    campaign = (
        json.loads(campaign_path.read_text(encoding="utf-8"))
        if campaign_path.exists()
        else None
    )

    def load_optional(path: Path) -> dict | None:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    rerun = load_optional(RUNS_DIR / "fix-and-rerun" / "rerun.json")
    agreement = load_optional(PROJECT_ROOT / "labels" / "agreement.json")

    html = render_html(
        data,
        criteria,
        LIMITATIONS,
        campaign=campaign,
        rerun=rerun,
        agreement=agreement,
    )
    out_path = run_dir / "deployment-readiness-report.html"
    out_path.write_text(html, encoding="utf-8")
    (run_dir / "report.seal").write_text(data.seal(), encoding="utf-8")

    label, _css, reason = gate_decision(data, criteria)
    size_kb = out_path.stat().st_size / 1024
    clips = sum(1 for f in data.findings if f.clip_path is not None)

    print(f"run                  {args.run_id}")
    print(f"turns                {len(data.turns)}")
    print(f"claims adjudicated   {len(data.findings)}")
    print(f"violations           {len(data.violations)}")
    print(f"abstentions          {len(data.abstentions)}")
    print(f"policy gap entries   {len(data.policy_gaps)}")
    print(f"clips embedded       {clips}")
    print(f"gate decision        {label} ({reason})")
    print(f"chain verifies       {log.verify()}")
    print(f"seal                 {data.seal()}")
    print(f"file                 {out_path}")
    print(f"size                 {size_kb:.1f} KB")
    print(f"external references  {html.count('http://') + html.count('https://')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
