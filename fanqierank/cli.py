from __future__ import annotations

import argparse
from pathlib import Path

from .constants import ALL_CHANNELS, DEFAULT_CHANNEL, CHANNELS, expand_channels
from .pipeline import (
    PipelineConfig,
    collect_raw_report,
    finalize_report_from_analysis,
    finalize_report_with_fallback_analysis,
    run_pipeline,
    today_in_timezone,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fanqierank", description="Generate Fanqie male/female new-book rank reports.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Collect raw Fanqie new-book rank data.")
    _add_common_args(collect_parser)
    collect_parser.add_argument("--limit", type=int, default=30, help="Books per category.")
    collect_parser.add_argument("--sleep-seconds", type=float, default=3.0, help="Delay between categories.")

    fallback_parser = subparsers.add_parser("fallback-finalize", help="Render publishable data using local heuristic analysis.")
    fallback_parser.add_argument("--date", required=True, help="Report date, YYYY-MM-DD.")
    fallback_parser.add_argument("--output", type=Path, default=Path("."), help="Repository root.")
    _add_channel_arg(fallback_parser)

    finalize_parser = subparsers.add_parser("finalize", help="Render publishable data from Codex analysis JSON.")
    finalize_parser.add_argument("--date", required=True, help="Report date, YYYY-MM-DD.")
    finalize_parser.add_argument("--output", type=Path, default=Path("."), help="Repository root.")
    finalize_parser.add_argument("--analysis-file", type=Path, help="Defaults to data/analysis/YYYY-MM-DD.json.")
    _add_channel_arg(finalize_parser)

    run_parser = subparsers.add_parser("run", help="Collect raw data and fallback-finalize it.")
    _add_common_args(run_parser)
    run_parser.add_argument("--limit", type=int, default=30, help="Books per category.")
    run_parser.add_argument("--sleep-seconds", type=float, default=3.0, help="Delay between categories.")

    args = parser.parse_args(argv)

    if args.command == "collect":
        report_date = args.date or today_in_timezone(args.timezone)
        for channel in expand_channels(args.channel):
            snapshot = collect_raw_report(PipelineConfig(
                report_date=report_date,
                timezone=args.timezone,
                output_root=args.output,
                limit=args.limit,
                sleep_seconds=args.sleep_seconds,
                channel=channel.key,
            ))
            print(f"Collected {len(snapshot.categories)} {channel.label} categories for {snapshot.date}")
        return 0

    if args.command == "fallback-finalize":
        for channel in expand_channels(args.channel):
            result = finalize_report_with_fallback_analysis(args.date, args.output, channel.key)
            print(f"Fallback-finalized {result['category_count']} {channel.label} categories for {result['date']}")
        return 0

    if args.command == "finalize":
        if args.channel == ALL_CHANNELS and args.analysis_file:
            parser.error("--analysis-file cannot be used with --channel all")
        for channel in expand_channels(args.channel):
            result = finalize_report_from_analysis(args.date, args.output, args.analysis_file, channel.key)
            print(f"Finalized {result['category_count']} Codex-analyzed {channel.label} categories for {result['date']}")
        return 0

    if args.command == "run":
        report_date = args.date or today_in_timezone(args.timezone)
        for channel in expand_channels(args.channel):
            result = run_pipeline(PipelineConfig(
                report_date=report_date,
                timezone=args.timezone,
                output_root=args.output,
                limit=args.limit,
                sleep_seconds=args.sleep_seconds,
                channel=channel.key,
            ))
            print(f"Generated {result['category_count']} {channel.label} categories for {result['date']}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date", help="Report date, YYYY-MM-DD. Defaults to today in --timezone.")
    parser.add_argument("--timezone", default="Asia/Shanghai", help="IANA timezone.")
    parser.add_argument("--output", type=Path, default=Path("."), help="Repository root.")
    _add_channel_arg(parser)


def _add_channel_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--channel",
        choices=[*CHANNELS.keys(), ALL_CHANNELS],
        default=DEFAULT_CHANNEL,
        help="Rank channel to process.",
    )
