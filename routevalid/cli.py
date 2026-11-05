"""Command line entry point for routevalid.

The CLI is how most people meet a protocol library, so it is part of the public surface and
gets the same typing and testing discipline as the rest of the package.
"""

from __future__ import annotations

import argparse
import sys

USAGE = """\
Examples:
  routevalid watch --prefix 1.2.3.0/24 --sources bmp,ris --min-confidence 0.8"""


def build_parser():
    return argparse.ArgumentParser(
        prog="routevalid",
        description="Correlates BMP sessions, RIS and RouteViews feeds, RPKI assertions, RTR updates and IRR objects into typed events with a replayable evidence bundle",
        epilog=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def main(argv=None):
    """Parse arguments, then refuse to pretend the protocol works.

    Exiting non-zero is the correct behaviour for a shell. A CLI that printed a friendly
    banner and exited 0 would be indistinguishable from one that actually did something.
    """
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_usage(sys.stderr)
    print("routevalid: no protocol behaviour is implemented yet; see ROADMAP.md", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
