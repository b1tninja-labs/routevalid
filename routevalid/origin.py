"""origin checks: the RFC 6811 validation state, and IRR evidence kept apart from it.

Two different kinds of statement live here and they are never merged into one verdict:

* `rov_state` is **RFC 6811 route origin validation**, a pure function of a route prefix, a route
  origin AS and a set of VRPs. Its answer is fully determined by that data (RFC 6811 section 2, last
  paragraph: no order of VRPs is mandated "however, the validation state output is fully determined")
  and it carries the VRPs that decided it.
* `irr_evidence` is **advisory** evidence from Internet Routing Registry route objects (RFC 2622
  section 4: the route and origin attribute pair is the class key). Databases disagree with one
  another and with the RPKI, and a registry object is not an authorisation, so the evidence is
  reported per source and is never an RFC 6811 state.

`check_origin` returns both in one `OriginVerdict` with a field each. `score.confidence` is where
they are weighed; nothing here decides which one wins.

Scope of what was read, so a citation is not mistaken for more: RFC 6811 section 2 and 2.1 in full
(no errata, rfclib 2026-11-13), RFC 8481 section 4 (every route is evaluated, and a redistributed
route with no AS_PATH uses the router's own AS), RFC 5065 section 3 and RFC 4271 section 4.3 for the
segment type codes, RFC 2622 section 4. RFC 8893 (the *effective origin* for export-side
validation) and RFC 9774 (AS_SET deprecation; it updates RFC 4271 and RFC 5065) are listed in
ROADMAP.md as rows and are not implemented here. RFC 4012 adds the ``route6`` class for IPv6; it was
not read, and `irr_evidence` treats an IPv6 route object with the same key shape.
"""

from __future__ import annotations

import enum
import ipaddress
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

__all__ = [
    "MAX_ASN",
    "IrrEvidence",
    "IrrRoute",
    "IrrSourceEvidence",
    "IrrStatus",
    "OriginVerdict",
    "RovResult",
    "RovState",
    "SegmentType",
    "Vrp",
    "check_origin",
    "irr_evidence",
    "route_origin_asn",
    "rov_state",
]

MAX_ASN = 2**32 - 1

Network = ipaddress.IPv4Network | ipaddress.IPv6Network


def _check_asn(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_ASN:
        raise ValueError(f"{what} must be an integer 0..{MAX_ASN}, not {value!r}")
    return value


def _check_network(value: object, what: str) -> Network:
    if not isinstance(value, ipaddress.IPv4Network | ipaddress.IPv6Network):
        raise TypeError(f"{what} must be an ipaddress network, not {type(value).__name__}")
    return value


class RovState(enum.Enum):
    """The three RFC 6811 section 2 validation states."""

    VALID = "Valid"
    INVALID = "Invalid"
    NOT_FOUND = "NotFound"


@dataclass(frozen=True, slots=True)
class Vrp:
    """A Validated ROA Payload (RFC 6811 section 2): prefix, maximum length, origin AS.

    Plain data on purpose. rpkit has its own ``Vrp`` with the same three fields, and neither
    project imports the other (rpkit is a dependency of routevalid, so the other direction would be
    a cycle). An ASN of 0 is a legal VRP that can never match a route (RFC 6811 section 2).
    """

    prefix: Network
    max_length: int
    asn: int

    def __post_init__(self) -> None:
        _check_network(self.prefix, "Vrp.prefix")
        if isinstance(self.max_length, bool) or not isinstance(self.max_length, int):
            raise TypeError("Vrp.max_length must be an int")
        if not self.prefix.prefixlen <= self.max_length <= self.prefix.max_prefixlen:
            raise ValueError(
                f"max length {self.max_length} is outside "
                f"{self.prefix.prefixlen}..{self.prefix.max_prefixlen} for {self.prefix}"
            )
        _check_asn(self.asn, "Vrp.asn")

    def sort_key(self) -> tuple[int, int, int, int, int]:
        """Total order across both families, so evidence tuples have one deterministic order."""
        return (
            self.prefix.version,
            int(self.prefix.network_address),
            self.prefix.prefixlen,
            self.max_length,
            self.asn,
        )


@dataclass(frozen=True, slots=True)
class RovResult:
    """An RFC 6811 state with the evidence that decided it.

    ``covering`` holds every distinct VRP that Covers the route prefix and ``matched`` the subset
    that also Matches it, both in `Vrp.sort_key` order. So ``Valid`` means ``matched`` is non-empty,
    ``Invalid`` means ``covering`` is non-empty and ``matched`` empty, and ``NotFound`` means
    ``covering`` is empty. A result whose state and evidence disagree cannot be built.
    """

    state: RovState
    matched: tuple[Vrp, ...]
    covering: tuple[Vrp, ...]

    def __post_init__(self) -> None:
        expected = (
            RovState.VALID
            if self.matched
            else RovState.INVALID
            if self.covering
            else RovState.NOT_FOUND
        )
        if self.state is not expected or not set(self.matched) <= set(self.covering):
            raise ValueError("RovResult state disagrees with its evidence")

    @property
    def unmatched(self) -> tuple[Vrp, ...]:
        """The covering VRPs that did not match: the reason an Invalid route is Invalid."""
        won = set(self.matched)
        return tuple(v for v in self.covering if v not in won)


def rov_state(route_prefix: Network, origin_asn: int | None, vrps: Iterable[Vrp]) -> RovResult:
    """Classify a route as RFC 6811 section 2 defines Valid, Invalid and NotFound.

    ``route_prefix`` is the Route Prefix and ``origin_asn`` the Route Origin ASN, where ``None`` is
    the RFC's distinguished value "NONE" (see `route_origin_asn`). A VRP Covers the route when its
    prefix length is no longer than the route's and the first VRP-length bits are identical; it
    Matches when it Covers, the route's length is within the VRP's maximum length, and the origin
    ASNs are equal. A route with origin "NONE" or ASN 0 is never Matched, and a VRP with ASN 0
    never Matches (section 2, "no VRP can have the value NONE ... no Route can be Matched by a VRP
    whose ASN is zero"). IPv4 and IPv6 never Cover each other.

    The state is independent of VRP order, and ``vrps`` is read once, so a generator is fine. This
    is a linear reference implementation; an indexed one belongs where a whole RIB is joined.

    Raises:
        TypeError: ``route_prefix`` is not an ``ipaddress`` network, so it cannot carry host bits.
        ValueError: ``origin_asn`` is outside 0..4294967295.
    """
    _check_network(route_prefix, "route_prefix")
    if origin_asn is not None:
        _check_asn(origin_asn, "origin_asn")
    length = route_prefix.prefixlen
    covering: set[Vrp] = set()
    matched: set[Vrp] = set()
    for vrp in vrps:
        if vrp.prefix.version != route_prefix.version or vrp.prefix.prefixlen > length:
            continue
        if not route_prefix.subnet_of(vrp.prefix):  # type: ignore[arg-type]
            continue
        covering.add(vrp)
        if (
            length <= vrp.max_length
            and origin_asn is not None
            and origin_asn != 0
            and vrp.asn == origin_asn
        ):
            matched.add(vrp)
    state = RovState.VALID if matched else RovState.INVALID if covering else RovState.NOT_FOUND
    return RovResult(
        state,
        tuple(sorted(matched, key=Vrp.sort_key)),
        tuple(sorted(covering, key=Vrp.sort_key)),
    )


class SegmentType(enum.IntEnum):
    """AS_PATH segment types: RFC 4271 section 4.3 (1, 2) and RFC 5065 section 3 (3, 4)."""

    AS_SET = 1
    AS_SEQUENCE = 2
    AS_CONFED_SEQUENCE = 3
    AS_CONFED_SET = 4


def route_origin_asn(segments: Sequence[tuple[int, Sequence[int]]], local_asn: int) -> int | None:
    """The Route Origin ASN of RFC 6811 section 2, or ``None`` for its value "NONE".

    The rightmost AS of the final segment when that segment is AS_SEQUENCE; ``local_asn`` (the BGP
    speaker's own AS) when the final segment is AS_CONFED_SEQUENCE or AS_CONFED_SET or the path is
    empty; "NONE" for any other final segment type. For a route redistributed into BGP there is no
    AS_PATH, and RFC 8481 section 4 says to use the AS of the router's BGP configuration, which is
    the empty-path case here.

    A final AS_SEQUENCE with no members has no rightmost AS, so it returns ``None``: the answer that
    can never yield Valid. A well-formed path never has one, and refusing it earlier belongs to the
    attribute parser (pathattr). Segment types are ints so an unassigned code returns ``None`` rather
    than raising: RFC 6811 says "any other type".

    Raises:
        ValueError: an ASN, or ``local_asn``, is outside 0..4294967295.
    """
    _check_asn(local_asn, "local_asn")
    for _, members in segments:
        for asn in members:
            _check_asn(asn, "AS_PATH member")
    if not segments:
        return local_asn
    kind, members = segments[-1]
    if kind == SegmentType.AS_SEQUENCE:
        return members[-1] if members else None
    if kind in (SegmentType.AS_CONFED_SEQUENCE, SegmentType.AS_CONFED_SET):
        return local_asn
    return None


class IrrStatus(enum.Enum):
    """What one registry says about an exact (prefix, origin) pair. Advisory, never RFC 6811."""

    REGISTERED = "registered"  # a route object with this prefix and this origin
    CONFLICTING = "conflicting"  # route objects for this prefix, none with this origin
    ABSENT = "absent"  # the source has no route object for this exact prefix


@dataclass(frozen=True, slots=True)
class IrrRoute:
    """One IRR route object: its source database, prefix and origin (RFC 2622 section 4 key)."""

    source: str
    prefix: Network
    origin_asn: int

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("an IRR route needs a source database name")
        _check_network(self.prefix, "IrrRoute.prefix")
        _check_asn(self.origin_asn, "IrrRoute.origin_asn")


@dataclass(frozen=True, slots=True)
class IrrSourceEvidence:
    """One source's view: its status and the route objects behind it."""

    source: str
    status: IrrStatus
    matching: tuple[IrrRoute, ...]
    conflicting: tuple[IrrRoute, ...]


@dataclass(frozen=True, slots=True)
class IrrEvidence:
    """IRR evidence per source, sorted by source name. Sources disagree, so none is collapsed.

    A source that was not asked is not in ``by_source``; asking it and finding nothing is
    ``ABSENT``. The difference is the point of passing ``sources`` to `irr_evidence`.
    """

    by_source: tuple[IrrSourceEvidence, ...]

    def status_of(self, source: str) -> IrrStatus | None:
        """The named source's status, or None when it was never consulted."""
        for item in self.by_source:
            if item.source == source:
                return item.status
        return None


def irr_evidence(
    prefix: Network,
    origin_asn: int | None,
    routes: Iterable[IrrRoute],
    sources: Iterable[str] = (),
) -> IrrEvidence:
    """Summarise route objects for one exact prefix and origin, per source database.

    This is advisory design, not a standard's algorithm: only objects whose prefix is exactly
    ``prefix`` count (a less specific registration is not evidence for this route), and a route with
    no origin (``None``) can be ``CONFLICTING`` or ``ABSENT`` but never ``REGISTERED``.
    ``sources`` names databases that were consulted and may have returned nothing; each appears as
    ``ABSENT``, so silence and "not asked" stay different.

    Raises:
        TypeError: ``prefix`` is not an ``ipaddress`` network.
        ValueError: ``origin_asn`` is outside 0..4294967295.
    """
    _check_network(prefix, "prefix")
    if origin_asn is not None:
        _check_asn(origin_asn, "origin_asn")
    match: dict[str, set[IrrRoute]] = {name: set() for name in sources}
    clash: dict[str, set[IrrRoute]] = {name: set() for name in match}
    for route in routes:
        match.setdefault(route.source, set())
        clash.setdefault(route.source, set())
        if route.prefix != prefix:
            continue
        (match if route.origin_asn == origin_asn else clash)[route.source].add(route)

    def ordered(items: set[IrrRoute]) -> tuple[IrrRoute, ...]:
        return tuple(sorted(items, key=lambda r: (r.source, r.origin_asn)))

    out = []
    for name in sorted(match):
        status = (
            IrrStatus.REGISTERED
            if match[name]
            else IrrStatus.CONFLICTING
            if clash[name]
            else IrrStatus.ABSENT
        )
        out.append(IrrSourceEvidence(name, status, ordered(match[name]), ordered(clash[name])))
    return IrrEvidence(tuple(out))


@dataclass(frozen=True, slots=True)
class OriginVerdict:
    """The RPKI state and the IRR evidence for one route, side by side and never merged."""

    rov: RovResult
    irr: IrrEvidence


def check_origin(
    prefix: Network,
    asn: int | None,
    roas: Iterable[Vrp],
    irr: Iterable[IrrRoute],
    sources: Iterable[str] = (),
) -> OriginVerdict:
    """Pair the RFC 6811 state (`rov_state`) with the IRR evidence (`irr_evidence`) for one route.

    The two answers are independent inputs to a later confidence judgement (``score.confidence``):
    this function neither ranks them nor lets IRR data change the RFC 6811 state, so an RPKI
    ``NotFound`` stays ``NotFound`` however many registries list the route.
    """
    return OriginVerdict(rov_state(prefix, asn, roas), irr_evidence(prefix, asn, irr, sources))
