"""ASPA verification on pathattr's decoded attributes (the reconstructed AS_PATH, section 5).

Provenance: the attribute bytes are hand-built from RFC 4271 section 4.3 (segments) and RFC 6793
sections 3 and 4.2.3 (AS_TRANS, AS4_PATH); the expected states are worked from
draft-ietf-sidrops-aspa-verification-29 sections 5.3 to 5.5.
"""

from __future__ import annotations

from typing import Any

import pytest

from routevalid.aspa import AspaState, Direction, segments_from_path, verify, verify_update

attribute = pytest.importorskip(
    "pathattr.attribute", reason="pathattr is a sibling checkout: ../pathattr (see pyproject)"
)
aspath = pytest.importorskip("pathattr.aspath")

UP = Direction.UPSTREAM


def h(text: str) -> bytes:
    return bytes.fromhex(text.replace(" ", ""))


def old_speaker_update() -> Any:
    """A two-octet session: AS_PATH 64500 23456, AS4_PATH 196618 (RFC 6793 section 4.2.3)."""
    raws = [
        attribute.RawAttribute(0x40, 2, h("02 02 fbf4 5ba0")),
        attribute.RawAttribute(0xC0, 17, h("02 01 0003000a")),
    ]
    return attribute.decode_attributes(raws, four_octet_as=False)


def test_reconstructed_path_is_what_aspa_judges() -> None:
    decoded = old_speaker_update()
    # RFC 6793 section 4.2.3: the leading surplus of AS_PATH, then AS4_PATH.
    assert [(s.type, s.asns) for s in decoded.effective_as_path] == [(2, (64500, 196618))]
    spas = {196618: frozenset({64500})}
    got = verify_update(decoded, spas, 64500, UP)
    assert got.state is AspaState.VALID
    assert got.path == (64500, 196618)
    # The unreconstructed AS_PATH holds AS_TRANS, which no ASPA mentions: Unknown, not Valid.
    naive = segments_from_path(decoded.as_path)
    assert verify(naive, spas, 64500, UP).state is AspaState.UNKNOWN


def test_reconstruction_exposes_a_leak_the_raw_path_hides() -> None:
    decoded = old_speaker_update()
    spas = {196618: frozenset({64999})}  # 64500 is not an attested provider of the origin
    assert verify_update(decoded, spas, 64500, UP).state is AspaState.INVALID
    assert verify(segments_from_path(decoded.as_path), spas, 64500, UP).state is AspaState.UNKNOWN


def test_four_octet_session_uses_as_path_as_is() -> None:
    raws = [attribute.RawAttribute(0x40, 2, h("02 02 0000fbf4 0003000a"))]
    decoded = attribute.decode_attributes(raws, four_octet_as=True)
    spas = {196618: frozenset({64500})}
    assert verify_update(decoded, spas, 64500, UP).state is AspaState.VALID


def test_missing_as_path_and_set_and_confederation_segments_are_invalid() -> None:
    empty = attribute.decode_attributes([], four_octet_as=True)
    got = verify_update(empty, {}, 64500, UP)
    assert (got.state, got.halted) == (AspaState.INVALID, "empty AS_PATH")
    with_set = attribute.decode_attributes(
        [attribute.RawAttribute(0x40, 2, h("01 01 0000fbf4 02 01 0003000a"))], four_octet_as=True
    )
    assert verify_update(with_set, {}, 64500, UP).halted == "AS_SET in AS_PATH"
    confed = attribute.decode_attributes(
        [attribute.RawAttribute(0x40, 2, h("03 01 0000fbf4 02 01 0003000a"))], four_octet_as=True
    )
    assert verify_update(confed, {}, 64500, UP).halted == "confederation segment"
