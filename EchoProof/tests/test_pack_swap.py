"""Engine/pack boundary tests (SPEC section 1).

The claim under test is that the engine has no constant that knows which corpus
it is running against. These pin the two places where it did.
"""

from __future__ import annotations

from engine.retrieval.base import is_within, root_section

CFR = ("(", "#")
DOTTED = (".",)


def test_root_section_under_the_cfr_convention() -> None:
    assert root_section("1006.14(b)(1)", CFR) == "1006.14"
    assert root_section("1006.6(d)(4)(ii)(C)(5)", CFR) == "1006.6"
    assert root_section("1006.104", CFR) == "1006.104"


def test_root_section_under_a_dotted_convention() -> None:
    """The defect the pack swap exposed.

    With parentheses hardcoded, CC-3.1 had no separator to split on, so every
    identifier became its own root and conflict detection stopped working.
    """
    assert root_section("CC-3.1", DOTTED) == "CC-3"
    assert root_section("CC-5.3", DOTTED) == "CC-5"
    assert root_section("CC-1", DOTTED) == "CC-1"


def test_chunk_suffix_is_always_stripped() -> None:
    """The #n suffix is engine-generated, not corpus-specific."""
    assert root_section("CC-3.1#2", DOTTED) == "CC-3"
    assert root_section("1006.14(b)#1", CFR) == "1006.14"


def test_is_within_accepts_a_more_specific_paragraph() -> None:
    assert is_within("1006.14(b)", "1006.14(b)(1)", CFR)
    assert is_within("CC-3", "CC-3.1", DOTTED)


def test_is_within_rejects_a_mere_prefix() -> None:
    """1006.2 must not match 1006.22, and CC-3 must not match CC-30."""
    assert not is_within("1006.2", "1006.22", CFR)
    assert not is_within("CC-3", "CC-30", DOTTED)


def test_is_within_accepts_an_exact_match() -> None:
    assert is_within("CC-2.3", "CC-2.3", DOTTED)


def test_is_within_rejects_unrelated_identifiers() -> None:
    assert not is_within("CC-2.3", "CC-5.1", DOTTED)
    assert not is_within("1006.14(g)", "1006.18(e)(1)", CFR)


def test_defaults_preserve_regulation_f_behaviour() -> None:
    """Scored Regulation F results must not move because of this change.

    CLAUDE.md decision 9 fixes the backend for a run whose numbers are reported,
    and a boundary fix that silently altered them would be a regression dressed
    as a refactor.
    """
    assert root_section("1006.14(b)(1)") == "1006.14"
    assert is_within("1006.14(b)", "1006.14(b)(1)")
    assert not is_within("1006.2", "1006.22")


def test_the_synthetic_pack_declares_its_own_scheme() -> None:
    from core.packs import load_policy_pack

    pack = load_policy_pack("synth_telecom")
    assert pack.hierarchy_separators == (".",)
    assert len(pack.sections) == 15
    assert pack.sections[0].section_id.startswith("CC-")


def test_regulation_f_pack_falls_back_to_the_cfr_scheme() -> None:
    from core.packs import load_policy_pack

    pack = load_policy_pack("reg_f")
    assert pack.hierarchy_separators == ("(", "#")
