"""Command-line entrypoint for LectureScribe."""

from __future__ import annotations

import sys

from lecturescribe.app import run


def main() -> int:
    """Run LectureScribe."""
    return run()


if __name__ == "__main__":
    sys.exit(main())
