"""Tests for the offset to timestamp mapping (SPEC section 8).

No network. These exercise the deterministic core: transcript assembly from
tokens, interval overlap, clip bounds, and the numeric confidence rule. The
Deepgram calls around them are thin HTTP and are exercised by the end to end
demo instead.
"""

from __future__ import annotations

import pytest

from engine.audio import (
    build_transcript,
    clip_bounds,
    lowest_numeric_confidence,
    map_offsets_to_words,
    numeric_confidence_ok,
)

# Shaped exactly like Deepgram's words array.
WORDS = [
    {"word": "your", "punctuated_word": "Your", "start": 0.10, "end": 0.32, "confidence": 0.99},
    {"word": "balance", "punctuated_word": "balance", "start": 0.32, "end": 0.71, "confidence": 0.98},
    {"word": "is", "punctuated_word": "is", "start": 0.71, "end": 0.83, "confidence": 0.99},
    {"word": "4500", "punctuated_word": "$4,500,", "start": 0.83, "end": 1.42, "confidence": 0.91},
    {"word": "and", "punctuated_word": "and", "start": 1.42, "end": 1.55, "confidence": 0.97},
    {"word": "i", "punctuated_word": "I", "start": 1.55, "end": 1.63, "confidence": 0.96},
    {"word": "can", "punctuated_word": "can", "start": 1.63, "end": 1.80, "confidence": 0.98},
    {"word": "remove", "punctuated_word": "remove", "start": 1.80, "end": 2.21, "confidence": 0.95},
    {"word": "it", "punctuated_word": "it.", "start": 2.21, "end": 2.40, "confidence": 0.94},
]


def test_transcript_is_assembled_from_tokens() -> None:
    transcript, tokens = build_transcript(WORDS)
    assert transcript == "Your balance is $4,500, and I can remove it."
    assert len(tokens) == len(WORDS)


def test_every_token_span_slices_back_to_its_own_text() -> None:
    """The invariant the whole citation chain rests on."""
    transcript, tokens = build_transcript(WORDS)
    for token in tokens:
        assert transcript[token.char_start : token.char_end] == token.text


def test_claim_offsets_map_to_the_expected_words() -> None:
    transcript, tokens = build_transcript(WORDS)
    claim = "Your balance is $4,500,"
    start = transcript.index(claim)
    matched = map_offsets_to_words(tokens, start, start + len(claim))
    assert [t.text for t in matched] == ["Your", "balance", "is", "$4,500,"]


def test_mapping_includes_a_partially_covered_word() -> None:
    """A boundary falling inside a word must not clip that word from the audio."""
    transcript, tokens = build_transcript(WORDS)
    start = transcript.index("balan")
    matched = map_offsets_to_words(tokens, start, start + 3)
    assert [t.text for t in matched] == ["balance"]


def test_clip_bounds_cover_the_matched_words_with_padding() -> None:
    _transcript, tokens = build_transcript(WORDS)
    start, end = clip_bounds(tokens[0:4], pad_seconds=0.15)
    assert start == pytest.approx(0.10 - 0.15 if 0.10 - 0.15 > 0 else 0.0)
    assert end == pytest.approx(1.42 + 0.15)


def test_clip_bounds_never_go_negative() -> None:
    _transcript, tokens = build_transcript(WORDS)
    start, _end = clip_bounds(tokens[0:1], pad_seconds=5.0)
    assert start == 0.0


def test_clip_is_a_sentence_not_the_whole_call() -> None:
    """The point of SPEC section 8: cite the sentence, not the recording."""
    transcript, tokens = build_transcript(WORDS)
    claim = "I can remove it."
    start = transcript.index(claim)
    matched = map_offsets_to_words(tokens, start, start + len(claim))
    clip_start, clip_end = clip_bounds(matched)
    full_duration = tokens[-1].end - tokens[0].start
    assert (clip_end - clip_start) < full_duration


def test_numeric_token_detection() -> None:
    _transcript, tokens = build_transcript(WORDS)
    numeric = [t.text for t in tokens if t.is_numeric]
    assert numeric == ["$4,500,"]


def test_low_confidence_numeric_token_blocks_a_finding() -> None:
    """A misheard digit must abstain, never produce a fabricated allegation."""
    words = [dict(w) for w in WORDS]
    words[3]["confidence"] = 0.42
    _transcript, tokens = build_transcript(words)
    assert lowest_numeric_confidence(tokens) == pytest.approx(0.42)
    assert numeric_confidence_ok(tokens, floor=0.75) is False


def test_confidence_rule_ignores_non_numeric_tokens() -> None:
    """Only numeric tokens are gated, per SPEC section 8."""
    words = [dict(w) for w in WORDS]
    words[7]["confidence"] = 0.10  # "remove", not numeric
    _transcript, tokens = build_transcript(words)
    assert numeric_confidence_ok(tokens, floor=0.75) is True


def test_no_numeric_tokens_means_the_rule_does_not_block() -> None:
    words = [w for w in WORDS if "4500" not in w["word"]]
    _transcript, tokens = build_transcript(words)
    assert lowest_numeric_confidence(tokens) is None
    assert numeric_confidence_ok(tokens) is True
