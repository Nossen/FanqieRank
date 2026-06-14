from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .analysis import (
    apply_codex_analysis,
    build_market_summary,
    compare_snapshots,
    trend_rows_with_current,
    validate_codex_analysis,
)
from .constants import DEFAULT_CHANNEL, TIMEZONE, get_channel
from .models import CodexAnalysis, RawSnapshot
from .renderer import write_final_outputs, write_raw_outputs
from .scraper import scrape_new_rank


@dataclass(frozen=True)
class PipelineConfig:
    report_date: str
    timezone: str = TIMEZONE
    output_root: Path = Path(".")
    limit: int = 30
    sleep_seconds: float = 3.0
    channel: str = DEFAULT_CHANNEL


def today_in_timezone(timezone: str = TIMEZONE) -> str:
    return datetime.now(ZoneInfo(timezone)).date().isoformat()


def collect_raw_report(
    config: PipelineConfig,
    scraper=None,
) -> RawSnapshot:
    channel_config = get_channel(config.channel)
    scraper = scraper or scrape_new_rank
    snapshot = scraper(
        channel=channel_config.key,
        report_date=config.report_date,
        timezone=config.timezone,
        limit=config.limit,
        sleep_seconds=config.sleep_seconds,
    )
    if not snapshot.categories:
        raise RuntimeError("No categories collected from Fanqie rank page")
    snapshot = _ensure_channel_source(snapshot, channel_config.key)
    write_raw_outputs(snapshot, config.output_root, channel_config.key)
    return snapshot


def run_pipeline(
    config: PipelineConfig,
    scraper=None,
) -> dict:
    collect_raw_report(config, scraper=scraper)
    return finalize_report_with_fallback_analysis(config.report_date, config.output_root, config.channel)


def finalize_report_with_fallback_analysis(
    report_date: str,
    output_root: Path = Path("."),
    channel: str = DEFAULT_CHANNEL,
) -> dict:
    channel_config = get_channel(channel)
    snapshot = load_raw_snapshot(output_root, report_date, channel_config.key)
    previous = load_previous_raw_snapshot(output_root, report_date, channel_config.key)
    trends = compare_snapshots(snapshot, previous)
    previous_date = previous.date if previous else ""
    source = {
        "rank": channel_config.rank_name,
        "channel": channel_config.key,
        "channel_label": channel_config.label,
        "collector": "Playwright raw snapshot",
        "analysis": "Local heuristic fallback",
    }
    return _write_final(snapshot, previous_date, trends, source, output_root, codex_market_summary=None, channel=channel_config.key)


def finalize_report_from_analysis(
    report_date: str,
    output_root: Path = Path("."),
    analysis_path: Path | None = None,
    channel: str = DEFAULT_CHANNEL,
) -> dict:
    channel_config = get_channel(channel)
    snapshot = load_raw_snapshot(output_root, report_date, channel_config.key)
    previous = load_previous_raw_snapshot(output_root, report_date, channel_config.key)
    trends = compare_snapshots(snapshot, previous)
    analysis_path = analysis_path or _data_dir(output_root, channel_config.key) / "analysis" / f"{report_date}.json"
    if not analysis_path.exists() and channel_config.legacy_root:
        legacy_path = output_root / "data" / "analysis" / f"{report_date}.json"
        if legacy_path.exists():
            analysis_path = legacy_path
    if not analysis_path.exists():
        raise FileNotFoundError(f"Analysis file not found: {analysis_path}")
    analysis = CodexAnalysis.from_dict(json.loads(analysis_path.read_text(encoding="utf-8")))
    validate_codex_analysis(analysis, snapshot)
    trends = apply_codex_analysis(trends, analysis)
    previous_date = previous.date if previous else ""
    source = {
        "rank": channel_config.rank_name,
        "channel": channel_config.key,
        "channel_label": channel_config.label,
        "collector": "Playwright raw snapshot",
        "analysis": analysis.source or "Codex scheduled automation",
    }
    return _write_final(snapshot, previous_date, trends, source, output_root, analysis.market_summary, channel=channel_config.key)


def _write_final(
    snapshot: RawSnapshot,
    previous_date: str,
    trends: dict,
    source: dict[str, str],
    output_root: Path,
    codex_market_summary: dict[str, str] | None,
    channel: str,
) -> dict:
    snapshot = _ensure_channel_source(snapshot, channel)
    write_raw_outputs(snapshot, output_root, channel)
    current_row = {
        "date": snapshot.date,
        "prev_date": previous_date,
        "source": source,
        "trends": trends,
    }
    existing_rows = load_trend_rows(output_root, channel)
    trend_rows = trend_rows_with_current(existing_rows, current_row)
    market_summary = build_market_summary(snapshot, trend_rows, source["analysis"], codex_market_summary)
    write_final_outputs(
        snapshot=snapshot,
        previous_date=previous_date,
        trends=trends,
        source=source,
        market_summary=market_summary,
        trend_rows=trend_rows,
        root=output_root,
        channel=channel,
    )
    return {
        "date": snapshot.date,
        "prev_date": previous_date,
        "source": source,
        "category_count": len(snapshot.categories),
        "book_count": sum(len(category.books) for category in snapshot.categories),
    }


def _ensure_channel_source(snapshot: RawSnapshot, channel: str) -> RawSnapshot:
    channel_config = get_channel(channel)
    source = dict(snapshot.source)
    source.setdefault("rank", channel_config.rank_name)
    source["channel"] = channel_config.key
    source["channel_label"] = channel_config.label
    if source == snapshot.source:
        return snapshot
    return replace(snapshot, source=source)


def load_raw_snapshot(root: Path, report_date: str, channel: str = DEFAULT_CHANNEL) -> RawSnapshot:
    channel_config = get_channel(channel)
    path = _data_dir(root, channel_config.key) / "raw" / f"{report_date}.json"
    if not path.exists() and channel_config.legacy_root:
        legacy_path = root / "data" / "raw" / f"{report_date}.json"
        if legacy_path.exists():
            path = legacy_path
    if not path.exists():
        raise FileNotFoundError(f"Raw snapshot not found: {path}")
    return RawSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))


def load_previous_raw_snapshot(root: Path, report_date: str, channel: str = DEFAULT_CHANNEL) -> RawSnapshot | None:
    channel_config = get_channel(channel)
    raw_dirs = [_data_dir(root, channel_config.key) / "raw"]
    if channel_config.legacy_root:
        raw_dirs.append(root / "data" / "raw")
    candidates = sorted({
        path
        for raw_dir in raw_dirs
        if raw_dir.exists()
        for path in raw_dir.glob("*.json")
        if path.stem != "latest" and path.stem < report_date
    }, key=lambda path: path.stem)
    if not candidates:
        return None
    return RawSnapshot.from_dict(json.loads(candidates[-1].read_text(encoding="utf-8")))


def load_trend_rows(root: Path, channel: str = DEFAULT_CHANNEL) -> list[dict]:
    channel_config = get_channel(channel)
    trend_dirs = []
    if channel_config.legacy_root:
        trend_dirs.append(root / "data" / "trends")
    trend_dirs.append(_data_dir(root, channel_config.key) / "trends")
    rows_by_date: dict[str, dict] = {}
    for trends_dir in trend_dirs:
        if not trends_dir.exists():
            continue
        for path in sorted(trends_dir.glob("*.json")):
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            rows_by_date[row.get("date") or path.stem] = row
    return [rows_by_date[date] for date in sorted(rows_by_date)]


def _data_dir(root: Path, channel: str) -> Path:
    return root / "data" / "channels" / channel
