# Specification completeness -- and the roadmap it implies

This is the project's north star: every protocol obligation routevalid could plausibly take on,
with an honest status against the code at `HEAD`. It is blunt about gaps on purpose. A
roadmap that overstates its coverage is not a plan, it is marketing.

**The honesty rule:** a row may read `[ok]` only when a named test would fail if the
behaviour regressed. Reading the code and agreeing with it is not enough. That is how
"decoded but never sent" quietly becomes "implemented".

Legend: `[ok]` implemented and pinned by a named test -- `[part]` partial, with what is
missing stated -- `[ ]` not implemented -- `[no]` deliberate non-goal.

Update the affected row in the same commit that changes the behaviour. A row and its test
drift apart within one release, and the document becomes useless exactly when it is needed.

## 1. Obligations

| Obligation | Spec | Status | Where |
|---|---|---|---|
| `observe.record()` | design | `[ ]` | `tests/test_obligations.py::record` |
| `visibility.announcers()` | design | `[ ]` | `tests/test_obligations.py::announcers` |
| `origin.check_origin()` | RFC 6480 | `[ ]` | `tests/test_obligations.py::check_origin` |
| `leak.check_path()` | RFC 9234 | `[ ]` | `tests/test_obligations.py::check_path` |
| `score.confidence()` | design | `[ ]` | `tests/test_obligations.py::confidence` |
| `event.emit()` | design | `[ ]` | `tests/test_obligations.py::emit` |
| `replay.reevaluate()` | RFC 9324 | `[ ]` | `tests/test_obligations.py::reevaluate` |

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
- RFC 6480 has 1 erratum on file, none verified; RFC 9324 updates RFC 8481 and should be read together with it.

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
