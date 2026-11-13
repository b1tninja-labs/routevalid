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
segment type codes, RFC 2622 section 4. RFC 8893 sections 1, 3 and 4 (the *effective origin* for
export-side validation; `effective_origin`), RFC 9774 sections 3 and 4 (AS_SET and AS_CONFED_SET;
`as_set_policy`), RFC 4271 section 5.1.2, RFC 5065 section 4.1 and RFC 6996 sections 3 to 5 were
read for the second pass; none has an erratum on the sections used. RFC 4012 adds the ``route6`` class for IPv6; it was
not read, and `irr_evidence` treats an IPv6 route object with the same key shape.
"""

from __future__ import annotations

import enum
import ipaddress
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

__all__ = [
    "MAX_ASN",
    "AsSetVerdict",
    "IrrEvidence",
    "IrrRoute",
    "IrrSourceEvidence",
    "IrrStatus",
    "OriginVerdict",
    "PrivateRemoval",
    "RovResult",
    "RovState",
    "SegmentType",
    "Vrp",
    "as_set_policy",
    "check_origin",
    "effective_origin",
    "effective_path",
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
    """The RPKI state and the IRR evidence for one route, side by side and never merged.

    ``as_set`` is the RFC 9774 finding for the route's AS_PATH, beside them, or ``None`` when no
    path was given. It never changes ``rov``: if it says ``rov_may_be_valid`` is False and ``rov``
    says Valid, both are reported and the caller sees the disagreement. No replacement state is
    invented, because RFC 9774 does not name one (PORTFOLIO.md sec. 9 item 15).
    """

    rov: RovResult
    irr: IrrEvidence
    as_set: AsSetVerdict | None = None


def check_origin(
    prefix: Network,
    asn: int | None,
    roas: Iterable[Vrp],
    irr: Iterable[IrrRoute],
    sources: Iterable[str] = (),
    *,
    segments: Segments | None = None,
    configured_to_accept: bool = False,
) -> OriginVerdict:
    """Pair the RFC 6811 state (`rov_state`) with the IRR evidence (`irr_evidence`) for one route.

    The two answers are independent inputs to a later confidence judgement (``score.confidence``):
    this function neither ranks them nor lets IRR data change the RFC 6811 state, so an RPKI
    ``NotFound`` stays ``NotFound`` however many registries list the route.

    Given the route's AS_PATH as ``segments``, the RFC 9774 finding (`as_set_policy`) is reported
    beside them in ``OriginVerdict.as_set``. The RFC 6811 state is exactly what `rov_state` said:
    a route with an AS_SET that RFC 6811 calls Valid stays Valid here, with the finding next to it
    saying RFC 9774 section 4 never allows that. This function does not pick Invalid or NotFound
    in its place.
    """
    finding = (
        None
        if segments is None
        else as_set_policy(segments, configured_to_accept=configured_to_accept)
    )
    return OriginVerdict(
        rov_state(prefix, asn, roas), irr_evidence(prefix, asn, irr, sources), finding
    )


# ---- RFC 8893 effective origin and RFC 9774 AS_SET policy ----------------------------------------

#: RFC 6996 section 5: Private Use ASNs, 64512-65534 and 4200000000-4294967294 inclusive.
PRIVATE_RANGES: tuple[tuple[int, int], ...] = ((64512, 65534), (4200000000, 4294967294))


def is_private_asn(asn: int) -> bool:
    """True for a Private Use ASN (RFC 6996 section 5). 65535 and 4294967295 are the RFC 7300 last
    ASNs, reserved but not Private Use, so they are not private here."""
    return any(low <= asn <= high for low, high in PRIVATE_RANGES)


class PrivateRemoval(enum.Enum):
    """How an egress policy removes Private Use ASNs. RFC 8893 names the knob and fixes no
    algorithm, and RFC 6996 section 4 notes that implementations differ on mixed paths."""

    NONE = "none"
    ALL = "all"  # every Private Use ASN is dropped, wherever it sits
    ONLY_IF_ALL_PRIVATE = "only-if-all-private"  # a mixed path is left untouched


Segments = Sequence[tuple[int, Sequence[int]]]


def effective_path(
    segments: Segments,
    local_asn: int,
    *,
    remove_private: PrivateRemoval = PrivateRemoval.NONE,
    strip_confed: bool = True,
    prepend: int = 1,
) -> tuple[tuple[int, tuple[int, ...]], ...]:
    """The AS_PATH as it would be sent to an external peer, so the origin can be read from it.

    Order of the steps (RFC 8893 section 3 says validation state MUST be determined "using the
    effective origin AS of the route as it will (or would) be announced to the peer", and leaves the
    steps to the implementation, so this order is this library's choice):

    1. ``strip_confed``: remove AS_CONFED_SEQUENCE and AS_CONFED_SET segments (RFC 5065 section 4.1
       (c)(1), which applies when the peer is outside the confederation; pass False to model an
       advertisement to a member AS or an internal peer, where nothing is stripped).
    2. ``remove_private``: drop Private Use ASNs (RFC 6996 section 5 ranges); a segment left
       empty is removed.
    3. ``prepend``: put ``local_asn`` that many times at the front (RFC 4271 section 5.1.2 (b):
       onto a leading AS_SEQUENCE, or as a new AS_SEQUENCE when the path is empty or leads with an
       AS_SET; the same text allows more than one copy by local configuration). 0 models an
       advertisement that is not prepended, such as an internal peer.

    Segment types are ints; a member list is not validated beyond the ASN range. The local ASN is
    never removed by step 2 (it is added after), which is the usual router order but not mandated.
    """
    _check_asn(local_asn, "local_asn")
    if isinstance(prepend, bool) or not isinstance(prepend, int) or prepend < 0:
        raise ValueError("prepend must be a non-negative integer")
    out: list[tuple[int, tuple[int, ...]]] = []
    for kind, members in segments:
        for asn in members:
            _check_asn(asn, "AS_PATH member")
        if strip_confed and kind in (SegmentType.AS_CONFED_SEQUENCE, SegmentType.AS_CONFED_SET):
            continue
        out.append((int(kind), tuple(members)))
    everything = [asn for _, members in out for asn in members]
    if remove_private is PrivateRemoval.ALL or (
        remove_private is PrivateRemoval.ONLY_IF_ALL_PRIVATE
        and everything
        and all(is_private_asn(a) for a in everything)
    ):
        out = [(k, kept) for k, m in out if (kept := tuple(a for a in m if not is_private_asn(a)))]
    if prepend:
        mine = (local_asn,) * prepend
        if out and out[0][0] == SegmentType.AS_SEQUENCE:
            out[0] = (out[0][0], mine + out[0][1])
        else:
            out.insert(0, (int(SegmentType.AS_SEQUENCE), mine))
    return tuple(out)


def effective_origin(
    segments: Segments,
    local_asn: int,
    *,
    remove_private: PrivateRemoval = PrivateRemoval.NONE,
    strip_confed: bool = True,
    prepend: int = 1,
) -> int | None:
    """The effective origin AS of RFC 8893: the RFC 6811 Route Origin ASN of the UPDATE to be sent.

    RFC 8893 section 1 defines it as "the Route Origin ASN [RFC6811] of the UPDATE to be sent to
    neighboring BGP speakers" and section 3 requires egress validation to use it. This is
    `route_origin_asn` applied to `effective_path`; read that function for the knobs. ``None`` is
    RFC 6811's "NONE" (for example the final segment is an AS_SET). Feed the result to `rov_state`.
    """
    path = effective_path(
        segments,
        local_asn,
        remove_private=remove_private,
        strip_confed=strip_confed,
        prepend=prepend,
    )
    return route_origin_asn(path, local_asn)


@dataclass(frozen=True, slots=True)
class AsSetVerdict:
    """What RFC 9774 says about a path that carries set segments.

    ``has_as_set`` and ``has_confed_set`` say which set types appear anywhere in the path.
    ``treat_as_withdraw`` is RFC 9774 section 3's receive rule (RFC 7606), unless the operator
    configured otherwise. ``rov_may_be_valid`` is False when an AS_SET appears: section 4 says ROV
    "never allows a route with AS_SET to be considered Valid". ``aspa_invalid`` is section 4's
    "a route with AS_SET is always considered Invalid" for ASPA.
    """

    has_as_set: bool
    has_confed_set: bool
    treat_as_withdraw: bool
    rov_may_be_valid: bool
    aspa_invalid: bool


def as_set_policy(segments: Segments, *, configured_to_accept: bool = False) -> AsSetVerdict:
    """The RFC 9774 sections 3 and 4 consequences of AS_SET and AS_CONFED_SET in an AS_PATH.

    Section 3: unless explicitly configured otherwise (``configured_to_accept``, "e.g., during a
    transition phase"), a speaker MUST use treat-as-withdraw (RFC 7606) on receiving an AS_SET or
    AS_CONFED_SET. Section 4 is about AS_SET only: ROV never yields Valid and ASPA yields Invalid.
    AS_CONFED_SET is treated by this function as a set for the section 3 receive rule only, because
    section 4 does not name it; a path with a confederation segment should not reach a validator
    (confederation segments do not cross the confederation edge, RFC 5065 section 4.1).
    The section 4 flags hold even when ``configured_to_accept`` is set: acceptance does not make
    such a route Valid. RFC 9774 does not say which RFC 6811 state to report in place of Valid
    (Invalid or NotFound), so none is chosen here.
    """
    for kind, members in segments:
        for asn in members:
            _check_asn(asn, "AS_PATH member")
        if isinstance(kind, bool) or not isinstance(kind, int):
            raise TypeError("segment type must be an int")
    kinds = {int(kind) for kind, _ in segments}
    has_set = int(SegmentType.AS_SET) in kinds
    has_cset = int(SegmentType.AS_CONFED_SET) in kinds
    return AsSetVerdict(
        has_as_set=has_set,
        has_confed_set=has_cset,
        treat_as_withdraw=(has_set or has_cset) and not configured_to_accept,
        rov_may_be_valid=not has_set,
        aspa_invalid=has_set,
    )
