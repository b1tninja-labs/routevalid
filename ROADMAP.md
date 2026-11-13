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
| `origin.check_origin()` | RFC 6811 for the state half (the row cited RFC 6480, the architecture document); returns RPKI state and IRR evidence as two fields, never one merged verdict | `[ok]` | `tests/test_origin.py::test_check_origin_pairs_without_merging`, `tests/test_origin.py::test_check_origin_irr_cannot_rescue_an_invalid_route` | M2a |
| `origin.effective_origin` | RFC 8893: the effective origin AS for export-side validation (after private-AS removal and confederation handling); not read yet | `[ ]` | `tests/test_effective_origin.py::test_effective_origin` (to be written) | M2b |
| `origin.as_set_policy` | RFC 9774 (updates RFC 4271 and RFC 5065): read section 4 in full, then pin that a route with AS_SET never validates; the `None` origin already cannot be Valid | `[ ]` | `tests/test_as_set.py::test_as_set_policy` (to be written) | M2b |
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
| `aspa.verification` | no ASPA RFC is in the library; RFC 9774 cites `draft-ietf-sidrops-aspa-verification`. Recorded as an unciteable draft until a profile publishes | `[ ]` | `docs/research.md` finding (not committed) | - |

## 2. Milestones

- M1 the observation model and visibility tracking
- M2a RFC 6811 state, route origin AS and IRR evidence on plain data, no dependency. Done 2026-11-13
- M2b origin checks against rpkit assertions and rpslkit output, effective origin (RFC 8893)
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
