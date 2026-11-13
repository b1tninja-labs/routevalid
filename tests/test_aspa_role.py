"""Choosing the algorithm from the RFC 9234 Role (draft-ietf-sidrops-aspa-verification-29).

Provenance: the case table is section 5.5 (upstream: Customer, Peer, RS from an RS-client, RS-client
from an RS; step 2 skipped for an RS-client), section 5.6 (downstream: from a Provider) and
section 6.4 (a Complex relationship MAY use downstream). Role values are RFC 9234 Table 1,
read through rfclib.
"""

from __future__ import annotations

import pytest

from routevalid.aspa import AspaState, Direction, direction_from_role, verify

PROVIDER, RS, RS_CLIENT, CUSTOMER, PEER = range(5)
UP, DOWN = Direction.UPSTREAM, Direction.DOWNSTREAM


@pytest.mark.parametrize(
    ("role", "direction", "rs_client"),
    [
        (CUSTOMER, UP, False),
        (PEER, UP, False),
        (RS_CLIENT, UP, False),  # we are the RS and received from an RS-client
        (RS, UP, True),  # we are the RS-client: the neighbour check is skipped
        (PROVIDER, DOWN, False),
    ],
    ids=["customer", "peer", "rs-client", "rs", "provider"],
)
def test_direction_from_role(role: int, direction: Direction, rs_client: bool) -> None:
    plan = direction_from_role(role)
    assert (plan.direction, plan.rs_client) == (direction, rs_client)
    assert plan.basis


@pytest.mark.parametrize("role", [PROVIDER, RS, RS_CLIENT, CUSTOMER, PEER, None])
def test_complex_relationship_applies_downstream(role: int | None) -> None:
    plan = direction_from_role(role, complex_relationship=True)
    assert (plan.direction, plan.rs_client) == (DOWN, False)


def test_no_role_and_unassigned_roles_choose_nothing() -> None:
    with pytest.raises(ValueError, match="no BGP Role"):
        direction_from_role(None)
    for bad in (5, 255, -1):
        with pytest.raises(ValueError, match="unassigned"):
            direction_from_role(bad)


def test_the_plan_drives_verify_for_a_transparent_route_server() -> None:
    # A transparent RS does not add its AS, so the first AS differs from the neighbour AS. An
    # RS-client skips step 2 and the path is judged; anyone else gets Invalid at step 2.
    spas = {64496: frozenset({64497})}
    path = [(2, [64497, 64496])]
    plan = direction_from_role(RS)
    got = verify(path, spas, 64999, plan.direction, rs_client=plan.rs_client)
    assert got.state is AspaState.VALID
    other = direction_from_role(PEER)
    refused = verify(path, spas, 64999, other.direction, rs_client=other.rs_client)
    assert (refused.state, refused.halted) == (
        AspaState.INVALID,
        "most recent AS is not the neighbor AS",
    )


def test_downstream_for_a_provider_accepts_a_path_with_a_down_ramp_upstream_refuses() -> None:
    # Wire order, neighbour first: 4 3 2 1. The origin 1 reaches its provider 2, then 3, and 3
    # hands the route down to its customer 4, which is our Provider: up-ramp 3, down-ramp 1, N = 4.
    # 3 attests only 5, so 4 is Not Provider+ of 3 seen upward and the upstream algorithm refuses.
    spas = {1: frozenset({2}), 2: frozenset({3}), 3: frozenset({5}), 4: frozenset({3})}
    path = [(2, [4, 3, 2, 1])]
    assert verify(path, spas, 4, DOWN).state is AspaState.VALID
    assert verify(path, spas, 4, UP).state is AspaState.INVALID
    assert direction_from_role(PROVIDER).direction is DOWN
