"""Build a policy pack from the eCFR API.

This is a corpus ingester, not engine code. It knows about eCFR XML and about
12 CFR 1006 specifically. That is fine and intended: the engine/pack boundary in
ARCHITECTURE.md says a new vertical means new pack files, and a new corpus format
means a new ingester next to this one. Nothing under engine/ imports this.

Output, written to packs/policy/reg_f/:
    sections.jsonl  one record per addressable paragraph, in the SPEC section 1
                    schema.
    manifest.json   corpus-level provenance including the document hash that
                    SPEC section 7 pins onto every finding as
                    policy_pack_version.

Run:
    python scripts/build_policy_pack_ecfr.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

import requests
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import POLICY_DIR  # noqa: E402
from core.contracts import ObligationType, PolicySection  # noqa: E402
from core.hashing import HASH_SCHEME, hash_text  # noqa: E402

ECFR_BASE = "https://www.ecfr.gov/api/versioner/v1"
PACK_ID = "reg_f"

# The corpus this pack covers. Everything below that is 12-CFR-1006-specific
# lives in this block so a sibling ingester can be written by copying the file
# and changing these five values.
CORPUS = {
    "title": "12",
    "chapter": "X",
    "subchapter": "V",
    "part": "1006",
    "label": "12 CFR Part 1006 (Regulation F), Debt Collection Practices",
}

# Section 1006.2 is the definitions section. Terms defined there are collected
# once and then cross-referenced into every other record.
DEFINITIONS_SECTION = "1006.2"


# ---------------------------------------------------------------------------
# Paragraph designator handling
#
# eCFR serves every paragraph of a section as a flat sibling <P>. The hierarchy
# exists only as designators embedded in the text: "(a)", then "(1)", then
# "(i)", then "(A)". Reconstructing the tree means deciding, for each
# designator, which level it belongs to.
#
# The hard case is "(i)", which is both the ninth lowercase letter and the first
# lowercase roman numeral. Context decides: if a digit level is currently open
# and no roman level is, "(i)" opens the roman level; if the alpha level is
# currently at "(h)", it continues the alpha level. The resolver below works by
# preferring whichever interpretation continues an open sequence.
# ---------------------------------------------------------------------------

ROMAN_SEQUENCE = [
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
]

ALPHA_LOWER = "alpha_lower"
DIGIT = "digit"
ROMAN_LOWER = "roman_lower"
ALPHA_UPPER = "alpha_upper"

# CFR designator styles cycle with depth: (a) (1) (i) (A) (1) (i) ... Modelling
# each style as belonging to exactly one fixed level is wrong and produced two
# distinct identifier collisions on the first build. In 1006.6(d)(4)(ii)(C) the
# regulation nests a numbered list at depth five, whose "(1)" collided with the
# real 1006.6(d)(1). Style has to be a function of depth, not an identity.
STYLE_BY_DEPTH = [
    ALPHA_LOWER,   # depth 1
    DIGIT,         # depth 2
    ROMAN_LOWER,   # depth 3
    ALPHA_UPPER,   # depth 4
    DIGIT,         # depth 5
    ROMAN_LOWER,   # depth 6
    ALPHA_UPPER,   # depth 7
]
MAX_DEPTH = len(STYLE_BY_DEPTH)

FIRST_OF_STYLE = {
    ALPHA_LOWER: "a",
    DIGIT: "1",
    ROMAN_LOWER: "i",
    ALPHA_UPPER: "A",
}


def _style_at(depth: int) -> str | None:
    """The designator style CFR uses at a given nesting depth."""
    if 1 <= depth <= MAX_DEPTH:
        return STYLE_BY_DEPTH[depth - 1]
    return None


def _matches_style(token: str, style: str) -> bool:
    """Whether a raw token could be a designator of this style.

    Deliberately permissive for lowercase romans: "i", "v" and "x" are valid
    tokens in both the alpha-lower and roman-lower styles, and which one is
    meant is a question about position, not about the token.
    """
    if style == DIGIT:
        return token.isdigit()
    if style == ALPHA_LOWER:
        return len(token) == 1 and token.isalpha() and token.islower()
    if style == ROMAN_LOWER:
        return token in ROMAN_SEQUENCE
    if style == ALPHA_UPPER:
        return len(token) == 1 and token.isalpha() and token.isupper()
    return False

DESIGNATOR_RE = re.compile(r"^\s*\(([0-9A-Za-z]{1,5})\)\s*")

# Characters eCFR uses to join a run-in heading to the designator that follows
# it. Built with chr() rather than written literally: the repository convention
# bans em dashes in source, and this keeps the codepoints explicit rather than
# dependent on how the file is encoded on disk.
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
RUN_IN_JOINERS = "." + EM_DASH + EN_DASH + "- "


class DesignatorError(ValueError):
    """Raised when a designator cannot be placed in the hierarchy."""


def _successor(style: str, current: str) -> str:
    """The designator that should follow `current` in this style."""
    if style == DIGIT:
        return str(int(current) + 1)
    if style == ROMAN_LOWER:
        index = ROMAN_SEQUENCE.index(current)
        return ROMAN_SEQUENCE[index + 1] if index + 1 < len(ROMAN_SEQUENCE) else ""
    # Alpha sequences in this corpus skip nothing, so a character increment is
    # sufficient. CFR does skip letters in some other parts, which would need a
    # per-corpus alphabet rather than this.
    return chr(ord(current) + 1)


class HierarchyResolver:
    """Turns a flat stream of designators into a path like ('b', '1', 'iii').

    Placement is decided by two rules, applied in order:

    1. If the token is the first designator of the style used one level deeper
       than the current position, it opens that level. This is what makes "(i)"
       following "(h)(2)" a roman numeral opening depth three rather than the
       letter after "(h)".

    2. Otherwise the token advances the deepest currently-open level whose style
       matches and whose sequence it continues. This is what keeps "(c)" after
       "(h)(2)(iii)" at depth one.

    The residual ambiguity is real and worth naming: a section that reaches
    "(h)(1)" and then opens a genuine top-level "(i)" would be misread as a
    roman numeral. That shape does not occur in this corpus, and rule 2 handles
    the case that does occur, 1006.2(i), because it is reached from depth one.
    """

    def __init__(self) -> None:
        # depth -> most recent designator seen at that depth
        self._open: dict[int, str] = {}
        self._depth = 0

    @property
    def path(self) -> tuple[str, ...]:
        return tuple(self._open[d] for d in range(1, self._depth + 1) if d in self._open)

    def push(self, token: str) -> None:
        chosen = self._choose(token)
        if chosen is None:
            raise DesignatorError(f"cannot place designator '({token})'")
        # Opening or advancing a level closes everything deeper than it.
        for deeper in [d for d in self._open if d > chosen]:
            del self._open[deeper]
        self._open[chosen] = token
        self._depth = chosen

    def _choose(self, token: str) -> int | None:
        # Rule 1: open the next level down.
        next_depth = self._depth + 1
        next_style = _style_at(next_depth)
        if (
            next_style is not None
            and _matches_style(token, next_style)
            and token == FIRST_OF_STYLE[next_style]
        ):
            return next_depth

        # Rule 2: advance the deepest open level this token continues.
        for depth in range(self._depth, 0, -1):
            style = _style_at(depth)
            if style is None or depth not in self._open:
                continue
            if _matches_style(token, style) and _successor(style, self._open[depth]) == token:
                return depth

        # Fallbacks for irregular drafting: the first designator of a section,
        # or a sequence that skips a value. Prefer the shallowest depth whose
        # style accepts the token.
        for depth in range(1, MAX_DEPTH + 1):
            style = _style_at(depth)
            if style is not None and _matches_style(token, style):
                return depth
        return None


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def _paragraph_text(node: etree._Element) -> str:
    """Flatten a <P> to plain text, preserving reading order."""
    return re.sub(r"\s+", " ", "".join(node.itertext())).strip()


def _italic_heading(node: etree._Element) -> str:
    """The paragraph's italic run-in heading, if it has one.

    eCFR marks run-in headings with <I>. Only a leading <I> counts: an italic
    case name in the middle of a sentence is not a heading.
    """
    for child in node:
        if child.tag == "I":
            head = re.sub(r"\s+", " ", "".join(child.itertext())).strip()
            return head.rstrip(".")
        break
    return ""


def _split_designators(text: str, heading: str) -> tuple[list[str], str]:
    """Peel leading designators off a paragraph, returning them and the body.

    Handles the combined form eCFR uses freely, where one <P> opens two levels
    at once: "(b) <I>Heading.</I> (1) A debt collector must not ...".
    """
    designators: list[str] = []
    remaining = text
    skipped_heading = False

    while True:
        match = DESIGNATOR_RE.match(remaining)
        if match:
            designators.append(match.group(1))
            remaining = remaining[match.end() :]
            continue
        # Allow exactly one run-in heading to sit between two designators.
        # eCFR punctuates the join inconsistently: "(c) Heading. (1) body" and
        # "(b) Heading-(1) body" both occur, the latter with an em dash. Not
        # stripping the dash lost paragraph 1006.14(b)(1), the core call
        # frequency prohibition, which is exactly the kind of provision this
        # system exists to cite.
        if heading and not skipped_heading and remaining.startswith(heading):
            # Escapes rather than literal dashes: the repository convention
            # bans em dashes in source, and the escape says which codepoint is
            # meant without depending on the file encoding.
            candidate = remaining[len(heading) :].lstrip(RUN_IN_JOINERS)
            if DESIGNATOR_RE.match(candidate):
                remaining = candidate
                skipped_heading = True
                continue
        break

    return designators, remaining.strip()


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

PROHIBITION_RE = re.compile(r"\bmust not\b|\bmay not\b|\bshall not\b|\bprohibit", re.I)
REQUIREMENT_RE = re.compile(r"\bmust\b|\bshall\b|\brequired to\b", re.I)
PERMISSION_RE = re.compile(r"\bmay\b|\bis permitted\b|\bnothing .* prohibits\b", re.I)

CROSS_REF_RE = re.compile(
    r"(?:§+\s*)?\b(1006\.\d+)((?:\([0-9A-Za-z]{1,5}\))*)|paragraph\s+((?:\([0-9A-Za-z]{1,5}\))+)",
    re.I,
)


def _root_of(section_id: str) -> str:
    """The root section a paragraph identifier belongs to.

    Written as an explicit split rather than a prefix test because "1006.2" is a
    prefix of "1006.22" and "1006.26". Treating those as the definitions section
    silently pulled run-in headings from time-barred-debt and unauthorised-
    charges provisions into the defined-terms list.
    """
    return section_id.split("(")[0]


DEFINITION_HEADING_RE = re.compile(r"^definitions?$", re.I)
DEFINITION_BODY_RE = re.compile(r"\bmeans\b|\bhas the same meaning\b", re.I)
CARVE_OUT_HEADING_RE = re.compile(r"exclu|except|safe harbor", re.I)


def _classify(
    text: str, section_id: str, heading: str = ""
) -> ObligationType | None:
    """Assign an obligation type from the text of the paragraph.

    Order matters: "must not" has to be tested before "must", or every
    prohibition is misfiled as a requirement.

    Returns None when the paragraph carries no modal of its own. That is the
    common case for enumerated sub-paragraphs: "(b)(1) A debt collector must not
    falsely represent or imply that:" followed by "(i) The debt collector is
    vouched for ...". The sub-paragraph is a prohibition, but only by inheriting
    from its parent. Defaulting these to `definition` mislabelled 224 of 303
    records on the first build, which would have made obligation_type useless as
    a retrieval or severity signal.
    """
    if _root_of(section_id) == DEFINITIONS_SECTION:
        return ObligationType.DEFINITION
    # A definitional paragraph outside the definitions section still defines.
    # Without this, 1006.14(b)(4) ("particular debt means ...") inherited the
    # surrounding call frequency prohibition purely because it states no modal.
    if DEFINITION_HEADING_RE.match(heading) or DEFINITION_BODY_RE.search(text):
        return ObligationType.DEFINITION
    # A carve-out is a permission even though it sits inside a prohibition, and
    # inheriting the prohibition would invert its meaning.
    if heading and CARVE_OUT_HEADING_RE.search(heading):
        return ObligationType.PERMISSION
    if PROHIBITION_RE.search(text):
        return ObligationType.PROHIBITION
    if REQUIREMENT_RE.search(text):
        return ObligationType.REQUIREMENT
    if PERMISSION_RE.search(text):
        return ObligationType.PERMISSION
    return None


def inherit_obligations(
    pairs: list[tuple[PolicySection, ObligationType | None]]
) -> list[PolicySection]:
    """Fill unclassified paragraphs from the enclosing provision.

    Inheritance walks depth, not identifiers. Looking up the literal parent
    identifier fails whenever an intermediate level has no paragraph of its own,
    which happens throughout eCFR: 1006.14(b)(2)(i) exists, but neither
    1006.14(b)(2) nor 1006.14(b) is ever emitted as its own <P>, so an
    identifier walk finds no ancestor and falls back to `definition`. That
    mislabelled the entire call frequency presumption as a definition.

    Tracking the most recent classified obligation at each depth in document
    order resolves it: an unclassified paragraph at depth 3 inherits from the
    most recent classification at depth 2 or shallower, which for that example
    is the "must not place telephone calls" prohibition it sits under.
    """
    by_depth: dict[int, ObligationType] = {}
    out: list[PolicySection] = []

    for section, explicit in pairs:
        depth = section.section_id.count("(")
        obligation = explicit

        if obligation is None:
            shallower = [d for d in by_depth if d < depth]
            if shallower:
                obligation = by_depth[max(shallower)]
        if obligation is None:
            obligation = ObligationType.DEFINITION

        by_depth[depth] = obligation
        # Opening a shallower level invalidates everything deeper, or a stale
        # deep classification would leak sideways into the next provision.
        for deeper in [d for d in by_depth if d > depth]:
            del by_depth[deeper]
        out.append(
            PolicySection(
                section_id=section.section_id,
                parent_section=section.parent_section,
                verbatim_text=section.verbatim_text,
                obligation_type=obligation,
                cross_references=section.cross_references,
                defined_terms=section.defined_terms,
                heading=section.heading,
            )
        )
    return out


def _cross_references(text: str, root_section: str) -> list[str]:
    """Collect references to other sections and to sibling paragraphs."""
    refs: list[str] = []
    for match in CROSS_REF_RE.finditer(text):
        if match.group(1):
            refs.append(match.group(1) + (match.group(2) or ""))
        elif match.group(3):
            # "paragraph (b)(1)" is relative to the section it appears in.
            refs.append(root_section + match.group(3))
    seen: set[str] = set()
    ordered: list[str] = []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            ordered.append(ref)
    return ordered


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def fetch_part_xml(date: str) -> bytes:
    """Download the part as XML for a specific issue date."""
    params = {
        "chapter": CORPUS["chapter"],
        "subchapter": CORPUS["subchapter"],
        "part": CORPUS["part"],
    }
    url = f"{ECFR_BASE}/full/{date}/title-{CORPUS['title']}.xml"
    response = requests.get(url, params=params, timeout=120)
    response.raise_for_status()
    return response.content


def latest_issue_date() -> str:
    """Ask eCFR for the newest issue date of this title."""
    response = requests.get(f"{ECFR_BASE}/titles.json", timeout=60)
    response.raise_for_status()
    for title in response.json()["titles"]:
        if str(title["number"]) == CORPUS["title"]:
            return title["latest_issue_date"]
    raise RuntimeError(f"title {CORPUS['title']} not present in eCFR titles.json")


def parse_sections(
    xml_bytes: bytes,
) -> Iterator[tuple[PolicySection, ObligationType | None]]:
    """Walk the part XML and yield one record per addressable unit.

    The second element of each pair is the obligation type the paragraph states
    for itself, or None when it states none. `inherit_obligations` resolves the
    Nones afterwards, once every parent is known.
    """
    root = etree.fromstring(xml_bytes)

    for div in root.iter("DIV8"):
        if div.get("TYPE") != "SECTION":
            continue
        root_section = (div.get("N") or "").strip()
        if not root_section:
            continue

        head_node = div.find("HEAD")
        section_heading = (
            re.sub(r"\s+", " ", "".join(head_node.itertext())).strip()
            if head_node is not None
            else ""
        )
        # Strip the leading section symbol and number from the heading so the
        # heading reads as a title rather than repeating the identifier.
        section_title = re.sub(r"^§+\s*[\d.]+\s*", "", section_heading).strip()

        resolver = HierarchyResolver()
        emitted_any = False
        full_text_parts: list[str] = []

        for para in div.findall("P"):
            text = _paragraph_text(para)
            if not text:
                continue
            full_text_parts.append(text)

            heading = _italic_heading(para)
            designators, body = _split_designators(text, heading)
            if not body:
                body = text

            if not designators:
                # An undesignated paragraph belongs to whatever is currently
                # open. Attaching it there beats inventing an identifier.
                path = resolver.path
            else:
                for token in designators:
                    try:
                        resolver.push(token)
                    except DesignatorError:
                        break
                path = resolver.path

            if not path:
                continue

            section_id = root_section + "".join(f"({d})" for d in path)
            parent = (
                root_section + "".join(f"({d})" for d in path[:-1])
                if len(path) > 1
                else root_section
            )
            emitted_any = True
            yield (
                PolicySection(
                    section_id=section_id,
                    parent_section=parent,
                    verbatim_text=body,
                    obligation_type=ObligationType.DEFINITION,  # placeholder
                    cross_references=_cross_references(body, root_section),
                    defined_terms=[],
                    heading=f"{section_heading} {heading}".strip()
                    if heading
                    else section_heading,
                ),
                _classify(body, section_id, heading),
            )

        # A section with no designated paragraphs still needs a record, or it
        # becomes unretrievable and therefore uncitable.
        if not emitted_any:
            body = " ".join(full_text_parts).strip()
            if body:
                yield (
                    PolicySection(
                        section_id=root_section,
                        parent_section=None,
                        verbatim_text=body,
                        obligation_type=ObligationType.DEFINITION,  # placeholder
                        cross_references=_cross_references(body, root_section),
                        defined_terms=[],
                        heading=section_heading,
                    ),
                    _classify(body, root_section),
                )
        _ = section_title


def collect_defined_terms(sections: list[PolicySection]) -> list[str]:
    """Pull the defined terms out of the definitions section's headings."""
    terms: list[str] = []
    for section in sections:
        if _root_of(section.section_id) != DEFINITIONS_SECTION:
            continue
        heading = section.heading
        # The run-in heading of a definition paragraph is the term itself, and
        # it is appended after the section heading by parse_sections.
        marker = re.sub(r"^§+\s*[\d.]+\s*[^§]*?\.\s*", "", heading).strip()
        if marker and len(marker) < 60 and marker.lower() not in {t.lower() for t in terms}:
            terms.append(marker)
    return terms


def annotate_defined_terms(
    sections: list[PolicySection], terms: list[str]
) -> list[PolicySection]:
    """Record which defined terms each paragraph actually uses."""
    patterns = [(term, re.compile(rf"\b{re.escape(term)}\b", re.I)) for term in terms]
    annotated: list[PolicySection] = []
    for section in sections:
        used = [term for term, pattern in patterns if pattern.search(section.verbatim_text)]
        annotated.append(
            PolicySection(
                section_id=section.section_id,
                parent_section=section.parent_section,
                verbatim_text=section.verbatim_text,
                obligation_type=section.obligation_type,
                cross_references=section.cross_references,
                defined_terms=used,
                heading=section.heading,
            )
        )
    return annotated


def build(date: str | None = None) -> dict[str, Any]:
    issue_date = date or latest_issue_date()
    xml_bytes = fetch_part_xml(issue_date)
    source_hash = hash_text(xml_bytes.decode("utf-8", errors="strict"))

    pairs = list(parse_sections(xml_bytes))
    if not pairs:
        raise RuntimeError("parsed zero sections; the eCFR XML layout has changed")

    sections = inherit_obligations(pairs)

    # Identifier collisions are silent and corrosive: two records sharing a
    # section_id means a finding can cite text that is not the text at that
    # citation. Both hierarchy bugs found while building this pack surfaced as
    # duplicates, so the check stays in permanently rather than being a one-off
    # debugging step.
    duplicates = _duplicate_ids([s.section_id for s in sections])
    if duplicates:
        raise RuntimeError(
            f"{len(duplicates)} duplicate section_id(s) produced, "
            f"first few: {duplicates[:5]}. The designator hierarchy is wrong."
        )

    terms = collect_defined_terms(sections)
    sections = annotate_defined_terms(sections, terms)

    out_dir = POLICY_DIR / PACK_ID
    out_dir.mkdir(parents=True, exist_ok=True)

    records = [s.to_dict() for s in sections]
    sections_path = out_dir / "sections.jsonl"
    with sections_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    # The pack hash covers the parsed records, not the raw XML. That is what
    # findings pin: if parsing changes, the pack version has to change too, even
    # when the underlying regulation did not.
    pack_hash = hash_text(
        "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=True) for r in records)
    )

    root_sections = sorted({r["section_id"].split("(")[0] for r in records})
    manifest = {
        "pack_id": PACK_ID,
        "label": CORPUS["label"],
        "source": "ecfr.gov",
        "issue_date": issue_date,
        "citation": f"{CORPUS['title']} CFR {CORPUS['part']}",
        "hash_scheme": HASH_SCHEME,
        "source_document_hash": source_hash,
        "policy_pack_version": pack_hash,
        "record_count": len(records),
        "root_section_count": len(root_sections),
        "root_sections": root_sections,
        "defined_terms": terms,
        "obligation_counts": _counts(records),
        # How this corpus separates hierarchy levels. Declared by the pack
        # because it is a property of the drafting convention, not of the
        # engine. CFR nests with parentheses; another corpus may nest with dots.
        "section_id_scheme": {
            "hierarchy_separators": ["(", "#"],
            "root_pattern_example": "1006.14(b)(1) -> 1006.14",
        },
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def _duplicate_ids(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for identifier in ids:
        if identifier in seen and identifier not in duplicates:
            duplicates.append(identifier)
        seen.add(identifier)
    return duplicates


def _counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        key = record["obligation_type"]
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Regulation F policy pack.")
    parser.add_argument(
        "--date",
        default=None,
        help="eCFR issue date (YYYY-MM-DD). Defaults to the latest for title 12.",
    )
    args = parser.parse_args()

    manifest = build(args.date)

    print(f"pack_id              {manifest['pack_id']}")
    print(f"citation             {manifest['citation']}")
    print(f"issue_date           {manifest['issue_date']}")
    print(f"root sections        {manifest['root_section_count']}")
    print(f"paragraph records    {manifest['record_count']}")
    print(f"defined terms        {len(manifest['defined_terms'])}")
    print(f"obligation counts    {manifest['obligation_counts']}")
    print(f"source_document_hash {manifest['source_document_hash']}")
    print(f"policy_pack_version  {manifest['policy_pack_version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
