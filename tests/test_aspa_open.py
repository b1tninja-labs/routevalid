"""From an OPEN to an ASPA plan (draft-ietf-sidrops-aspa-verification-29 sections 5.5, 5.6, 6.3).

Provenance: the Role capability bytes are built by hand from RFC 9234 section 4.1 and Tables 1
and 2 (read through the library), and the mismatch codes (OPEN Message Error 2, subcode 11) are
RFC 9234 section 4.2.
"""

from __future__ import annotations

import ipaddress
from typing import Any

import pytest

from routevalid.aspa import Direction, plan_from_open

message = pytest.importorskip(
    "pathattr.message", reason="pathattr is a sibling checkout: ../pathattr (see pyproject)"
)
roles = pytest.importorskip("pathattr.roles")
errors = pytest.importorskip("pathattr.errors")

PROVIDER, RS, RS_CLIENT, CUSTOMER, PEER = range(5)
UP, DOWN = Direction.UPSTREAM, Direction.DOWNSTREAM


def open_with(*caps: Any) -> Any:
    value = b"".join(bytes([c.code, len(c.value)]) + c.value for c in caps)
    parameters = (message.OptionalParameter(2, value),) if caps else ()
    return message.Open(4, 64496, 90, ipaddress.IPv4Address("192.0.2.1"), parameters)


def role_open(*values: int) -> Any:
    return open_with(*(message.Capability(9, bytes([v])) for v in values))


def test_role_from_open_to_plan() -> None:
    # (neighbour's role, our configured role) pairs of Table 2, then the plan of 5.5 and 5.6
    cases = [
        (CUSTOMER, PROVIDER, UP, False),
        (PEER, PEER, UP, False),
        (RS_CLIENT, RS, UP, False),
        (RS, RS_CLIENT, UP, True),
        (PROVIDER, CUSTOMER, DOWN, False),
    ]
    for remote, local, direction, rs_client in cases:
        plan = plan_from_open(role_open(remote), local)
        assert (plan.direction, plan.rs_client) == (direction, rs_client)


def test_a_role_mismatch_stops_before_any_plan() -> None:
    with pytest.raises(errors.BgpError) as info:
        plan_from_open(role_open(PEER), PROVIDER)
    assert (info.value.code, info.value.subcode) == (2, 11)
    with pytest.raises(errors.BgpError) as info:
        plan_from_open(role_open(PEER, CUSTOMER), None)  # differing repeats
    assert (info.value.code, info.value.subcode) == (2, 11)


def test_no_local_role_checks_nothing_and_a_missing_remote_role() -> None:
    assert plan_from_open(role_open(CUSTOMER), None).direction is UP
    # no capability from the neighbour: the draft chooses nothing, unless it is complex (6.4)
    with pytest.raises(ValueError, match="no BGP Role"):
        plan_from_open(open_with(), PROVIDER)
    assert plan_from_open(open_with(), PROVIDER, complex_relationship=True).direction is DOWN
    # strict mode (RFC 9234 section 4.2) refuses a configured role with no remote one
    with pytest.raises(errors.BgpError):
        plan_from_open(open_with(), PROVIDER, strict=True)
    assert (
        plan_from_open(role_open(CUSTOMER), PROVIDER, complex_relationship=True).direction is DOWN
    )
