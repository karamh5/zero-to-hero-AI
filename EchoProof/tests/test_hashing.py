"""Tests for the canonical hashing that every integrity claim rests on.

The report seal, the evidence chain, the policy pack version and every finding's
integrity hash all reduce to this module. It had no tests, which meant nothing
verified that the chain hash actually depends on the previous hash. A chain
whose links do not depend on each other is not a chain.
"""

from __future__ import annotations

import pytest

from core.hashing import canonical_json, chain_hash, hash_object, hash_text, short


def test_canonical_json_is_stable_across_key_order() -> None:
    """Dict ordering must not change a hash, or every seal is unstable."""
    a = canonical_json({"b": 1, "a": 2, "c": {"z": 1, "y": 2}})
    b = canonical_json({"c": {"y": 2, "z": 1}, "a": 2, "b": 1})
    assert a == b
    assert hash_object({"b": 1, "a": 2}) == hash_object({"a": 2, "b": 1})


def test_canonical_json_is_ascii_safe() -> None:
    """The corpus contains section symbols and typographic quotes.

    Encoding-dependent output would make a hash depend on the console the run
    happened on.
    """
    text = canonical_json({"s": "§ 1006.14 “quoted”"})
    assert text.isascii()


def test_a_changed_payload_changes_the_digest() -> None:
    assert hash_object({"verdict": "supported"}) != hash_object(
        {"verdict": "contradicted"}
    )


def test_chain_hash_depends_on_the_previous_hash() -> None:
    """The property that makes the log tamper evident.

    Identical entries appended after different predecessors must produce
    different hashes, otherwise entries could be reordered or spliced freely.
    """
    entry = {"span_type": "judge.rule", "payload": {"verdict": "contradicted"}}
    assert chain_hash("aaa", entry) != chain_hash("bbb", entry)


def test_chain_hash_depends_on_the_entry() -> None:
    assert chain_hash("prev", {"x": 1}) != chain_hash("prev", {"x": 2})


def test_chain_hash_is_deterministic() -> None:
    entry = {"span_type": "finding.emit", "payload": {"section_id": "1006.14(g)"}}
    assert chain_hash("prev", entry) == chain_hash("prev", entry)


def test_genesis_entry_is_hashable() -> None:
    """The first entry has no predecessor and must still produce a hash."""
    assert len(chain_hash("", {"first": True})) == 64


def test_editing_an_early_entry_invalidates_everything_after_it() -> None:
    """Recomputing a chain after a mid-log edit must diverge from there on."""
    entries = [{"n": 1}, {"n": 2}, {"n": 3}]

    def build(items: list[dict]) -> list[str]:
        head = ""
        hashes = []
        for item in items:
            head = chain_hash(head, item)
            hashes.append(head)
        return hashes

    original = build(entries)
    tampered = build([{"n": 1}, {"n": 99}, {"n": 3}])

    assert original[0] == tampered[0]
    assert original[1] != tampered[1]
    assert original[2] != tampered[2]


def test_objects_with_to_dict_are_serialisable() -> None:
    class Thing:
        def to_dict(self) -> dict:
            return {"a": 1}

    assert hash_object({"thing": Thing()}) == hash_object({"thing": {"a": 1}})


def test_unserialisable_objects_raise_rather_than_hash_their_address() -> None:
    """A default repr would make the hash depend on memory layout."""

    class Opaque:
        pass

    with pytest.raises(TypeError):
        hash_object({"x": Opaque()})


def test_hash_text_is_sha256_length() -> None:
    assert len(hash_text("anything")) == 64


def test_short_is_display_only() -> None:
    digest = hash_text("x")
    assert short(digest, 12) == digest[:12]
    assert len(short(digest)) < len(digest)
