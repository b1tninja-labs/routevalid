"""RFC 8893 effective origin and RFC 9774 AS_SET policy.

RFC 8893 and RFC 9774 publish no test vectors, so the cases are derived from the text read through
rfclib (2026-11-13, no errata on either): RFC 8893 sections 1 and 3 define the effective origin as
the Route Origin ASN of the UPDATE to be sent; RFC 4271 section 5.1.2 (b) and RFC 5065 section 4.1
(c) say how the path changes on the way out; RFC 6996 section 5 gives the Private Use ranges;
RFC 9774 sections 3 and 4 give the AS_SET consequences.
"""

from __future__ import annotations

import ipaddress

import pytest

from routevalid.origin import (
    PrivateRemoval,
    RovState,
    SegmentType,
    Vrp,
    as_set_policy,
    effective_origin,
    effective_path,
    is_private_asn,
    rov_state,
)

SEQ = SegmentType.AS_SEQUENCE
SET = SegmentType.AS_SET
CSEQ = SegmentType.AS_CONFED_SEQUENCE
CSET = SegmentType.AS_CONFED_SET


def test_private_ranges_are_rfc_6996_and_exclude_the_rfc_7300_last_asns() -> None:
    assert not is_private_asn(64511)
    assert is_private_asn(64512)
    assert is_private_asn(65534)
    assert not is_private_asn(65535)
    assert not is_private_asn(4199999999)
    assert is_private_asn(4200000000)
    assert is_private_asn(4294967294)
    assert not is_private_asn(4294967295)


def test_effective_origin() -> None:
    # An unchanged path keeps its origin; the local AS is prepended and does not move it.
    assert effective_origin([(SEQ, [64496, 64497])], 64500) == 64497
    # A route with no AS_PATH (locally originated) gets the local AS as its origin.
    assert effective_origin([], 64500) == 64500
    # Removal of private ASes changes the origin: the case RFC 8893 section 1 names.
    private = [(SEQ, [64496, 65001])]
    assert effective_origin(private, 64500) == 65001
    assert effective_origin(private, 64500, remove_private=PrivateRemoval.ALL) == 64496
    # All-private path with ALL removal leaves only the local AS, which becomes the origin.
    assert effective_origin([(SEQ, [65001, 65002])], 64500, remove_private=PrivateRemoval.ALL) == (
        64500
    )
    # Mixed path under ONLY_IF_ALL_PRIVATE (RFC 6996 section 4 notes implementations differ): untouched.
    only = PrivateRemoval.ONLY_IF_ALL_PRIVATE
    assert effective_origin(private, 64500, remove_private=only) == 65001
    assert effective_origin([(SEQ, [65001, 65002])], 64500, remove_private=only) == 64500


def test_effective_origin_decides_the_rov_state() -> None:
    vrps = [Vrp(ipaddress.ip_network("192.0.2.0/24"), 24, 64496)]
    prefix = ipaddress.ip_network("192.0.2.0/24")
    path = [(SEQ, [64496, 65001])]
    # As received the origin is 65001 (Invalid); as it will be announced it is 64496 (Valid).
    received = effective_origin(path, 64500, prepend=0)
    sent = effective_origin(path, 64500, remove_private=PrivateRemoval.ALL)
    assert rov_state(prefix, received, vrps).state is RovState.INVALID
    assert rov_state(prefix, sent, vrps).state is RovState.VALID


def test_effective_origin_confederation_segments_are_stripped_for_external_peers() -> None:
    # RFC 5065 section 4.1 (c)(1): confederation segments MUST be removed toward an outside peer.
    path = [(CSEQ, [65010, 65011]), (SEQ, [64496])]
    assert effective_path(path, 64500) == ((2, (64500, 64496)),)
    # Toward a member AS they are kept; a final confed segment then reads as the local AS.
    kept = effective_path([(CSEQ, [65010])], 64500, strip_confed=False, prepend=0)
    assert kept == ((3, (65010,)),)
    assert effective_origin([(CSEQ, [65010])], 64500, strip_confed=False, prepend=0) == 64500


def test_effective_path_prepend_follows_rfc_4271_5_1_2() -> None:
    assert effective_path([(SEQ, [64496])], 64500) == ((2, (64500, 64496)),)
    assert effective_path([(SET, [64496, 64497])], 64500) == ((2, (64500,)), (1, (64496, 64497)))
    assert effective_path([], 64500, prepend=3) == ((2, (64500, 64500, 64500)),)
    assert effective_path([(SEQ, [64496])], 64500, prepend=0) == ((2, (64496,)),)


def test_effective_origin_final_set_is_none() -> None:
    assert effective_origin([(SEQ, [64496]), (SET, [64497, 64498])], 64500) is None


@pytest.mark.parametrize("bad", [-1, 2**32, True])
def test_effective_origin_refuses_bad_asn(bad: int) -> None:
    with pytest.raises(ValueError, match="must be"):
        effective_origin([(SEQ, [bad])], 64500)
    with pytest.raises(ValueError, match="local_asn"):
        effective_origin([], bad)


@pytest.mark.parametrize("bad", [-1, True, 1.5])
def test_effective_path_refuses_bad_prepend(bad: object) -> None:
    with pytest.raises(ValueError, match="prepend"):
        effective_path([], 64500, prepend=bad)  # type: ignore[arg-type]


# ---- RFC 9774 -----------------------------------------------------------------------------


def test_as_set_policy() -> None:
    plain = as_set_policy([(SEQ, [64496, 64497])])
    assert not plain.has_as_set
    assert not plain.treat_as_withdraw
    assert plain.rov_may_be_valid
    assert not plain.aspa_invalid

    # Section 4: an AS_SET anywhere (not only last) forbids Valid in ROV and forces ASPA Invalid.
    middle = as_set_policy([(SEQ, [64496]), (SET, [1, 2]), (SEQ, [64497])])
    assert middle.has_as_set
    assert middle.treat_as_withdraw
    assert not middle.rov_may_be_valid
    assert middle.aspa_invalid

    # Section 3 names AS_CONFED_SET for treat-as-withdraw; section 4 does not name it.
    confed = as_set_policy([(CSET, [65010])])
    assert confed.has_confed_set
    assert confed.treat_as_withdraw
    assert confed.rov_may_be_valid
    assert not confed.aspa_invalid


def test_as_set_policy_configured_to_accept_never_makes_the_route_valid() -> None:
    verdict = as_set_policy([(SET, [1, 2])], configured_to_accept=True)
    assert not verdict.treat_as_withdraw
    assert not verdict.rov_may_be_valid
    assert verdict.aspa_invalid


def test_as_set_policy_refuses_bad_input() -> None:
    with pytest.raises(ValueError, match="AS_PATH member"):
        as_set_policy([(SEQ, [2**32])])
    with pytest.raises(TypeError):
        as_set_policy([(True, [1])])
