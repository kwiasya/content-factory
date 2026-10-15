"""Old name of ``cf.footage``: ``python -m cf.walk …`` still runs it, with a notice on stderr."""

from __future__ import annotations

import sys

from cf import footage


def main(argv: list[str] | None = None) -> int:
    print("cf.walk is now cf.footage", file=sys.stderr)
    return footage.main(argv)


if __name__ == "__main__":
    sys.exit(main())
