from __future__ import annotations

import json
from dataclasses import dataclass
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
from .constants import TIMEZONE
from .models import CodexAnalysis, RawSnapshot
from .renderer import write_final_outputs, write_raw_outputs
from .scraper import scrape_male_new_rank


@dataclass(frozen=True)
class PipelineConfig:
    report_date: str
    timezone: str = TIMEZONE
    output_root: Path = Path(".")
    limit: int = 30
    sleep_seconds: float = 3.0


def today_in_timezone(timezone: str = TIMEZONE) -> str:
    return datetime.now(ZoneInfo(timezone)).date().isoformat()


def collect_raw_report(
    config: PipelineConfig,
    scraper=None,
) -> RawSnapshot:
    scraper = scraper or scrape_male_new_rank
    snapshot = scraper(
        report_date=config.report_date,
        timezone=config.timezone,
        limit=config.limit,
        sleep_seconds=config.sleep_seconds,
    )
    if not snapshot.categories:
        raise RuntimeError("No categories collected from Fanqie rank page")
    write_raw_outputs(snapshot, config.output_root)
    return snapshot


def run_pipeline(
    config: PipelineConfig,
    scraper=None,
) -> dict:
    collect_raw_report(config, scraper=scraper)
    return finalize_report_with_fallback_analysis(config.report_date, config.output_root)


def finalize_report_with_fallback_analysis(
    report_date: str,
    output_root: Path = Path("."),
) -> dict:
    snapshot = load_raw_snapshot(output_root, report_date)
    previous = load_previous_raw_snapshot(output_root, report_date)
    trends = compare_snapshots(snapshot, previous)
    previous_date = previous.date if previous else ""
    source = {
        "rank": "Fanqie male new-book rank",
        "collector": "Playwright raw snapshot",
        "analysis": "Local heuristic fallback",
    }
    return _write_final(snapshot, previous_date, trends, source, output_root, codex_market_summary=None)


def finalize_report_from_analysis(
    report_date: str,
    output_root: Path = Path("."),
    analysis_path: Path | None = None,
) -> dict:
    snapshot = load_raw_snapshot(output_root, report_date)
    previous = load_previous_raw_snapshot(output_root, report_date)
    trends = compare_snapshots(snapshot, previous)
    analysis_path = analysis_path or output_root / "data" / "analysis" / f"{report_date}.json"
    if not analysis_path.exists():
        raise FileNotFoundError(f"Analysis file not found: {analysis_path}")
    analysis = CodexAnalysis.from_dict(json.loads(analysis_path.read_text(encoding="utf-8")))
    validate_codex_analysis(analysis, snapshot)
    trends = apply_codex_analysis(trends, analysis)
    previous_date = previous.date if previous else ""
    source = {
        "rank": "Fanqie male new-book rank",
        "collector": "Playwright raw snapshot",
        "analysis": analysis.source or "Codex scheduled automation",
    }
    return _write_final(snapshot, previous_date, trends, source, output_root, analysis.market_summary)


def _write_final(
    snapshot: RawSnapshot,
    previous_date: str,
    trends: dict,
    source: dict[str, str],
    output_root: Path,
    codex_market_summary: dict[str, str] | None,
) -> dict:
    current_row = {
        "date": snapshot.date,
        "prev_date": previous_date,
        "source": source,
        "trends": trends,
    }
    existing_rows = load_trend_rows(output_root)
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
    )
    return {
        "date": snapshot.date,
        "prev_date": previous_date,
        "source": source,
        "category_count": len(snapshot.categories),
        "book_count": sum(len(category.books) for category in snapshot.categories),
    }


def load_raw_snapshot(root: Path, report_date: str) -> RawSnapshot:
    path = root / "data" / "raw" / f"{report_date}.json"
    if not path.exists():
        raise FileNotFoundError(f"Raw snapshot not found: {path}")
    return RawSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))


def load_previous_raw_snapshot(root: Path, report_date: str) -> RawSnapshot | None:
    raw_dir = root / "data" / "raw"
    if not raw_dir.exists():
        return None
    candidates = sorted(
        path for path in raw_dir.glob("*.json")
        if path.stem != "latest" and path.stem < report_date
    )
    if not candidates:
        return None
    return RawSnapshot.from_dict(json.loads(candidates[-1].read_text(encoding="utf-8")))


def load_trend_rows(root: Path) -> list[dict]:
    trends_dir = root / "data" / "trends"
    if not trends_dir.exists():
        return []
    rows: list[dict] = []
    for path in sorted(trends_dir.glob("*.json")):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return rows
