"""End to end audio path: speech in, cited clip out (SPEC sections 2 and 8).

Synthesize an agent turn, transcribe it with word timings, adjudicate the text,
then cut the audio for the flagged sentence. Adjudication runs on text only and
the audio step happens after the verdict exists, which is the ordering SPEC
section 8 requires.

Run:
    python scripts/audio_demo.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapter.capture import CapturedTurn, record_turn  # noqa: E402
from core.config import RUNS_DIR, STT_MODEL, TTS_MODEL, load_settings  # noqa: E402
from core.packs import (  # noqa: E402
    load_criteria,
    load_policy_pack,
    policy_index_dir,
)
from engine.audio import (  # noqa: E402
    build_transcript,
    clip_bounds,
    lowest_numeric_confidence,
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

# A turn with a real Regulation F issue in it, so the audio path has a finding
# to cite. Two sentences, so the clip is demonstrably a sentence and not the
# whole recording.
DEFAULT_TURN = (
    "Good afternoon, this is Jordan from Harbor Recovery Group calling about "
    "your account. Pay the full balance of four thousand five hundred dollars "
    "today and I can have this removed from your credit report entirely."
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audio path end to end.")
    parser.add_argument("--text", default=DEFAULT_TURN)
    parser.add_argument("--pack", default="reg_f")
    parser.add_argument("--run-id", default="audio-demo")
    args = parser.parse_args()

    settings = load_settings()
    if not settings.has_deepgram:
        print("DEEPGRAM_API_KEY is not set in .env")
        return 1

    run_dir = RUNS_DIR / args.run_id
    log = EvidenceLog(run_id=args.run_id)

    print("=" * 70)
    print("1. synthesize the agent turn")
    print("=" * 70)
    audio_path = synthesize(
        args.text, settings.deepgram_api_key, run_dir / "audio" / "turn.wav"
    )
    duration = probe_duration(audio_path)
    print(f"  tts model     {TTS_MODEL}")
    print(f"  wav           {audio_path.name}  {audio_path.stat().st_size} bytes")
    print(f"  duration      {duration:.2f} s")

    print()
    print("=" * 70)
    print("2. transcribe with word level timings")
    print("=" * 70)
    transcription = transcribe(audio_path, settings.deepgram_api_key)
    print(f"  stt model     {STT_MODEL}")
    print(f"  words         {len(transcription.tokens)}")
    print(f"  transcript    {transcription.transcript}")
    lowest = lowest_numeric_confidence(transcription.tokens)
    print(f"  min numeric confidence  {lowest if lowest is not None else 'n/a'}")

    turn = CapturedTurn(
        turn_id="a01",
        transcript=transcription.transcript,
        source="audio",
        audio_ref=str(audio_path),
    )
    record_turn(log, turn)
    log.append("agent.turn.audio", transcription.to_span_payload())

    print()
    print("=" * 70)
    print("3. adjudicate, text only, no audio as input")
    print("=" * 70)
    pack = load_policy_pack(args.pack)
    criteria = load_criteria("criteria")
    thresholds = load_criteria("thresholds")["thresholds"]
    config = RetrievalConfig(
        floor=float(thresholds["floor"]),
        # Phase 1's measured operating point, not the pair-calibrated ceiling.
        ceiling=0.548,
        conflict_margin=float(thresholds["conflict_margin"]),
        top_k=int(thresholds.get("top_k", 50)),
        first_stage_k=int(thresholds.get("first_stage_k", 50)),
        rerank_k=int(thresholds.get("rerank_k", 50)),
        judge_candidates=int(thresholds.get("judge_candidates", 10)),
    )
    retriever = LocalHybridRetriever(
        cache_dir=policy_index_dir(args.pack), reranker=CrossEncoderReranker()
    )
    retriever.index(build_chunks(pack.sections))
    obligations = {s.section_id: s.obligation_type.value for s in pack.sections}

    result = adjudicate_turn(
        client=ModelClient(settings),
        retriever=retriever,
        config=config,
        transcript=transcription.transcript,
        turn_id="a01",
        call_date=date.today(),
        log=log,
        criteria=criteria,
        section_obligations=obligations,
    )
    print(f"  claims        {len(result.claims)}")
    print(f"  findings      {len(result.findings)}")
    print(f"  abstentions   {len(result.abstentions)}")

    print()
    print("=" * 70)
    print("4. cite the audio for each adjudicated claim")
    print("=" * 70)

    # Clip every claim that reached a verdict, so the demo shows the mapping
    # working even on a turn where the judge abstains.
    to_clip = result.findings or result.judgements
    clipped = 0
    for judgement in to_clip:
        claim = next(
            c for c in result.claims if c.claim_id == judgement.adjudication.claim_id
        )
        matched = map_offsets_to_words(
            transcription.tokens, claim.char_start, claim.char_end
        )
        if not matched:
            print(f"  {claim.claim_id}: no words mapped, skipping")
            continue

        start, end = clip_bounds(matched)
        allowed = numeric_confidence_ok(matched)
        clip_path, digest = slice_clip(
            audio_path, start, end, run_dir / "clips" / f"{claim.claim_id}.wav"
        )
        clip_duration = probe_duration(clip_path)
        clipped += 1

        print(f"  {claim.claim_id}  {judgement.adjudication.verdict.value}")
        print(f"      text      {claim.text(transcription.transcript)[:78]!r}")
        print(f"      chars     [{claim.char_start}:{claim.char_end}] -> "
              f"{len(matched)} word tokens")
        print(f"      audio     {start:.2f}s to {end:.2f}s "
              f"({clip_duration:.2f}s of {duration:.2f}s full call)")
        print(f"      clip      {clip_path.name}  {clip_path.stat().st_size} bytes")
        print(f"      sha256    {digest[:16]}")
        if not allowed:
            print("      ABSTAIN: a numeric token fell below the confidence floor")

        log.append(
            SPAN_FINDING_EMIT,
            {
                "claim_id": claim.claim_id,
                "verdict": judgement.adjudication.verdict.value,
                "section_id": judgement.adjudication.section_id,
                "audio_clip_ref": digest,
                "clip_start_s": round(start, 3),
                "clip_end_s": round(end, 3),
                "word_token_count": len(matched),
                "numeric_confidence_ok": allowed,
                "chain_hash": log.head,
            },
        )

    path = log.write(run_dir / "evidence.jsonl")
    reloaded = EvidenceLog.read(path)

    print()
    print("=" * 70)
    print("evidence")
    print("=" * 70)
    print(f"  clips written      {clipped}")
    print(f"  spans              {len(log.spans)}")
    print(f"  span types         {sorted({s.span_type for s in log.spans})}")
    print(f"  chain verifies     {log.verify()}")
    print(f"  reload head match  {reloaded.head == log.head}")
    print(f"  evidence log       {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
