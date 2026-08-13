"""Audio evidence and citation (SPEC section 8).

The claim carries character offsets into a transcript. The transcript comes from
Nova-3, which also returns per word start and end times. Mapping one to the
other has to be exact, because the output is a clip presented as evidence that
the agent said a specific sentence.

**The mapping is deterministic by construction, not by matching.** Rather than
taking Deepgram's assembled transcript string and trying to locate words in it
afterwards, this module builds the transcript FROM the word tokens and records
each token's character span as it goes. A claim offset then resolves to a set of
tokens by simple interval overlap. There is no fuzzy matching anywhere, which
matters because fuzzy matching fails hardest on hedged, disfluent speech, and
hedged speech is exactly where the liability sits.

Adjudication never sees audio. SPEC section 8 is explicit that audio is bolted
on after a verdict exists and is never an input to it, so nothing in this module
is called before a verdict.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from core.config import (
    DEEPGRAM_BASE_URL,
    STT_MODEL,
    STT_NUMERIC_CONFIDENCE_FLOOR,
    TTS_MODEL,
)
from core.hashing import hash_text

TIMEOUT = 180
_DIGIT_RE = re.compile(r"\d")


class AudioError(RuntimeError):
    """Raised when speech synthesis, transcription, or slicing fails."""


@dataclass(frozen=True)
class WordToken:
    """One recognised word, with both its time span and its character span."""

    text: str
    start: float
    end: float
    confidence: float
    char_start: int
    char_end: int

    @property
    def is_numeric(self) -> bool:
        """Whether this token carries a digit, and so falls under the floor."""
        return bool(_DIGIT_RE.search(self.text))

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "confidence": round(self.confidence, 4),
            "char_start": self.char_start,
            "char_end": self.char_end,
        }


@dataclass(frozen=True)
class Transcription:
    """A transcript assembled from tokens, so offsets are exact by construction."""

    transcript: str
    tokens: list[WordToken]
    model: str
    audio_path: Path

    def to_span_payload(self) -> dict[str, Any]:
        return {
            "transcript": self.transcript,
            "transcript_hash": hash_text(self.transcript),
            "stt_model": self.model,
            "word_timings": [t.to_dict() for t in self.tokens],
            "stt_confidence": round(
                min((t.confidence for t in self.tokens), default=0.0), 4
            ),
            "audio_ref": str(self.audio_path),
        }


# ---------------------------------------------------------------------------
# Synthesis and transcription
# ---------------------------------------------------------------------------


def synthesize(text: str, api_key: str, out_path: Path, model: str = TTS_MODEL) -> Path:
    """Render text to speech with Aura-2 and write a WAV.

    Used to produce call audio whose exact wording is known, so the offset to
    timestamp mapping can be checked against ground truth instead of eyeballed.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.post(
        f"{DEEPGRAM_BASE_URL}/speak",
        params={"model": model, "encoding": "linear16", "container": "wav",
                "sample_rate": "24000"},
        headers={"Authorization": f"Token {api_key}", "Content-Type": "application/json"},
        json={"text": text},
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        raise AudioError(f"Aura synthesis failed ({response.status_code}): {response.text[:200]}")
    out_path.write_bytes(response.content)
    return out_path


def transcribe(audio_path: Path, api_key: str, model: str = STT_MODEL) -> Transcription:
    """Transcribe with Nova-3, requesting word level timings and confidence."""
    audio = audio_path.read_bytes()
    response = requests.post(
        f"{DEEPGRAM_BASE_URL}/listen",
        params={
            "model": model,
            "punctuate": "true",
            # smart_format rewrites numbers and dates into display forms, which
            # would put text in the transcript that the speaker did not say and
            # break the promise that a claim quotes the call verbatim.
            "smart_format": "false",
            "utterances": "false",
        },
        headers={"Authorization": f"Token {api_key}", "Content-Type": "audio/wav"},
        data=audio,
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        raise AudioError(f"Nova transcription failed ({response.status_code}): {response.text[:200]}")

    payload = response.json()
    try:
        alternative = payload["results"]["channels"][0]["alternatives"][0]
        words = alternative["words"]
    except (KeyError, IndexError) as exc:
        raise AudioError(f"unexpected Deepgram response shape: {exc}") from exc

    transcript, tokens = build_transcript(words)
    return Transcription(
        transcript=transcript, tokens=tokens, model=model, audio_path=audio_path
    )


def build_transcript(words: list[dict[str, Any]]) -> tuple[str, list[WordToken]]:
    """Assemble the transcript from tokens, recording each token's char span.

    This is the step that makes the whole citation chain exact. Deepgram also
    returns a joined transcript string, but locating words inside a string
    somebody else assembled means re-deriving positions that were already known
    and losing them. Building it here means every token's character span is
    recorded at the moment the string is formed.
    """
    parts: list[str] = []
    tokens: list[WordToken] = []
    cursor = 0

    for word in words:
        # punctuated_word carries the casing and punctuation a reader expects;
        # `word` is the bare lowercase form. The transcript shown as evidence
        # should read the way the call sounded.
        text = str(word.get("punctuated_word") or word.get("word") or "")
        if not text:
            continue
        if parts:
            parts.append(" ")
            cursor += 1
        start_offset = cursor
        parts.append(text)
        cursor += len(text)
        tokens.append(
            WordToken(
                text=text,
                start=float(word.get("start", 0.0)),
                end=float(word.get("end", 0.0)),
                confidence=float(word.get("confidence", 0.0)),
                char_start=start_offset,
                char_end=cursor,
            )
        )
    return "".join(parts), tokens


# ---------------------------------------------------------------------------
# Offset to timestamp mapping
# ---------------------------------------------------------------------------


def map_offsets_to_words(
    tokens: list[WordToken], char_start: int, char_end: int
) -> list[WordToken]:
    """Every token whose character span overlaps the claim's span.

    Overlap rather than containment: a claim boundary can fall inside a word,
    and dropping a partially covered word would clip the first or last syllable
    off the audio evidence.
    """
    return [
        token
        for token in tokens
        if token.char_start < char_end and token.char_end > char_start
    ]


def clip_bounds(
    tokens: list[WordToken], pad_seconds: float = 0.15
) -> tuple[float, float]:
    """Start and end times for a clip covering these tokens.

    Padded slightly because cutting exactly on the token boundary clips the
    onset of the first word and the release of the last, which makes a clip
    sound truncated and invites a reviewer to doubt it.
    """
    if not tokens:
        raise AudioError("cannot compute clip bounds for zero tokens")
    start = max(0.0, min(t.start for t in tokens) - pad_seconds)
    end = max(t.end for t in tokens) + pad_seconds
    return start, end


def lowest_numeric_confidence(tokens: list[WordToken]) -> float | None:
    """Lowest confidence among tokens carrying digits, or None if there are none."""
    numeric = [t.confidence for t in tokens if t.is_numeric]
    return min(numeric) if numeric else None


def numeric_confidence_ok(
    tokens: list[WordToken], floor: float = STT_NUMERIC_CONFIDENCE_FLOOR
) -> bool:
    """Whether a finding may be emitted, per SPEC section 8's confidence rule.

    A numeric token recognised below the floor routes to abstention. Reporting
    that an agent stated a wrong amount when the amount may simply have been
    misheard would be a fabricated allegation, and it is the single most
    embarrassing failure this product could put in front of a compliance
    officer.
    """
    lowest = lowest_numeric_confidence(tokens)
    return lowest is None or lowest >= floor


# ---------------------------------------------------------------------------
# Clip extraction
# ---------------------------------------------------------------------------


def slice_clip(
    audio_path: Path, start: float, end: float, out_path: Path
) -> tuple[Path, str]:
    """Cut [start, end) out of the source audio with ffmpeg.

    Returns the path and the content hash. The clip is content addressed so the
    evidence log can reference it by digest, which is what lets a report claim
    the clip has not been altered since the finding was written.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.05, end - start)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}",
        "-i", str(audio_path),
        "-c:a", "pcm_s16le",
        str(out_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise AudioError(f"ffmpeg failed: {result.stderr.strip()[:300]}")

    digest = hash_text(out_path.read_bytes().hex())
    return out_path, digest


def probe_duration(audio_path: Path) -> float:
    """Duration in seconds, read from the file rather than assumed."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(audio_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AudioError(f"ffprobe failed: {result.stderr.strip()[:200]}")
    return float(json.loads(result.stdout)["format"]["duration"])
