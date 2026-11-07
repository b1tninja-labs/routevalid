# routevalid

<!-- PyPI badges go live with the first release. Until then a version badge renders
     "no version" on the landing page, which reads as a defect rather than a date, so
     the badges stay commented out until the tag exists.
-->

**Pre-alpha shell.** The package surface, the obligation matrix and the CI gates exist.
No protocol behaviour is implemented: every public function raises `NotImplementedError`,
and the test suite records that rather than hiding it. Read
[ROADMAP.md](ROADMAP.md) before depending on any of it.

routevalid -- hijack and leak detection with evidence attached

Detection tools either are research prototypes or are hosted dashboards you cannot self host. What is missing is a library: given observations from your own BMP sessions plus RIS and RouteViews, plus RPKI from rpkit and RTR state from rtrkit, emit typed events with the evidence that justified each one. RFC 9234 gives the role information that makes leaks checkable against declared relationships rather than guessed, and that document has no errata and almost no implementations, which is exactly the kind of gap this portfolio exists for.

## The gap, with a date

PyPI was queried on 2026-11-05 for this name and for every neighbouring project. Landscape
claims rot quickly: two projects in this portfolio shipped within five days of the survey,
which is why the table below carries dates instead of adjectives.

| Project | Version | Last release | Why it is not this project |
|---|---|---|---|
| STEAL-179 and similar research tools | - | - | research artefacts, not maintained libraries |
| hosted monitoring dashboards | - | - | BGPStream based services: useful, but not something you can embed |
| routevalid, leakkit, stealer, bgp-hijack | - | - | all free on PyPI (2026-11-05) |

What this project intends to add:

- prefix visibility tracking: who announces it, from which AS, seen by which collectors
- origin checks combining RPKI state, RPSL assertions and observed AS paths with explicit disagreement handling
- leak checks using declared roles where available and inferred relationships where not
- confidence scoring from collector diversity, so one vantage point cannot raise a page
- an evidence bundle per event, replayable from the raw observations

## Specification spine

Status and publication dates below were read from the RFC Editor record on 2026-11-05. A
section number is cited only where that section was read in full; everything else cites the
document, which is the honest grain size for a plan. See [docs/rfc-map.md](docs/rfc-map.md).

| Document | Status | Published | What it gives this project |
|---|---|---|---|
| RFC 9234 | Proposed Standard | 2022-05 | roles in OPEN and UPDATE: the basis for leak detection against declared relationships |
| RFC 6480 | Informational | 2012-02 | the RPKI architecture whose assertions an origin check consumes |
| RFC 9324 | Proposed Standard | 2022-12 | why fresh RPKI data must not trigger a route refresh when re-evaluating |
| RFC 6396 | Proposed Standard | 2011-10 | the archive format for replaying history against a detection rule |
| RFC 6811 | Proposed Standard | 2013-01 | BGP prefix origin validation: the Valid, Invalid and NotFound states an origin check returns |
| RFC 8481 | Proposed Standard | 2018-09 | clarifications to origin validation: every prefix gets a state, no policy without operator configuration |

### Errata watch

- RFC 9234 reports no errata as of 2026-10-29, and deployment is thin enough that you should expect to test against peers who do not send the attribute.
- RFC 6480 has 1 erratum on file, none verified; RFC 9324 updates RFC 8481 and should be read together with it. RFC 6811 is updated by RFC 8481 and RFC 8893; neither RFC 6811 nor RFC 8481 has a verified erratum (rfclib, 2026-11-07).

## Module layout

| Module | Responsibility |
|---|---|
| `observe` | the normalised observation model from bmpkit and bgpfeed |
| `visibility` | prefix and AS visibility tracking over collectors and time |
| `origin` | origin checks combining RPKI, RPSL and observed paths |
| `leak` | role and relationship checks on AS paths (RFC 9234) |
| `score` | confidence from collector diversity and disagreement |
| `event` | typed events with severity, evidence and replay references |
| `replay` | deterministic re-evaluation of history against a rule set |
| `rules` | the policy object deciding what counts as an event |

## What it does not do

- a dashboard, an alerting pipeline or a ticket system
- storage engine design: it consumes a sink
- community based mitigation or any action against a router: detection only


## Install

```bash
git clone https://github.com/b1tninja/routevalid.git
cd routevalid
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
```

Not published to PyPI yet. The name is reserved for this repository's trusted publisher at
the moment of the first release.

## Development

All four gates must pass, on Linux and Windows alike:

```bash
ruff check . && ruff format --check .
mypy routevalid tests
pytest -q --cov
python -O -m pytest -q
```

The last line is the one that matters most in a protocol library. `-O` strips `assert`, and a
parser whose bounds checks were asserts stops being a parser under production flags. Wire
paths raise named exceptions; asserts belong in tests and nowhere else.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
