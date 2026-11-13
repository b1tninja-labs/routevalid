# Changelog

The format follows Keep a Changelog, and this project adheres to Semantic Versioning.

## Unreleased

### Added

- `origin.rov_state`: the RFC 6811 section 2 validation state on plain data, returning the state with
  the covering and matching VRPs that decided it. Tested against an independent bit-string oracle.
- `origin.route_origin_asn`: the Route Origin ASN rules of RFC 6811 section 2 from AS_PATH segments.
- `origin.irr_evidence` and `origin.check_origin`: IRR route-object evidence kept in its own type, per
  source, and paired with (never merged into) the RPKI state.
- ROADMAP rows for the rest of the work, the spec spine corrected (RFC 8893, RFC 9774, RFC 4271,
  RFC 5065, RFC 2622, RFC 7854 added), and owner decision D1: RFC 6811 lives here.

### Changed

- `origin.check_origin` returns an `OriginVerdict` with `rov` and `irr` fields; it previously mixed an
  RFC 6811 state with IRR evidence in one `OriginVerdict`, and its row cited RFC 6480, the
  architecture document, instead of RFC 6811.

The other public functions are still stubs that raise `NotImplementedError`;
[ROADMAP.md](ROADMAP.md) lists what blocks them.

## 0.0.0 - 2026-11-05

### Added

- Package skeleton, obligation matrix and CI gates for routevalid.
- `routevalid.apps` namespace reserved for composition that is not protocol behaviour.
