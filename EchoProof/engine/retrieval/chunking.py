"""Structure-aware chunking (SPEC section 5).

Two rules govern this module and both exist to protect citation accuracy:

1. A chunk never spans a section boundary. If it did, a finding could quote a
   rule that is half one provision and half another, and the section_id printed
   on the finding card would be wrong for part of the quoted text.

2. Every chunk carries its parent heading into the text that gets embedded.
   A paragraph reading "(A) More than seven times within seven consecutive
   days; nor" is meaningless in isolation. Without the heading, the dense
   retriever has nothing to match a query about call frequency against.
"""

from __future__ import annotations

import re

from core.contracts import Chunk, PolicySection

# Long provisions get split so a single chunk does not dominate the index or
# blow past the embedding model's context. The split is on sentence boundaries
# and always stays inside one section.
MAX_CHUNK_CHARS = 1200
MIN_TAIL_CHARS = 200

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.;:])\s+(?=[A-Z(“\"])")


class ChunkingError(ValueError):
    """Raised when chunking would violate a section boundary."""


def split_long_text(text: str) -> list[str]:
    """Split on sentence boundaries, packing up to MAX_CHUNK_CHARS per piece."""
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    sentences = _SENTENCE_BOUNDARY.split(text)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > MAX_CHUNK_CHARS:
            pieces.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip() if current else sentence
    if current.strip():
        # A tiny trailing fragment retrieves badly on its own, so fold it back.
        if pieces and len(current.strip()) < MIN_TAIL_CHARS:
            pieces[-1] = f"{pieces[-1]} {current.strip()}"
        else:
            pieces.append(current.strip())
    return pieces


def build_chunks(sections: list[PolicySection]) -> list[Chunk]:
    """Turn policy records into retrievable chunks."""
    by_id = {s.section_id: s for s in sections}
    chunks: list[Chunk] = []
    for section in sections:
        text = section.verbatim_text.strip()
        if not text:
            continue
        heading = _heading_for(section, by_id)
        pieces = split_long_text(text)
        for index, piece in enumerate(pieces):
            suffix = f"#{index}" if len(pieces) > 1 else ""
            chunks.append(
                Chunk(
                    chunk_id=f"{section.section_id}{suffix}",
                    section_id=section.section_id,
                    parent_heading=heading,
                    text=piece,
                )
            )
    _assert_no_boundary_spanning(chunks, sections)
    return chunks


def _heading_for(
    section: PolicySection, by_id: dict[str, PolicySection]
) -> str:
    """The context line prepended to a chunk before embedding.

    Carries the section heading AND every enclosing list stem. Legal text
    distributes one operative clause across a parent and its enumerated
    children: 1006.18(b)(1) says "A debt collector must not falsely represent or
    imply that:" and 1006.18(b)(1)(i) then says only "The debt collector is
    vouched for, bonded by, or affiliated with the United States". Indexed
    alone, that child contains no prohibition at all, no modal verb, and nothing
    a query about false government affiliation can match. Retrieval was
    returning the parent stub instead of the specific paragraph, which would
    have put an imprecise citation on the finding card.

    Only ancestors whose text ends in a colon are pulled in. Those are list
    stems, whose meaning genuinely continues into the child. An ancestor that
    ends in a full stop is a complete provision and does not.
    """
    parts = [section.section_id]
    if section.heading:
        parts.append(section.heading)

    stems: list[str] = []
    parent_id = section.parent_section
    while parent_id is not None:
        parent = by_id.get(parent_id)
        if parent is None:
            break
        parent_text = parent.verbatim_text.strip()
        if parent_text.endswith(":"):
            stems.append(parent_text)
        parent_id = parent.parent_section

    parts.extend(reversed(stems))
    return " ".join(parts).strip()


def _assert_no_boundary_spanning(
    chunks: list[Chunk], sections: list[PolicySection]
) -> None:
    """Verify rule 1 above rather than trusting it.

    This is cheap and it catches the failure that matters: a refactor that packs
    short adjacent paragraphs together to reduce chunk count would silently
    produce chunks whose text does not belong to their section_id.
    """
    by_id = {s.section_id: s.verbatim_text for s in sections}
    for chunk in chunks:
        source = by_id.get(chunk.section_id)
        if source is None:
            raise ChunkingError(f"chunk {chunk.chunk_id} has no source section")
        if chunk.text not in source:
            raise ChunkingError(
                f"chunk {chunk.chunk_id} text is not a substring of section "
                f"{chunk.section_id}; chunking crossed a boundary"
            )
