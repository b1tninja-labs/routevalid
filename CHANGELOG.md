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

- `origin.effective_origin` and `origin.effective_path` (RFC 8893 sections 1, 3, 4): the Route Origin ASN of
  the UPDATE as it will be sent, with explicit knobs for Private Use AS removal (RFC 6996 ranges),
  confederation stripping (RFC 5065 section 4.1) and local-AS prepend (RFC 4271 section 5.1.2).
- `origin.as_set_policy` (RFC 9774 sections 3 and 4): treat-as-withdraw, ROV never Valid and ASPA Invalid
  for an AS_SET.
- `routevalid.aspa`: ASPA AS_PATH verification pinned to draft-ietf-sidrops-aspa-verification-29
  (provider authorization, ramp bounds, upstream and downstream algorithms), checked against an
  independent enumeration oracle.

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
