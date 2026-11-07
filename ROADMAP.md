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
| `observe.record()` | design | `[ ]` | `tests/test_obligations.py::test_record` (to be written) | M1 |
| `visibility.announcers()` | design | `[ ]` | `tests/test_obligations.py::test_announcers` (to be written) | M1 |
| `origin.check_origin()` | RFC 6480 | `[ ]` | `tests/test_obligations.py::test_check_origin` (to be written) | M2 |
| `leak.check_path()` | RFC 9234 | `[ ]` | `tests/test_obligations.py::test_check_path` (to be written) | M3 |
| `score.confidence()` | design | `[ ]` | `tests/test_obligations.py::test_confidence` (to be written) | M4 |
| `event.emit()` | design | `[ ]` | `tests/test_obligations.py::test_emit` (to be written) | M4 |
| `replay.reevaluate()` | RFC 9324 | `[ ]` | `tests/test_obligations.py::test_reevaluate` (to be written) | M5 |

## 2. Milestones

- M1 the observation model and visibility tracking
- M2 origin checks against rpkit assertions and rpslkit output
- M3 role based leak checks with an inferred relationship fallback
- M4 confidence scoring and the event schema with evidence
- M5 replay, then a historical corpus to measure false positives
- M6 publication: 0.1.0 with a measured precision report

Every milestone is accepted by its rows above flipping to `[ok]` with a named test, not by
the code existing. Coverage in `pyproject.toml` ratchets in the same commit.

## 3. Errata watch

- RFC 9234 reports no errata as of 2026-10-29, and deployment is thin enough that you should expect to test against peers who do not send the attribute.
- RFC 6480 has 1 erratum on file, none verified; RFC 9324 updates RFC 8481 and should be read together with it. RFC 6811 is updated by RFC 8481 and RFC 8893; neither RFC 6811 nor RFC 8481 has a verified erratum (rfclib, 2026-11-07).

## 4. Deliberate non-goals

| Non-goal | Status | Revisit when |
|---|---|---|
| a dashboard, an alerting pipeline or a ticket system | `[no]` | a named document requires it |
| storage engine design: it consumes a sink | `[no]` | a named document requires it |
| community based mitigation or any action against a router: detection only | `[no]` | a named document requires it |

## 5. Open questions

- none recorded yet

## 6. Publication checklist

- [ ] every `[ ]` row above either `[ok]` or moved to a named later milestone
- [ ] `docs/research.md` claims re-verified and the dated ones either promoted or deleted
- [ ] interoperability evidence recorded in `docs/` against a non-Python implementation
- [ ] `tools/check_dist.py` proves the wheel ships the fixtures the README promises
- [ ] version 0.1.0 tagged, trusted publisher configured, README badges uncommented
