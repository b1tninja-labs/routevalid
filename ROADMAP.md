# Specification completeness -- and the roadmap it implies

This is the project's north star: every protocol obligation routevalid could plausibly take on,
with an honest status against the code at `HEAD`. It is blunt about gaps on purpose. A
roadmap that overstates its coverage is not a plan, it is marketing.

**The honesty rule:** a row may read `[ok]` only when a named test would fail if the
behaviour regressed. Reading the code and agreeing with it is not enough. That is how
"decoded but never sent" quietly becomes "implemented".

Legend: `[ok]` implemented and pinned by a named test -- `[part]` partial, with what is
missing stated -- `[ ]` not implemented -- `[no]` deliberate non-goal.

A Where cell marked `(to be written)` names the test that will pin the row once it exists; no
such test has been written yet, and the row cannot leave `[ ]` until it has. The Milestone
column places the row on the ladder in section 2, and `-` means it is not placed yet.

Update the affected row in the same commit that changes the behaviour. A row and its test
drift apart within one release, and the document becomes useless exactly when it is needed.

## 1. Obligations

| Obligation | Spec | Status | Where | Milestone |
|---|---|---|---|---|
| `observe.record()` | design; acceptance: a recorded observation is replayable byte for byte from its stored form | `[ ]` | `tests/test_obligations.py::test_record` (to be written) | M1 |
| `visibility.announcers()` | design; acceptance: the answer carries which collectors and peers were consulted, so "not seen" and "not asked" differ | `[ ]` | `tests/test_obligations.py::test_announcers` (to be written) | M1 |
| `visibility.coverage_state` | design: a typed coverage state (seen, not seen, unknown) travels with every visibility answer | `[ ]` | `tests/test_coverage.py::test_coverage_state` (to be written) | M1 |
| `origin.rov_state()` | RFC 6811 section 2 and 2.1, RFC 8481 section 4; pure, no IRR parameter | `[ok]` | `tests/test_origin.py::test_rov_matches_bruteforce_oracle`, `tests/test_origin.py::test_one_match_among_many_is_valid_regardless_of_order` | M2a |
| `origin.route_origin_asn()` | RFC 6811 section 2 (AS_SEQUENCE, confederation and empty-path rules), segment codes from RFC 4271 section 4.3 and RFC 5065 section 3 | `[ok]` | `tests/test_origin.py::test_origin_final_as_set_is_none`, `tests/test_origin.py::test_origin_confed_tail_is_local` | M2a |
| `origin.irr_evidence()` | design (RFC 2622 section 4: route plus origin is the key); per source, advisory, never an RFC 6811 state | `[ok]` | `tests/test_origin.py::test_irr_evidence_per_source_statuses`, `tests/test_origin.py::test_irr_evidence_is_never_an_rov_state` | M2a |
| `origin.check_origin()` | RFC 6811 for the state half (the row cited RFC 6480, the architecture document); returns RPKI state and IRR evidence as two fields, never one merged verdict, plus the optional RFC 9774 AS_SET finding as a third | `[ok]` | `tests/test_origin.py::test_check_origin_pairs_without_merging`, `tests/test_origin.py::test_check_origin_irr_cannot_rescue_an_invalid_route` | M2a |
| `origin.effective_origin()` | RFC 8893 sections 1, 3 and 4 (read in full, no errata): pure function of the AS_PATH segments and explicit egress knobs (Private Use removal per RFC 6996 section 5, confederation stripping per RFC 5065 section 4.1 (c), local-AS prepend per RFC 4271 section 5.1.2 (b)); RFC 8893 fixes no algorithm for the knobs, so the order is this library's choice and documented | `[ok]` | `tests/test_effective_origin.py::test_effective_origin`, `tests/test_effective_origin.py::test_effective_origin_decides_the_rov_state`, `tests/test_effective_origin.py::test_effective_origin_confederation_segments_are_stripped_for_external_peers` | M2b |
| `origin.effective_path()` | the path the effective origin is read from; RFC 4271 section 5.1.2, RFC 5065 section 4.1 | `[ok]` | `tests/test_effective_origin.py::test_effective_path_prepend_follows_rfc_4271_5_1_2` | M2b |
| `origin.as_set_policy()` | RFC 9774 sections 3 and 4 (read in full, no errata): treat-as-withdraw on AS_SET or AS_CONFED_SET unless configured otherwise; ROV never Valid and ASPA always Invalid for an AS_SET anywhere in the path. Which RFC 6811 state replaces Valid is unspecified, so none is chosen | `[ok]` | `tests/test_effective_origin.py::test_as_set_policy`, `tests/test_effective_origin.py::test_as_set_policy_configured_to_accept_never_makes_the_route_valid` | M2b |
| `origin.as_set_rov_state` | decision: RFC 9774 section 4 says an AS_SET route is never Valid, but RFC 6811 section 2 only makes the origin NONE when the *final* segment is a set, so an AS_SET in the middle of a path still reaches Valid in `rov_state`. Decided 2026-11-13 (PORTFOLIO.md sec. 9 item 15): `check_origin(..., segments=)` keeps the RFC 6811 state and reports the `as_set_policy` finding in `OriginVerdict.as_set` beside it; it never invents a replacement state | `[ok]` | `tests/test_origin.py::test_check_origin_reports_the_as_set_finding_beside_the_rfc_6811_state` | M2b |
| `origin.rov_against_rpkit_and_rtrkit` | feed `rov_state` from rpkit assertions and the rtrkit stream; both are shells, so this is design-only until they land. `Vrp` is plain data here and converts by field | `[ ]` | `tests/test_vrp_feed.py::test_vrp_feed` (to be written) | M2b |
| `leak.otc_check_ingress` | RFC 9234 section 5 ingress rules (read before writing); needs the OTC attribute from pathattr | `[ ]` | `tests/test_leak_ingress.py::test_otc_check_ingress` (to be written) | M3 |
| `leak.otc_check_egress` | RFC 9234 section 5 egress rules | `[ ]` | `tests/test_leak_egress.py::test_otc_check_egress` (to be written) | M3 |
| `leak.check_path()` | RFC 9234 | `[ ]` | `tests/test_obligations.py::test_check_path` (to be written) | M3 |
| `leak.infer_relationships` | design: relationship inference when no BGP role is negotiated; an inference model, not an RFC; acceptance is a labelled corpus | `[ ]` | `tests/test_infer.py::test_infer_relationships` (to be written) | M3 |
| `score.confidence()` | design; acceptance: monotone, adding an independent observer never lowers confidence, property-tested; combines `OriginVerdict.rov` and `.irr` without letting IRR move an RPKI state | `[ ]` | `tests/test_obligations.py::test_confidence` (to be written) | M4 |
| `event.schema_version` | design: the event schema carries a version and an additive-change rule | `[ ]` | `tests/test_event_schema.py::test_schema_version` (to be written) | M4 |
| `event.verify_bundle` | design: an evidence bundle holds hashes over its inputs and can be re-verified; the README promises replayable evidence and no row defined the bundle | `[ ]` | `tests/test_bundle.py::test_verify_bundle` (to be written) | M4 |
| `event.emit()` | design | `[ ]` | `tests/test_obligations.py::test_emit` (to be written) | M4 |
| `replay.reevaluate()` | RFC 9324 | `[ ]` | `tests/test_obligations.py::test_reevaluate` (to be written) | M5 |
| `replay.fixture_loader` | design: load a recorded observation set so a replay is a fixture, not a network call | `[ ]` | `tests/test_fixture_loader.py::test_fixture_loader` (to be written) | M5 |
| `replay.historical_corpus` | M5 says "then a historical corpus to measure false positives" and no row owned it; acceptance is a published precision figure | `[ ]` | `docs/corpus.md` (to be written) | M5 |
| `plan.depends-on` | `docs/plan.md` names rpkit and rtrkit only. The real set adds pathattr (OTC and AS_PATH), bmpkit and bgpfeed (observations) and rpslkit (IRR); `rov_state` needs none of them. The file is generated, so PORTFOLIO.md changes | `[ ]` | `PORTFOLIO.md` section 4 (owner) | - |
| `aspa.verify()` | draft-ietf-sidrops-aspa-verification-29 sections 5.2 to 5.6 (pinned; an Internet-Draft read raw from ietf.org/archive/id, not an RFC): `authorized`, COMPRESSED_AS_PATH, the four ramp bounds, upstream and downstream algorithms, RS-client exception, AS_SET Invalid | `[ok]` | `tests/test_aspa.py::test_verify_matches_enumeration_oracle`, `tests/test_aspa.py::test_downstream_leak_is_invalid`, `tests/test_aspa.py::test_upstream_valid_unknown_invalid`, `tests/test_aspa.py::test_upstream_halts_before_the_ramps` | M2b |
| `aspa.union_spas()` | draft section 5.3: union of several ASPAs, AS0 dropped beside others; 8210bis-29 section 5.12 (an ASPA has at least one provider) | `[ok]` | `tests/test_aspa.py::test_union_spas_unions_and_drops_as0_beside_others` | M2b |
| `aspa.applicable()` | draft section 6.2: AFI 1 or 2 with SAFI 1 only | `[ok]` | `tests/test_aspa.py::test_applicable_families` | M2b |
| `aspa.feed` | build the U-SPAS table from rpkit ASPA objects or the rtrkit ASPA PDU (draft-ietf-sidrops-8210bis-29 section 5.12); both are shells. Plain data: customer to set of providers | `[ ]` | `tests/test_aspa_feed.py::test_aspa_feed` (to be written) | M2b |
| `aspa.direction_from_role` | draft sections 6.3 and 6.4: choose upstream or downstream from the RFC 9234 role, and the Complex-relationship fallback (apply downstream); needs `leak` roles | `[ ]` | `tests/test_aspa_role.py::test_direction_from_role` (to be written) | M3 |
| `aspa.as_path_reconstruction` | draft section 5: apply to the reconstructed AS_PATH (RFC 6793 section 4.2.3); pathattr owns the AS4_PATH merge, so a pathattr row is the prerequisite | `[ ]` | `tests/test_aspa_pathattr.py::test_reconstructed_path` (to be written) | M2b |
| `aspa.as0-in-path` | the draft does not say what an AS 0 inside an AS_PATH means; `authorized` looks it up like any ASN. Ask the draft authors or refuse AS 0 in the path | `[ ]` | `tests/test_aspa.py::test_as0_in_path` (to be written) | - |
| `aspa.draft-to-rfc` | re-pin when draft-ietf-sidrops-aspa-verification publishes as an RFC; re-check section numbers and the confederation-segment behaviour (the draft is silent; this code reports Invalid) | `[ ]` | `docs/rfc-map.md` (owner) | - |

## 2. Milestones

- M1 the observation model and visibility tracking
- M2a RFC 6811 state, route origin AS and IRR evidence on plain data, no dependency. Done 2026-11-13
- M2b origin checks against rpkit assertions and rpslkit output; effective origin (RFC 8893), AS_SET policy (RFC 9774) and ASPA verification (draft -29) on plain data done 2026-11-13
- M3 role based leak checks with an inferred relationship fallback
- M4 confidence scoring and the event schema with evidence
- M5 replay, then a historical corpus to measure false positives
- M6 publication: 0.1.0 with a measured precision report

Every milestone is accepted by its rows above flipping to `[ok]` with a named test, not by
the code existing. Coverage in `pyproject.toml` ratchets in the same commit.

## 3. Errata watch

- RFC 9234 reports no errata as of 2026-10-29, and deployment is thin enough that you should expect to test against peers who do not send the attribute.
- RFC 4271 carries 9 verified errata and is updated by RFC 9774, which also updates RFC 5065 (1 verified erratum): read the errata before the AS_PATH rows close.
- RFC 2622 carries 3 verified errata and is updated by RFC 4012 and RFC 7909; `origin.irr_evidence` uses only the section 4 route class key, on which none of the errata sit.
- RFC 6480 has 1 erratum on file, none verified; RFC 9324 updates RFC 8481 and should be read together with it. RFC 6811 is updated by RFC 8481 and RFC 8893; neither RFC 6811 nor RFC 8481 has a verified erratum (rfclib, 2026-11-07).

## 4. Deliberate non-goals

| Non-goal | Status | Revisit when |
|---|---|---|
| a dashboard, an alerting pipeline or a ticket system | `[no]` | a named document requires it |
| storage engine design: it consumes a sink | `[no]` | a named document requires it |
| community based mitigation or any action against a router: detection only | `[no]` | a named document requires it |

## 5. Open questions

- **D1 (owner decision, recommended): where RFC 6811 lives.** It was planned three times: rpkit `validation.validate_origin`, routevalid `check_origin`, asnkit `rov.annotate`. Recommendation: **routevalid is the home**. `origin.rov_state` is pure, has no dependency and is done, with an independent oracle test. rpkit cannot import it (routevalid depends on rpkit, so that would be a cycle) and its job is to emit VRPs; asnkit can import routevalid, or keep a one-line indexed wrapper for RIB-scale joins. Record the decision on the board and mark rpkit's `validation.validate_origin` row `[no]`.
- the VRP type: routevalid and rpkit each keep a plain `Vrp(prefix, max_length, asn)` and convert by field, so neither project imports the other. Revisit if a shared record package is ever wanted.
- the sink interface shape for `event.emit`
- whether an IRR route with no origin (a route whose origin is NONE) belongs in `irr_evidence` at all; it is `CONFLICTING` today
- host bits on a route prefix: decided, the API takes `ipaddress` networks and a strict network refuses them; a caller holding text parses with `ip_network(text)` and handles the error

## 6. Publication checklist

- [ ] every `[ ]` row above either `[ok]` or moved to a named later milestone
- [ ] `docs/research.md` claims re-verified and the dated ones either promoted or deleted
- [ ] interoperability evidence recorded in `docs/` against a non-Python implementation
- [ ] `tools/check_dist.py` proves the wheel ships the fixtures the README promises
- [ ] version 0.1.0 tagged, trusted publisher configured, README badges uncommented
