"""ASPA AS_PATH verification, draft-ietf-sidrops-aspa-verification-29 sections 5.2 to 5.6.

The draft is not in rfclib; it was read raw from ietf.org/archive/id at revision -29. It carries no
test vectors in the text (its examples are an external website), so the cases below are worked by
hand from sections 5.3 to 5.6, and an independent oracle checks the ramp bounds. The oracle does
not use the bounds at all: it enumerates every way of resolving each "No Attestation" hop to
Provider+ or Not Provider+, decides each completed path by the concrete reading of section 5.2
("the combined length of the up-ramp and down-ramp is equal to or greater than N"), and says
Valid if every resolution is valid, Invalid if none is, Unknown otherwise. That is the meaning
section 5.4 gives the min and max bounds.
"""

from __future__ import annotations

import itertools
import random

import pytest

from routevalid.aspa import (
    DRAFT,
    AspaState,
    Authorization,
    Direction,
    applicable,
    authorized,
    compress_path,
    union_spas,
    verify,
)

UP = Direction.UPSTREAM
DOWN = Direction.DOWNSTREAM
V, I, U = AspaState.VALID, AspaState.INVALID, AspaState.UNKNOWN  # noqa: E741


def seq(*asns: int) -> list[tuple[int, list[int]]]:
    return [(2, list(asns))]


def test_draft_revision_is_pinned() -> None:
    assert DRAFT == "draft-ietf-sidrops-aspa-verification-29"


def test_authorized_function_has_three_outcomes() -> None:
    spas = {1: {2}}
    assert authorized(1, 2, spas) is Authorization.PROVIDER
    assert authorized(1, 3, spas) is Authorization.NOT_PROVIDER
    assert authorized(9, 2, spas) is Authorization.NO_ATTESTATION


def test_union_spas_unions_and_drops_as0_beside_others() -> None:
    table = union_spas([(1, [2]), (1, [3]), (5, [0]), (6, [0]), (6, [7])])
    assert table == {1: frozenset({2, 3}), 5: frozenset({0}), 6: frozenset({7})}
    with pytest.raises(ValueError, match="at least one"):
        union_spas([(1, [])])


def test_as0_aspa_makes_every_provider_not_provider() -> None:
    spas = union_spas([(1, [0])])
    assert authorized(1, 2, spas) is Authorization.NOT_PROVIDER
    assert verify(seq(2, 1), spas, 2, UP).state is I


def test_compress_path_removes_only_consecutive_repeats() -> None:
    assert compress_path([3, 3, 2, 2, 2, 1, 3]) == (3, 2, 1, 3)


def test_applicable_families() -> None:
    assert applicable(1, 1)
    assert applicable(2, 1)
    assert not applicable(1, 2)
    assert not applicable(25, 70)


# ---- upstream (section 5.5) --------------------------------------------------------------------


def test_upstream_valid_unknown_invalid() -> None:
    assert verify(seq(2, 1), {1: {2}}, 2, UP).state is V
    assert verify(seq(2, 1), {}, 2, UP).state is U  # No Attestation: lower bound short
    assert verify(seq(2, 1), {1: {9}}, 2, UP).state is I
    result = verify(seq(2, 1), {1: {9}}, 2, UP)
    assert (result.max_up_ramp, result.min_up_ramp, result.halted) == (1, 1, "max_up_ramp < N")


def test_upstream_single_as_and_prepends() -> None:
    assert verify(seq(7), {}, 7, UP).state is V
    # Prepends do not change the verdict (section 5.2 compresses them).
    assert verify(seq(2, 2, 2, 1, 1), {1: {2}}, 2, UP).path == (2, 1)
    assert verify(seq(2, 2, 2, 1, 1), {1: {2}}, 2, UP).state is V


def test_upstream_three_hops_with_a_gap() -> None:
    spas = {1: {2}}  # 2 has no ASPA: hop (2,3) is No Attestation
    result = verify(seq(3, 2, 1), spas, 3, UP)
    assert result.state is U
    assert (result.max_up_ramp, result.min_up_ramp) == (3, 2)
    assert verify(seq(3, 2, 1), {1: {2}, 2: {3}}, 3, UP).state is V
    assert verify(seq(3, 2, 1), {1: {2}, 2: {9}}, 3, UP).state is I


def test_upstream_halts_before_the_ramps() -> None:
    assert verify([], {}, 2, UP).halted == "empty AS_PATH"
    assert verify([], {}, 2, UP).state is I
    mismatch = verify(seq(5, 1), {1: {5}}, 2, UP)
    assert (mismatch.state, mismatch.halted) == (I, "most recent AS is not the neighbor AS")
    assert verify([(2, [2]), (2, [1])], {1: {2}}, 2, UP).state is V
    assert verify([(1, [2, 3]), (2, [1])], {1: {2}}, 2, UP).halted == "AS_SET in AS_PATH"
    assert verify([(1, [2]), (2, [1])], {1: {2}}, 2, UP).state is I
    assert verify([(3, [2]), (2, [1])], {1: {2}}, 2, UP).halted == "confederation segment"


def test_upstream_rs_client_skips_the_neighbor_check_only_upstream() -> None:
    assert verify(seq(5, 1), {1: {5}}, 2, UP, rs_client=True).state is V
    # Section 5.6 step 2 has no RS-client exception.
    assert verify(seq(5, 1), {1: {5}}, 2, DOWN, rs_client=True).halted.startswith("most recent")


# ---- downstream (section 5.6) ------------------------------------------------------------------


def test_downstream_valid_with_both_ramps() -> None:
    # 1 customer of 2; 3 customer of 2; route from 3 down to us: up 1->2, down 3->2.
    spas = {1: {2}, 3: {2}}
    result = verify(seq(3, 2, 1), spas, 3, DOWN)
    assert result.state is V


def test_downstream_leak_is_invalid() -> None:
    # 2 is a customer of 10 only, so 3 is not its provider and 4's route via 3 is a leak.
    spas = {1: {2}, 2: {10}, 3: {10}, 4: {10}}
    result = verify(seq(4, 3, 2, 1), spas, 4, DOWN)
    assert result.state is I
    assert (result.max_up_ramp, result.max_down_ramp) == (2, 1)
    assert result.halted == "max_up_ramp + max_down_ramp < N"


def test_downstream_peer_apex_is_valid_and_gaps_are_unknown() -> None:
    # Two lateral peers at the apex: 1 -> 2, and 3 -> 10; 2 and 3 are peers.
    assert verify(seq(3, 2, 1), {1: {2}, 2: {10}, 3: {10}}, 3, DOWN).state is V
    # A longer path with only the origin attested: the sum of the lower bounds falls short.
    assert verify(seq(4, 3, 2, 1), {1: {2}}, 4, DOWN).state is U


def test_downstream_empty_and_single() -> None:
    assert verify([], {}, 3, DOWN).state is I
    assert verify(seq(3), {}, 3, DOWN).state is V


# ---- the independent oracle --------------------------------------------------------------------


def concrete_valid(labels_up: list[bool], labels_down: list[bool], direction: Direction) -> bool:
    """Section 5.2 on a fully resolved path. ``labels_up[k]`` says A(k+1) -> A(k+2) is a
    customer-to-provider hop; ``labels_down[k]`` says A(k+2) -> A(k+1) is (the same index pairs
    seen from the receiving end). N is len(labels_up) + 1."""
    n = len(labels_up) + 1
    up = 1
    for ok in labels_up:
        if not ok:
            break
        up += 1
    down = 1
    for ok in reversed(labels_down):
        if not ok:
            break
        down += 1
    if direction is Direction.UPSTREAM:
        return up == n
    return up + down >= n


def oracle(path_wire: list[int], spas: dict[int, set[int]], direction: Direction) -> AspaState:
    a = [asn for i, asn in enumerate(path_wire) if i == 0 or path_wire[i - 1] != asn][::-1]
    n = len(a)
    if n == 1:
        return V
    up_status = [spas.get(a[k]) for k in range(n - 1)]
    pairs_up = [(a[k], a[k + 1]) for k in range(n - 1)]
    pairs_down = [(a[k + 1], a[k]) for k in range(n - 1)]

    def label(pair: tuple[int, int]) -> bool | None:
        entry = spas.get(pair[0])
        if entry is None:
            return None
        return pair[1] in entry

    kinds = [label(p) for p in pairs_up]
    kinds_d = [label(p) for p in pairs_down]
    unknown_slots = [("u", k) for k, x in enumerate(kinds) if x is None] + [
        ("d", k) for k, x in enumerate(kinds_d) if x is None
    ]
    del up_status
    outcomes = set()
    for choice in itertools.product([True, False], repeat=len(unknown_slots)):
        up = list(kinds)
        dn = list(kinds_d)
        for (which, k), value in zip(unknown_slots, choice, strict=True):
            (up if which == "u" else dn)[k] = value
        outcomes.add(concrete_valid([bool(x) for x in up], [bool(x) for x in dn], direction))
    if outcomes == {True}:
        return V
    if outcomes == {False}:
        return I
    return U


def test_verify_matches_enumeration_oracle() -> None:
    rng = random.Random(20261113)
    seen: dict[Direction, set[AspaState]] = {UP: set(), DOWN: set()}
    for _ in range(4000):
        pool = list(range(1, 6))
        length = rng.randint(1, 6)
        wire = [rng.choice(pool) for _ in range(length)]
        spas: dict[int, set[int]] = {}
        for customer in pool:
            if rng.random() < 0.7:
                spas[customer] = {p for p in pool if p != customer and rng.random() < 0.4} or {0}
        direction = rng.choice([UP, DOWN])
        got = verify([(2, wire)], spas, wire[0], direction)
        assert got.state is oracle(wire, spas, direction), (wire, spas, direction)
        seen[direction].add(got.state)
    assert seen[UP] == set(AspaState)
    assert seen[DOWN] == set(AspaState), "the generator must reach every state or proves little"
