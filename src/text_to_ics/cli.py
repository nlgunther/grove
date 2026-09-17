"""
text_to_ics/cli.py — thin CLI entry point.

Routing and formatting only; the actual extract → adapt → write
pipeline lives in run().
"""
import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from shared.calendar.ics_writer import ICSWriter
from .adapter import to_calendar_event
from .extractor import EventExtractor
from .heuristic_extractor import HeuristicExtractor

_DEFAULT_TZ = "America/Los_Angeles"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="text2ics",
        description="Convert free text into a Google-Calendar-ready .ics file.",
    )
    parser.add_argument("text", nargs="?", help="Event text (reads stdin if omitted)")
    parser.add_argument("-o", "--output", help="Output .ics path (default: stdout)")
    parser.add_argument("--calendar-name", default="text-to-ics", help="X-WR-CALNAME value")
    parser.add_argument("--tz", default=_DEFAULT_TZ, help=f"Reference timezone (default: {_DEFAULT_TZ})")
    parser.add_argument(
        "--extractor", choices=["heuristic", "llm"], default="heuristic",
        help="Extraction backend (default: heuristic, no API calls)",
    )
    return parser


def run(text: str, extractor: EventExtractor, tz: str, calendar_name: str) -> str:
    """Extract events from text and return the complete .ics content."""
    reference = datetime.now(ZoneInfo(tz))
    specs = extractor.extract(text, reference=reference)

    writer = ICSWriter(calendar_name)
    for spec in specs:
        writer.add_event(to_calendar_event(spec))
    return writer.to_string()


def _get_extractor(name: str) -> EventExtractor:
    if name == "llm":
        from .llm_extractor import LLMExtractor
        return LLMExtractor()
    return HeuristicExtractor()


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    text = args.text if args.text is not None else sys.stdin.read()

    try:
        ics_content = run(text, _get_extractor(args.extractor), args.tz, args.calendar_name)
    except ValueError as exc:
        print(f"text2ics: {exc}", file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(ics_content)
    else:
        print(ics_content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
