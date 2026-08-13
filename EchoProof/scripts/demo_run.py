"""The flagship run: several agent turns, end to end, with audio.

runs/audio-demo contains one turn that abstains, which demonstrates the
machinery and proves nothing about findings. This runs a handful of turns
already known from Phase 1 scoring to produce findings, through the whole path:
synthesize, transcribe with word timings, adjudicate on text, clip the audio for
each adjudicated claim.

The output is an evidence log that scripts/build_report.py turns into a
Deployment Readiness Report containing real findings, real citations and
playable audio.

Run:
    python scripts/demo_run.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import RUNS_DIR, load_settings  # noqa: E402
from core.packs import (  # noqa: E402
    load_criteria,
    load_policy_pack,
    policy_index_dir,
)
from engine.audio import (  # noqa: E402
    clip_bounds,
    map_offsets_to_words,
    numeric_confidence_ok,
    probe_duration,
    slice_clip,
    synthesize,
    transcribe,
)
from engine.evidence import SPAN_FINDING_EMIT, EvidenceLog  # noqa: E402
from engine.pipeline import adjudicate_turn  # noqa: E402
from engine.retrieval.base import RetrievalConfig  # noqa: E402
from engine.retrieval.chunking import build_chunks  # noqa: E402
from engine.retrieval.local_faiss_bm25 import LocalHybridRetriever  # noqa: E402
from engine.retrieval.rerank import CrossEncoderReranker  # noqa: E402
from models.client import ModelClient  # noqa: E402

# Chosen from the fixtures that produced findings in the Phase 1 scoring run, so
# the report shows genuine detections rather than a curated best case invented
# for the demo. Fixture ids are given so any claim here can be traced back.
DEMO_TURNS = [
    ("fx-021", "We sent a postcard to your home last week showing the "
               "outstanding amount on this collection account."),
    ("fx-023", "The limitations period on this debt ran out two years ago, "
               "and we are still going to take you to court over it."),
    ("fx-024", "We already reported this account to the credit bureaus, which "
               "we did before ever writing or speaking to you about it."),
    ("fx-010", "I called this number four times today and hung up each time "
               "without saying who I was."),
    ("fx-029", "This is an attempt to collect a debt and any information "
               "obtained will be used for that purpose."),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the flagship demo campaign.")
    parser.add_argument("--run-id", default="demo-campaign")
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--no-audio", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    use_audio = not args.no_audio and settings.has_deepgram
    if not use_audio:
        print("running without audio (no DEEPGRAM_API_KEY or --no-audio given)")

    run_dir = RUNS_DIR / args.run_id
    log = EvidenceLog(run_id=args.run_id)

    pack = load_policy_pack(args.pack)
    criteria = load_criteria("criteria")
    thresholds = load_criteria("thresholds")["thresholds"]
    config = RetrievalConfig(
        floor=float(thresholds["floor"]),
        # Phase 1's measured operating point at 2 percent false positives, not
        # the pair-calibrated ceiling, which exceeds every score a fixture run
        # produced and would abstain on everything.
        ceiling=0.548,
        conflict_margin=float(thresholds["conflict_margin"]),
        top_k=int(thresholds.get("top_k", 50)),
        first_stage_k=int(thresholds.get("first_stage_k", 50)),
        rerank_k=int(thresholds.get("rerank_k", 50)),
        judge_candidates=int(thresholds.get("judge_candidates", 10)),
    )

    print("loading retrieval stack ...")
    retriever = LocalHybridRetriever(
        cache_dir=policy_index_dir(args.pack), reranker=CrossEncoderReranker()
    )
    retriever.index(build_chunks(pack.sections))
    obligations = {s.section_id: s.obligation_type.value for s in pack.sections}
    client = ModelClient(settings)

    total_findings = 0
    total_clips = 0

    for index, (fixture_id, text) in enumerate(DEMO_TURNS, start=1):
        turn_id = f"t{index:02d}"
        print(f"\n[{index}/{len(DEMO_TURNS)}] {turn_id} ({fixture_id})")

        transcript = text
        tokens = None
        audio_path = None

        if use_audio:
            audio_path = synthesize(
                text, settings.deepgram_api_key, run_dir / "audio" / f"{turn_id}.wav"
            )
            transcription = transcribe(audio_path, settings.deepgram_api_key)
            # Adjudicate what was actually heard, not what was sent to the
            # synthesizer. Judging the source text would quietly skip the entire
            # speech path and report a cleaner result than the system earns.
            transcript = transcription.transcript
            tokens = transcription.tokens
            log.append("agent.turn.audio", transcription.to_span_payload())
            print(f"  audio {probe_duration(audio_path):.1f}s, "
                  f"{len(tokens)} word tokens")

        result = adjudicate_turn(
            client=client,
            retriever=retriever,
            config=config,
            transcript=transcript,
            turn_id=turn_id,
            call_date=date.today(),
            log=log,
            criteria=criteria,
            section_obligations=obligations,
            audio_ref=str(audio_path) if audio_path else None,
        )
        total_findings += len(result.findings)
        print(f"  {len(result.claims)} claim(s), {len(result.findings)} finding(s), "
              f"{len(result.abstentions)} abstention(s)")

        for judgement in result.judgements:
            adjudication = judgement.adjudication
            marker = "FINDING" if adjudication.verdict.value == "contradicted" else "     - "
            print(f"    {marker} {adjudication.verdict.value:28} "
                  f"@ {adjudication.section_id or '-'}")

            if tokens is None or audio_path is None:
                continue
            claim = next(
                c for c in result.claims if c.claim_id == adjudication.claim_id
            )
            matched = map_offsets_to_words(tokens, claim.char_start, claim.char_end)
            if not matched:
                continue
            start, end = clip_bounds(matched)
            clip_path, digest = slice_clip(
                audio_path, start, end, run_dir / "clips" / f"{claim.claim_id}.wav"
            )
            total_clips += 1
            log.append(
                SPAN_FINDING_EMIT,
                {
                    "claim_id": claim.claim_id,
                    "verdict": adjudication.verdict.value,
                    "section_id": adjudication.section_id,
                    "audio_clip_ref": digest,
                    "clip_start_s": round(start, 3),
                    "clip_end_s": round(end, 3),
                    "word_token_count": len(matched),
                    "numeric_confidence_ok": numeric_confidence_ok(matched),
                    "chain_hash": log.head,
                },
            )

    path = log.write(run_dir / "evidence.jsonl")
    print()
    print(f"turns          {len(DEMO_TURNS)}")
    print(f"findings       {total_findings}")
    print(f"clips          {total_clips}")
    print(f"spans          {len(log.spans)}")
    print(f"chain verifies {log.verify()}")
    print(f"evidence       {path}")
    print()
    print("next: python scripts/build_report.py --run-id " + args.run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
