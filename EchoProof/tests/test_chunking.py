"""Tests for structure-aware chunking (SPEC section 5).

The invariant under test is that a chunk never contains text from outside its
own section. If it did, a finding could quote a rule that is half one provision
and half another while printing a single section identifier beside it.
"""

from __future__ import annotations

import pytest

from core.contracts import ObligationType, PolicySection
from engine.retrieval.chunking import (
    MAX_CHUNK_CHARS,
    ChunkingError,
    build_chunks,
    split_long_text,
)


def section(section_id: str, text: str, parent: str | None = None) -> PolicySection:
    return PolicySection(
        section_id=section_id,
        parent_section=parent,
        verbatim_text=text,
        obligation_type=ObligationType.PROHIBITION,
        heading=f"Heading for {section_id}",
    )


def test_every_chunk_text_belongs_to_its_own_section() -> None:
    sections = [
        section("1006.1", "A debt collector must not do the first thing."),
        section("1006.2", "A debt collector must not do the second thing."),
    ]
    chunks = build_chunks(sections)
    by_id = {s.section_id: s.verbatim_text for s in sections}
    for chunk in chunks:
        assert chunk.text in by_id[chunk.section_id]


def test_boundary_violation_is_detected_rather_than_shipped() -> None:
    """The assertion exists so a future refactor cannot quietly break this."""
    sections = [section("1006.1", "Real text.")]
    chunks = build_chunks(sections)
    broken = type(chunks[0])(
        chunk_id="1006.1",
        section_id="1006.1",
        parent_heading="x",
        text="Text that is not in the section at all.",
    )
    with pytest.raises(ChunkingError):
        from engine.retrieval.chunking import _assert_no_boundary_spanning

        _assert_no_boundary_spanning([broken], sections)


def test_short_text_is_one_chunk() -> None:
    assert len(split_long_text("One short sentence.")) == 1


def test_long_text_splits_on_sentence_boundaries() -> None:
    sentence = "A debt collector must not place repeated telephone calls. "
    long_text = sentence * 60
    pieces = split_long_text(long_text)
    assert len(pieces) > 1
    assert all(len(p) <= MAX_CHUNK_CHARS + len(sentence) for p in pieces)


def test_parent_stem_is_carried_into_context() -> None:
    """An enumerated child is meaningless without the clause it hangs from.

    1006.18(b)(1) says "must not falsely represent that:" and its children say
    only the thing represented. Indexed alone the child contains no prohibition.
    """
    sections = [
        section("1006.18(b)(1)", "A debt collector must not falsely represent that:"),
        section(
            "1006.18(b)(1)(i)",
            "The debt collector is affiliated with the United States.",
            parent="1006.18(b)(1)",
        ),
    ]
    chunks = build_chunks(sections)
    child = next(c for c in chunks if c.section_id == "1006.18(b)(1)(i)")
    assert "must not falsely represent" in child.parent_heading
    assert "affiliated with the United States" in child.text


def test_a_complete_parent_is_not_pulled_into_the_child() -> None:
    """Only list stems, which end in a colon, continue into their children."""
    sections = [
        section("1006.14(a)", "A debt collector must not harass any person."),
        section(
            "1006.14(a)(1)",
            "Using obscene language.",
            parent="1006.14(a)",
        ),
    ]
    chunks = build_chunks(sections)
    child = next(c for c in chunks if c.section_id == "1006.14(a)(1)")
    assert "must not harass" not in child.parent_heading


def test_empty_sections_are_skipped_not_indexed() -> None:
    chunks = build_chunks([section("1006.1", "   "), section("1006.2", "Real.")])
    assert [c.section_id for c in chunks] == ["1006.2"]


def test_embed_text_puts_the_heading_first() -> None:
    chunks = build_chunks([section("1006.1", "The body text.")])
    assert chunks[0].embed_text.startswith("1006.1")
    assert "The body text." in chunks[0].embed_text
