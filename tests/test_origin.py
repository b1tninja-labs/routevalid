"""RFC 6811 section 2: the validation state, plus the origin-AS rule and the IRR evidence split.

RFC 6811 publishes no test vectors, so the truth table here is derived from the section 2
definitions (Covered, Matched, NotFound/Valid/Invalid, and the NONE and AS0 observations in the
paragraph after them) and cross-checked by an independent oracle that works on bit strings and
never touches ``ipaddress`` network arithmetic. RFC 6811 and RFC 8481 have no errata (rfclib,
2026-11-13). Segment type codes come from RFC 4271 section 4.3 and RFC 5065 section 3.
"""

from __future__ import annotations

import ipaddress
import random
from typing import Any

import pytest

from routevalid.origin import (
    IrrRoute,
    IrrStatus,
    OriginVerdict,
    RovResult,
    RovState,
    SegmentType,
    Vrp,
    check_origin,
    irr_evidence,
    route_origin_asn,
    rov_state,
)

V = RovState


def net(text: str) -> Any:
    return ipaddress.ip_network(text)


def vrp(prefix: str, max_length: int, asn: int) -> Vrp:
    return Vrp(net(prefix), max_length, asn)


# ---- the three states ------------------------------------------------------------------------


def test_rov_valid_exact_match() -> None:
    v = vrp("192.0.2.0/24", 24, 64496)
    result = rov_state(net("192.0.2.0/24"), 64496, [v])
    assert result.state is V.VALID
    assert result.matched == (v,)
    assert result.covering == (v,)


def test_rov_valid_within_maxlength() -> None:
    v = vrp("192.0.2.0/24", 26, 64496)
    assert rov_state(net("192.0.2.128/25"), 64496, [v]).state is V.VALID
    assert rov_state(net("192.0.2.192/26"), 64496, [v]).state is V.VALID


def test_rov_invalid_too_specific() -> None:
    """Route longer than the VRP's max length: covered, not matched."""
    v = vrp("192.0.2.0/24", 26, 64496)
    result = rov_state(net("192.0.2.0/27"), 64496, [v])
    assert result.state is V.INVALID
    assert result.matched == ()
    assert result.unmatched == (v,)


def test_rov_invalid_wrong_origin() -> None:
    v = vrp("192.0.2.0/24", 24, 64496)
    assert rov_state(net("192.0.2.0/24"), 64497, [v]).state is V.INVALID


def test_rov_not_found_no_cover() -> None:
    result = rov_state(net("198.51.100.0/24"), 64496, [vrp("192.0.2.0/24", 24, 64496)])
    assert result.state is V.NOT_FOUND
    assert result.covering == ()
    assert rov_state(net("198.51.100.0/24"), 64496, []).state is V.NOT_FOUND


def test_a_less_specific_route_is_not_covered_by_a_more_specific_vrp() -> None:
    """Covered needs the VRP prefix length <= the route's: the route /16 is not under VRP /24."""
    assert (
        rov_state(net("192.0.0.0/16"), 64496, [vrp("192.0.2.0/24", 24, 64496)]).state is V.NOT_FOUND
    )


def test_rov_none_origin_is_invalid_when_covered_else_not_found() -> None:
    v = vrp("192.0.2.0/24", 24, 64496)
    assert rov_state(net("192.0.2.0/24"), None, [v]).state is V.INVALID
    assert rov_state(net("203.0.113.0/24"), None, [v]).state is V.NOT_FOUND


def test_rov_as0_vrp_never_matches() -> None:
    """RFC 6811 section 2: no Route can be Matched by a VRP whose ASN is zero."""
    v = vrp("192.0.2.0/24", 24, 0)
    assert rov_state(net("192.0.2.0/24"), 0, [v]).state is V.INVALID
    assert rov_state(net("192.0.2.0/24"), 64496, [v]).state is V.INVALID


def test_route_origin_zero_is_never_valid_even_with_an_as0_vrp_and_a_real_one() -> None:
    assert rov_state(net("192.0.2.0/24"), 0, [vrp("192.0.2.0/24", 24, 64496)]).state is V.INVALID


def test_one_match_among_many_is_valid_regardless_of_order() -> None:
    vrps = [
        vrp("192.0.0.0/8", 8, 1),
        vrp("192.0.2.0/24", 24, 2),
        vrp("192.0.2.0/24", 25, 3),
        vrp("192.0.0.0/16", 24, 64496),
        vrp("0.0.0.0/0", 0, 64496),
    ]
    expected = rov_state(net("192.0.2.0/24"), 64496, vrps)
    assert expected.state is V.VALID
    assert expected.matched == (vrp("192.0.0.0/16", 24, 64496),)
    rng = random.Random(6811)
    for _ in range(25):
        rng.shuffle(vrps)
        assert rov_state(net("192.0.2.0/24"), 64496, vrps) == expected


def test_family_isolation() -> None:
    """IPv4 and IPv6 never cover each other, including the all-zero default prefixes."""
    v6_default = vrp("::/0", 128, 64496)
    v4_default = vrp("0.0.0.0/0", 32, 64496)
    assert rov_state(net("192.0.2.0/24"), 64496, [v6_default]).state is V.NOT_FOUND
    assert rov_state(net("2001:db8::/32"), 64496, [v4_default]).state is V.NOT_FOUND
    assert rov_state(net("192.0.2.0/24"), 64496, [v4_default, v6_default]).state is V.VALID


def test_default_route_vrp_covers_everything() -> None:
    v = vrp("0.0.0.0/0", 32, 64496)
    assert rov_state(net("203.0.113.5/32"), 64496, [v]).state is V.VALID
    assert rov_state(net("0.0.0.0/0"), 64496, [v]).state is V.VALID
    assert rov_state(net("203.0.113.0/24"), 64497, [v]).state is V.INVALID


def test_ipv6_matching() -> None:
    v = vrp("2001:db8::/32", 48, 64496)
    assert rov_state(net("2001:db8:1::/48"), 64496, [v]).state is V.VALID
    assert rov_state(net("2001:db8:1::/49"), 64496, [v]).state is V.INVALID
    assert rov_state(net("2001:db9::/32"), 64496, [v]).state is V.NOT_FOUND


def test_duplicate_vrps_collapse_in_the_evidence() -> None:
    v = vrp("192.0.2.0/24", 24, 1)
    assert rov_state(net("192.0.2.0/24"), 1, [v, v, v]).matched == (v,)


def test_vrps_may_be_a_generator_consumed_once() -> None:
    source = (v for v in [vrp("192.0.2.0/24", 24, 1), vrp("192.0.0.0/16", 16, 2)])
    result = rov_state(net("192.0.2.0/24"), 1, source)
    assert result.state is V.VALID
    assert len(result.covering) == 2


# ---- independent oracle ----------------------------------------------------------------------


def bits(network: Any) -> str:
    width = network.max_prefixlen
    return format(int(network.network_address), f"0{width}b")[: network.prefixlen]


def oracle(route: Any, origin: int | None, vrps: list[Vrp]) -> V:
    """RFC 6811 section 2 written over bit strings, sharing no code with the implementation."""
    covered = [
        x
        for x in vrps
        if x.prefix.version == route.version and bits(route).startswith(bits(x.prefix))
    ]
    if not covered:
        return V.NOT_FOUND
    for x in covered:
        if (
            route.prefixlen <= x.max_length
            and origin is not None
            and origin == x.asn
            and x.asn != 0
        ):
            return V.VALID
    return V.INVALID


def random_network(rng: random.Random) -> Any:
    if rng.random() < 0.7:
        length = rng.randint(0, 12)
        return ipaddress.ip_network((rng.getrandbits(32) >> (32 - length) << (32 - length), length))
    length = rng.randint(0, 12)
    return ipaddress.ip_network((rng.getrandbits(128) >> (128 - length) << (128 - length), length))


def test_rov_matches_bruteforce_oracle() -> None:
    rng = random.Random(20261113)
    states = set()
    for _ in range(3000):
        vrps = []
        for _ in range(rng.randint(0, 6)):
            prefix = random_network(rng)
            vrps.append(
                Vrp(
                    prefix,
                    rng.randint(prefix.prefixlen, min(prefix.max_prefixlen, 14)),
                    rng.choice([0, 1, 2, 3]),
                )
            )
        route = random_network(rng)
        origin = rng.choice([None, 0, 1, 2, 3])
        got = rov_state(route, origin, vrps)
        assert got.state is oracle(route, origin, vrps)
        states.add(got.state)
    assert states == set(V), "the generator must reach all three states or the check proves little"


# ---- hostile input ---------------------------------------------------------------------------


@pytest.mark.parametrize(("length", "asn"), [(23, 1), (33, 1), (-1, 1), (24, -1), (24, 2**32)])
def test_vrp_with_impossible_fields_is_rejected(length: int, asn: int) -> None:
    with pytest.raises(ValueError, match=r"max length|ASN|must be"):
        Vrp(net("192.0.2.0/24"), length, asn)


def test_vrp_rejects_bool_and_non_network() -> None:
    with pytest.raises(TypeError):
        Vrp(net("192.0.2.0/24"), True, 1)
    with pytest.raises(TypeError):
        Vrp("192.0.2.0/24", 24, 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=r"Vrp\.asn"):
        Vrp(net("192.0.2.0/24"), 24, True)


def test_host_bits_set_route_prefix_cannot_be_built() -> None:
    """Decision: the API takes ipaddress networks, and a strict network refuses host bits."""
    with pytest.raises(ValueError, match="host bits"):
        ipaddress.ip_network("192.0.2.1/24")
    with pytest.raises(TypeError):
        rov_state("192.0.2.1/24", 1, [])  # type: ignore[arg-type]


@pytest.mark.parametrize("asn", [-1, 2**32, True, "1", 1.0])
def test_bad_route_origin_is_refused_not_treated_as_none(asn: Any) -> None:
    with pytest.raises(ValueError, match="origin_asn"):
        rov_state(net("192.0.2.0/24"), asn, [])


def test_result_cannot_disagree_with_its_evidence() -> None:
    v = vrp("192.0.2.0/24", 24, 1)
    with pytest.raises(ValueError, match="disagrees"):
        RovResult(V.VALID, (), (v,))
    with pytest.raises(ValueError, match="disagrees"):
        RovResult(V.NOT_FOUND, (), (v,))
    with pytest.raises(ValueError, match="disagrees"):
        RovResult(V.INVALID, (v,), (v,))


# ---- route origin ASN ------------------------------------------------------------------------

SEQ, SET, CSEQ, CSET = (
    SegmentType.AS_SEQUENCE,
    SegmentType.AS_SET,
    SegmentType.AS_CONFED_SEQUENCE,
    SegmentType.AS_CONFED_SET,
)


def test_segment_type_codes_are_the_rfc_codes() -> None:
    assert [int(t) for t in (SET, SEQ, CSEQ, CSET)] == [1, 2, 3, 4]


def test_origin_rightmost_of_final_sequence() -> None:
    assert route_origin_asn([(SEQ, [64500, 64501, 64496])], 65000) == 64496
    assert route_origin_asn([(SET, [1, 2]), (SEQ, [3, 4])], 65000) == 4


def test_origin_empty_path_is_local() -> None:
    assert route_origin_asn([], 65000) == 65000


def test_origin_final_as_set_is_none() -> None:
    assert route_origin_asn([(SEQ, [1, 2]), (SET, [3, 4])], 65000) is None


def test_origin_confed_tail_is_local() -> None:
    assert route_origin_asn([(SEQ, [1, 2]), (CSEQ, [65001])], 65000) == 65000
    assert route_origin_asn([(SEQ, [1]), (CSET, [65001, 65002])], 65000) == 65000


def test_origin_final_segment_empty_sequence_is_none() -> None:
    """Design decision: no rightmost AS exists, so NONE (never Valid), not the earlier segment."""
    assert route_origin_asn([(SEQ, [1, 2]), (SEQ, [])], 65000) is None


def test_origin_unknown_segment_type_is_none_not_crash() -> None:
    assert route_origin_asn([(SEQ, [1]), (9, [2])], 65000) is None
    assert route_origin_asn([(0, [2])], 65000) is None


@pytest.mark.parametrize("bad", [-1, 2**32, True])
def test_origin_asn_out_of_32_bit_range_rejected(bad: Any) -> None:
    with pytest.raises(ValueError, match="AS_PATH member"):
        route_origin_asn([(SEQ, [1, bad])], 65000)
    with pytest.raises(ValueError, match="local_asn"):
        route_origin_asn([], bad)


def test_origin_feeds_rov_state_end_to_end() -> None:
    v = vrp("192.0.2.0/24", 24, 64496)
    origin = route_origin_asn([(SEQ, [64500, 64496])], 65000)
    assert rov_state(net("192.0.2.0/24"), origin, [v]).state is V.VALID
    via_set = route_origin_asn([(SEQ, [64500]), (SET, [64496, 64497])], 65000)
    assert rov_state(net("192.0.2.0/24"), via_set, [v]).state is V.INVALID


# ---- IRR evidence is a different type, per source --------------------------------------------


def test_irr_evidence_is_never_an_rov_state() -> None:
    ev = irr_evidence(net("192.0.2.0/24"), 1, [IrrRoute("RIPE", net("192.0.2.0/24"), 1)])
    assert not isinstance(ev.by_source[0].status, RovState)
    assert IrrStatus.REGISTERED.value != RovState.VALID.value


def test_irr_evidence_per_source_statuses() -> None:
    prefix = net("192.0.2.0/24")
    routes = [
        IrrRoute("RIPE", prefix, 64496),
        IrrRoute("RADB", prefix, 64497),  # RADB only knows a different origin
        IrrRoute("ARIN", net("192.0.2.0/25"), 64496),  # a more specific object is not evidence
        IrrRoute("ALTDB", net("192.0.0.0/16"), 64496),  # nor is a less specific one
    ]
    ev = irr_evidence(prefix, 64496, routes, sources=["LEVEL3"])
    assert [(s.source, s.status) for s in ev.by_source] == [
        ("ALTDB", IrrStatus.ABSENT),
        ("ARIN", IrrStatus.ABSENT),
        ("LEVEL3", IrrStatus.ABSENT),
        ("RADB", IrrStatus.CONFLICTING),
        ("RIPE", IrrStatus.REGISTERED),
    ]
    assert ev.status_of("RADB") is IrrStatus.CONFLICTING
    assert ev.status_of("NEVERASKED") is None
    radb = next(s for s in ev.by_source if s.source == "RADB")
    assert radb.conflicting == (IrrRoute("RADB", prefix, 64497),)


def test_irr_route_without_origin_is_never_registered() -> None:
    ev = irr_evidence(net("192.0.2.0/24"), None, [IrrRoute("RIPE", net("192.0.2.0/24"), 1)])
    assert ev.by_source[0].status is IrrStatus.CONFLICTING


def test_irr_route_validation() -> None:
    with pytest.raises(ValueError, match="source"):
        IrrRoute("", net("192.0.2.0/24"), 1)
    with pytest.raises(ValueError, match="origin_asn"):
        IrrRoute("RIPE", net("192.0.2.0/24"), -1)


# ---- check_origin keeps the two apart --------------------------------------------------------


def test_check_origin_pairs_without_merging() -> None:
    prefix = net("192.0.2.0/24")
    verdict = check_origin(prefix, 64496, [], [IrrRoute("RIPE", prefix, 64496)])
    assert isinstance(verdict, OriginVerdict)
    # IRR agrees with the route, yet the RPKI state stays what RFC 6811 says: no VRP, NotFound.
    assert verdict.rov.state is V.NOT_FOUND
    assert verdict.irr.status_of("RIPE") is IrrStatus.REGISTERED


def test_check_origin_irr_cannot_rescue_an_invalid_route() -> None:
    prefix = net("192.0.2.0/24")
    verdict = check_origin(
        prefix, 64499, [vrp("192.0.2.0/24", 24, 64496)], [IrrRoute("RIPE", prefix, 64499)]
    )
    assert verdict.rov.state is V.INVALID
    assert verdict.irr.status_of("RIPE") is IrrStatus.REGISTERED


def test_check_origin_reports_the_as_set_finding_beside_the_rfc_6811_state() -> None:
    # RFC 6811 section 2 only makes the origin NONE for a final AS_SET, so an AS_SET in the middle
    # still reaches Valid in rov_state. RFC 9774 section 4 says such a route is never Valid.
    # check_origin reports both and invents no replacement state (PORTFOLIO.md sec. 9 item 15).
    prefix = net("192.0.2.0/24")
    roas = [vrp("192.0.2.0/24", 24, 64496)]
    middle_set = [(2, [64510]), (1, [64511, 64512]), (2, [64496])]
    verdict = check_origin(prefix, 64496, roas, [], segments=middle_set)
    assert verdict.rov.state is V.VALID  # the RFC 6811 state, untouched
    assert verdict.as_set is not None
    assert verdict.as_set.has_as_set
    assert not verdict.as_set.rov_may_be_valid
    assert verdict.as_set.treat_as_withdraw
    # no path given: no finding; a path with no set: a finding that raises no flag
    assert check_origin(prefix, 64496, roas, []).as_set is None
    clean = check_origin(prefix, 64496, roas, [], segments=[(2, [64496])]).as_set
    assert clean is not None
    assert clean.rov_may_be_valid
    assert not clean.treat_as_withdraw
    # the state is the same with or without the finding
    assert check_origin(prefix, 64496, roas, [], segments=middle_set).rov == rov_state(
        prefix, 64496, roas
    )
