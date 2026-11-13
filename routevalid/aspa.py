"""ASPA-based AS_PATH verification, pinned to draft-ietf-sidrops-aspa-verification-29.

This is an Internet-Draft, not an RFC (rfclib has no copy). The revision is pinned in
`DRAFT` and the text was read raw from
``https://www.ietf.org/archive/id/draft-ietf-sidrops-aspa-verification-29.txt`` (dated
2026-10-16, expires 2027-04-19). Section numbers below are that revision's. A later revision may
move them; re-read before relying on this after the draft changes or publishes as an RFC.

Pure functions over plain data. The ASPA table is a mapping from a Customer AS to the set of its
Provider ASes (the U-SPAS of section 5.3, built from validated ASPA data by `union_spas`).
Obtaining that table (rpkit, or the RTR ASPA PDU of rtrkit) is not this module's job.

Scope kept to the draft: the procedures apply to AFI 1 or 2 with SAFI 1 only (section 6.2,
`applicable`), on four-octet-AS speakers using the reconstructed AS_PATH (section 5, RFC 6793
section 4.2.3: the caller reconstructs it), on eBGP sessions at the edge. Choosing the algorithm
(upstream or downstream) from the peering relationship (RFC 9234 roles, section 6.3) and handling
Complex relationships (section 6.4) is the caller's decision and is passed in as `Direction`.
"""

from __future__ import annotations

import enum
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass

__all__ = [
    "DRAFT",
    "AspaResult",
    "AspaState",
    "Authorization",
    "Direction",
    "applicable",
    "authorized",
    "compress_path",
    "union_spas",
    "verify",
]

DRAFT = "draft-ietf-sidrops-aspa-verification-29"

MAX_ASN = 2**32 - 1

# Segment type codes: RFC 4271 section 4.3 (1, 2) and RFC 5065 section 3 (3, 4).
_AS_SET = 1
_AS_SEQUENCE = 2

Spas = Mapping[int, Collection[int]]
Segments = Sequence[tuple[int, Sequence[int]]]


class AspaState(enum.Enum):
    """The three outcomes of sections 5.5 and 5.6."""

    VALID = "Valid"
    INVALID = "Invalid"
    UNKNOWN = "Unknown"


class Authorization(enum.Enum):
    """The provider authorization function of section 5.3 (Figure 2)."""

    NO_ATTESTATION = "No Attestation"
    PROVIDER = "Provider+"
    NOT_PROVIDER = "Not Provider+"


class Direction(enum.Enum):
    """Which algorithm applies: section 5.5 for routes from a Customer, a Peer, or between a Route
    Server and its client; section 5.6 for routes from a Provider."""

    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"


def applicable(afi: int, safi: int) -> bool:
    """Section 6.2: the procedures MUST be applied to {AFI 1, SAFI 1} and {AFI 2, SAFI 1} and MUST
    NOT be applied to other address families by default."""
    return afi in (1, 2) and safi == 1


def _asn(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_ASN:
        raise ValueError(f"{what} must be an integer 0..{MAX_ASN}, not {value!r}")
    return value


def union_spas(records: Iterable[tuple[int, Iterable[int]]]) -> dict[int, frozenset[int]]:
    """Build the U-SPAS table from (customer, providers) pairs, one pair per valid ASPA.

    Section 5.3: with several valid ASPAs for one Customer AS the U-SPAS is the union of their
    provider sets, and "If a U-SPAS includes an AS 0 and one or more other AS numbers, then the AS 0
    is removed". An ASPA with no provider cannot exist (draft-ietf-sidrops-8210bis-29 section 5.12
    requires at least one on announcement), so an empty provider list is refused.
    """
    table: dict[int, set[int]] = {}
    for customer, providers in records:
        _asn(customer, "customer ASN")
        members = {_asn(p, "provider ASN") for p in providers}
        if not members:
            raise ValueError("an ASPA record needs at least one provider ASN")
        table.setdefault(customer, set()).update(members)
    out: dict[int, frozenset[int]] = {}
    for customer, members in table.items():
        if len(members) > 1:
            members.discard(0)
        out[customer] = frozenset(members)
    return out


def authorized(customer: int, provider: int, spas: Spas) -> Authorization:
    """Section 5.3: is ``provider`` an attested provider of ``customer``?

    "No Attestation" when the table has no entry for ``customer``; else "Provider+" when its
    entry lists ``provider``; else "Not Provider+". ``spas`` is taken as already a U-SPAS (see
    `union_spas`). An AS0 ASPA (entry ``{0}``) therefore makes every real provider "Not Provider+".
    The draft does not say what to do with AS 0 appearing in an AS_PATH; it is looked up like any
    other ASN.
    """
    entry = spas.get(customer)
    if entry is None:
        return Authorization.NO_ATTESTATION
    return Authorization.PROVIDER if provider in entry else Authorization.NOT_PROVIDER


def compress_path(asns: Iterable[int]) -> tuple[int, ...]:
    """Remove consecutive duplicate ASNs (section 5.2's COMPRESSED_AS_PATH). The input and output
    run in AS_PATH wire order: the neighbor AS first, the origin AS last."""
    out: list[int] = []
    for asn in asns:
        _asn(asn, "AS_PATH member")
        if not out or out[-1] != asn:
            out.append(asn)
    return tuple(out)


@dataclass(frozen=True, slots=True)
class AspaResult:
    """The outcome with the evidence that decided it.

    ``path`` is the COMPRESSED_AS_PATH in wire order (so ``path[-1]`` is AS(1), the origin).
    ``halted`` names the step of section 5.5 or 5.6 that decided. The four ramp bounds are None
    when a step before they are computed halted. Upstream sets both down-ramp bounds to 0.
    """

    state: AspaState
    direction: Direction
    halted: str
    path: tuple[int, ...]
    max_up_ramp: int | None = None
    min_up_ramp: int | None = None
    max_down_ramp: int | None = None
    min_down_ramp: int | None = None


def _bounds(path: tuple[int, ...], spas: Spas) -> tuple[int, int, int, int]:
    """Section 5.4. ``a[i]`` below is AS(i+1) of the draft: ``a[0]`` is the origin."""
    a = path[::-1]
    n = len(a)
    max_up = min_up = n
    for i in range(1, n):  # draft index I = i; pair (A(I), A(I+1)) = (a[i-1], a[i])
        auth = authorized(a[i - 1], a[i], spas)
        if auth is Authorization.NOT_PROVIDER:
            max_up = min(max_up, i)
        if auth is not Authorization.PROVIDER:
            min_up = min(min_up, i)
    max_down = min_down = n
    for j in range(n, 1, -1):  # draft index J; pair (A(J), A(J-1)) = (a[j-1], a[j-2])
        auth = authorized(a[j - 1], a[j - 2], spas)
        if auth is Authorization.NOT_PROVIDER:
            max_down = min(max_down, n - j + 1)
        if auth is not Authorization.PROVIDER:
            min_down = min(min_down, n - j + 1)
    return max_up, min_up, max_down, min_down


def verify(
    segments: Segments,
    spas: Spas,
    neighbor_asn: int,
    direction: Direction,
    *,
    rs_client: bool = False,
) -> AspaResult:
    """Verify an AS_PATH with ASPA (draft-ietf-sidrops-aspa-verification-29 sections 5.4 to 5.6).

    ``segments`` is the (reconstructed, section 5) AS_PATH as (segment type, ASNs) in wire order.
    ``neighbor_asn`` is the BGP neighbor's ASN. ``rs_client`` means the receiving AS is an RS-client
    and the upstream neighbor check is skipped (section 5.5 step 2; the downstream algorithm has no
    such exception).

    Steps run in the draft's order. Empty path, neighbor mismatch and any AS_SET are Invalid
    (section 5.1 also says to evaluate a route that skipped those checks as Invalid). The draft is
    silent on AS_CONFED_SEQUENCE and AS_CONFED_SET; they must not cross a confederation edge, so a
    path carrying one is reported Invalid with ``halted`` "confederation segment" instead of
    raising on hostile input. Then the ramp bounds of section 5.4 decide: upstream needs
    ``max_up_ramp == N`` for Valid or Unknown and ``min_up_ramp == N`` for Valid; downstream uses
    the sums with the down-ramp.
    """
    _asn(neighbor_asn, "neighbor_asn")
    flat: list[int] = []
    has_set = has_confed = False
    for kind, members in segments:
        if kind == _AS_SET:
            has_set = True
        elif kind != _AS_SEQUENCE:
            has_confed = True
        for asn in members:
            _asn(asn, "AS_PATH member")
        flat.extend(members)
    path = compress_path(flat)

    def halt(state: AspaState, why: str, *bounds: int) -> AspaResult:
        got = bounds if bounds else (None, None, None, None)
        return AspaResult(state, direction, why, path, *got)

    if has_confed:
        return halt(AspaState.INVALID, "confederation segment")
    if not path:
        return halt(AspaState.INVALID, "empty AS_PATH")
    if (direction is Direction.DOWNSTREAM or not rs_client) and path[0] != neighbor_asn:
        return halt(AspaState.INVALID, "most recent AS is not the neighbor AS")
    if has_set:
        return halt(AspaState.INVALID, "AS_SET in AS_PATH")
    n = len(path)
    max_up, min_up, max_down, min_down = _bounds(path, spas)
    if direction is Direction.UPSTREAM:
        if max_up < n:
            return halt(AspaState.INVALID, "max_up_ramp < N", max_up, min_up, 0, 0)
        if min_up < n:
            return halt(AspaState.UNKNOWN, "min_up_ramp < N", max_up, min_up, 0, 0)
        return halt(AspaState.VALID, "up-ramp covers the path", max_up, min_up, 0, 0)
    bounds = (max_up, min_up, max_down, min_down)
    if max_up + max_down < n:
        return halt(AspaState.INVALID, "max_up_ramp + max_down_ramp < N", *bounds)
    if min_up + min_down < n:
        return halt(AspaState.UNKNOWN, "min_up_ramp + min_down_ramp < N", *bounds)
    return halt(AspaState.VALID, "ramps cover the path", *bounds)
