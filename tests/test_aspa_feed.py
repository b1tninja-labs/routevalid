"""The U-SPAS feed: pairs, mappings, and the ASPA records an RTR router holds.

Provenance: the byte strings are hand-built from Figure 11 of draft-ietf-sidrops-8210bis-29 (the
draft prints no vectors), the same ones rtrkit's own tests use. The expectations come from
section 5.12 (one PDU per customer, a replacement for the same customer, a withdrawal removes the
record) and from draft-ietf-sidrops-aspa-verification-29 section 5.3 for the union.
"""

from __future__ import annotations

import pytest

from routevalid.aspa import AspaState, Direction, feed, verify

rtrkit = pytest.importorskip(
    "rtrkit", reason="rtrkit is a sibling checkout: ../rtrkit (see pyproject pythonpath)"
)


payload = pytest.importorskip("rtrkit.payload")


def h(text: str) -> bytes:
    return bytes.fromhex(text.replace(" ", ""))


def test_feed_unions_pairs_and_accepts_a_mapping() -> None:
    pairs = [(1, [2]), (1, [3]), (5, [0])]
    assert feed(pairs) == {1: frozenset({2, 3}), 5: frozenset({0})}
    assert feed({1: (2, 3), 5: (0,)}) == feed(pairs)
    assert feed(iter(pairs)) == feed(pairs)


def test_feed_refuses_a_record_with_no_provider() -> None:
    with pytest.raises(ValueError, match="at least one"):
        feed([(1, [])])
    with pytest.raises(ValueError, match="at least one"):
        feed({1: ()})


def test_feed_reads_the_aspa_records_of_an_rtr_payload() -> None:
    # Figure 11: version 2, type 11, flags 0x01 announce; customer 64496, providers 64497 and 64498.
    wire = h("02 0B 0100 00000014 0000FBF0 0000FBF1 0000FBF2") + h(
        "02 0B 0100 00000010 0000FBF3 00000000"  # customer 64499, the AS0 ASPA
    )
    db = payload.PayloadDb()
    pdus = []
    while wire:
        pdu, used = rtrkit.decode_pdu(wire)
        pdus.append(pdu)
        wire = wire[used:]
    payload.apply_payload(db, pdus)
    table = feed(db)
    assert table == {64496: frozenset({64497, 64498}), 64499: frozenset({0})}
    assert feed(db.aspas) == table


def test_rtr_replacement_and_withdrawal_reach_the_table() -> None:
    db = payload.PayloadDb()
    announce = rtrkit.Aspa(2, True, 64496, (64497,))
    replace = rtrkit.Aspa(2, True, 64496, (64498,))  # section 5.12: replaces, never adds
    payload.apply_payload(db, [announce])
    assert feed(db) == {64496: frozenset({64497})}
    payload.apply_payload(db, [replace])
    assert feed(db) == {64496: frozenset({64498})}
    payload.apply_payload(db, [rtrkit.Aspa(2, False, 64496, ())])
    assert feed(db) == {}


def test_a_leak_is_invalid_against_a_table_fed_from_rtr() -> None:
    # 64496 attests 64497 as its only provider and 64497 attests 64499. A path that reaches 64497
    # through 64500, which 64497's ASPA does not list, is a leak.
    db = payload.PayloadDb()
    payload.apply_payload(
        db,
        [rtrkit.Aspa(2, True, 64496, (64497,)), rtrkit.Aspa(2, True, 64497, (64499,))],
    )
    table = feed(db)
    leaked = verify([(2, [64500, 64497, 64496])], table, 64500, Direction.UPSTREAM)
    assert leaked.state is AspaState.INVALID
    clean = verify([(2, [64499, 64497, 64496])], table, 64499, Direction.UPSTREAM)
    assert clean.state is AspaState.VALID
    # 64499 has no ASPA, so the hop from it to 64501 is unattested: Unknown, not Invalid.
    unknown = verify([(2, [64501, 64499, 64497, 64496])], table, 64501, Direction.UPSTREAM)
    assert unknown.state is AspaState.UNKNOWN
