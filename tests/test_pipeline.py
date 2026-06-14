from __future__ import annotations

import json
from pathlib import Path

import pytest

from fanqierank.cli import main
from fanqierank.models import Book, CategorySnapshot, RawSnapshot
from fanqierank.pipeline import (
    PipelineConfig,
    collect_raw_report,
    finalize_report_from_analysis,
    finalize_report_with_fallback_analysis,
)


def make_snapshot(report_date: str, reads_offset: int = 0) -> RawSnapshot:
    return RawSnapshot(
        date=report_date,
        timezone="Asia/Shanghai",
        generated_at=f"{report_date}T08:30:00Z",
        source={"rank": "Fanqie male new-book rank", "collector": "test"},
        categories=[
            CategorySnapshot(
                name="都市脑洞",
                books=[
                    Book("系统让我当神豪", "作者甲", f"{10 + reads_offset}万", "都市 系统 神豪 爽文", "", "https://fanqienovel.com/page/1001"),
                    Book("重生高武时代", "作者乙", f"{6 + reads_offset}万", "高武 重生 升级", "", "https://fanqienovel.com/page/1002"),
                ],
            ),
            CategorySnapshot(
                name="东方仙侠",
                books=[
                    Book("剑开万界", "作者丙", f"{8 + reads_offset}万", "修仙 万界 杀伐果断", "", "https://fanqienovel.com/page/2001"),
                    Book("我在宗门签到", "作者丁", f"{5 + reads_offset}万", "签到 无敌 修仙", "", "https://fanqienovel.com/page/2002"),
                ],
            ),
        ],
    )


def fake_scraper(channel: str, report_date: str, timezone: str, limit: int, sleep_seconds: float) -> RawSnapshot:
    assert channel == "male"
    assert timezone == "Asia/Shanghai"
    assert limit == 30
    assert sleep_seconds == 0
    return make_snapshot(report_date)


def fake_female_scraper(channel: str, report_date: str, timezone: str, limit: int, sleep_seconds: float) -> RawSnapshot:
    assert channel == "female"
    return RawSnapshot(
        date=report_date,
        timezone=timezone,
        generated_at=f"{report_date}T08:30:00Z",
        source={"rank": "Fanqie female new-book rank", "channel": "female", "channel_label": "女频", "collector": "test"},
        categories=[
            CategorySnapshot(
                name="古风世情",
                books=[
                    Book("穿越朱门", "作者甲", "12万", "古言 宫斗 女强", "", "https://fanqienovel.com/page/3001"),
                ],
            )
        ],
    )


def write_raw(root: Path, snapshot: RawSnapshot) -> None:
    path = root / "data" / "raw" / f"{snapshot.date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot.to_dict(), ensure_ascii=False), encoding="utf-8")


def test_collect_raw_report_writes_raw_json_and_markdown(tmp_path: Path) -> None:
    snapshot = collect_raw_report(
        PipelineConfig("2026-06-09", output_root=tmp_path, sleep_seconds=0),
        scraper=fake_scraper,
    )

    assert snapshot.date == "2026-06-09"
    assert snapshot.source["channel"] == "male"
    assert (tmp_path / "data" / "channels" / "male" / "raw" / "2026-06-09.json").exists()
    assert (tmp_path / "data" / "raw" / "2026-06-09.json").exists()
    assert (tmp_path / "data" / "raw" / "latest.json").exists()
    assert (tmp_path / "reports" / "male" / "raw" / "2026-06-09.md").exists()


def test_fallback_finalize_writes_frontend_json_api_and_reports(tmp_path: Path) -> None:
    write_raw(tmp_path, make_snapshot("2026-06-08", reads_offset=0))
    write_raw(tmp_path, make_snapshot("2026-06-09", reads_offset=1))

    result = finalize_report_with_fallback_analysis("2026-06-09", tmp_path)

    assert result["category_count"] == 2
    latest = json.loads((tmp_path / "data" / "channels" / "male" / "latest_ranks.json").read_text(encoding="utf-8"))
    legacy_latest = json.loads((tmp_path / "data" / "latest_ranks.json").read_text(encoding="utf-8"))
    assert latest["source"]["analysis"] == "Local heuristic fallback"
    assert legacy_latest["channel"] == "male"
    assert latest["categories"][0]["trend"]["reads_growth"][0]["growth"] == "+1.0万"
    assert (tmp_path / "api" / "channels" / "male" / "lastest" / "all.json").exists()
    channel_index = json.loads((tmp_path / "api" / "channels" / "male" / "lastest" / "index.json").read_text(encoding="utf-8"))
    assert channel_index["types"][0]["url"] == "api/channels/male/lastest/all.json"
    assert (tmp_path / "api" / "lastest" / "all.json").exists()
    assert (tmp_path / "reports" / "male" / "2026-06-09.md").exists()
    assert "番茄新书榜风向标" in (tmp_path / "README.md").read_text(encoding="utf-8")


def test_female_channel_writes_only_channel_outputs(tmp_path: Path) -> None:
    snapshot = collect_raw_report(
        PipelineConfig("2026-06-09", output_root=tmp_path, sleep_seconds=0, channel="female"),
        scraper=fake_female_scraper,
    )

    assert snapshot.source["channel"] == "female"
    result = finalize_report_with_fallback_analysis("2026-06-09", tmp_path, "female")

    assert result["source"]["channel"] == "female"
    latest = json.loads((tmp_path / "data" / "channels" / "female" / "latest_ranks.json").read_text(encoding="utf-8"))
    assert latest["channel_label"] == "女频"
    assert latest["categories"][0]["name"] == "古风世情"
    channel_index = json.loads((tmp_path / "api" / "channels" / "female" / "lastest" / "index.json").read_text(encoding="utf-8"))
    assert channel_index["types"][0]["url"] == "api/channels/female/lastest/all.json"
    assert not (tmp_path / "data" / "latest_ranks.json").exists()


def test_codex_finalize_requires_every_category_and_writes_codex_source(tmp_path: Path) -> None:
    write_raw(tmp_path, make_snapshot("2026-06-08", reads_offset=0))
    write_raw(tmp_path, make_snapshot("2026-06-09", reads_offset=1))
    analysis_dir = tmp_path / "data" / "analysis"
    analysis_dir.mkdir(parents=True)
    analysis_path = analysis_dir / "2026-06-09.json"
    analysis_path.write_text(
        json.dumps(
            {
                "date": "2026-06-09",
                "source": "Codex scheduled automation",
                "categories": [
                    {
                        "name": "都市脑洞",
                        "summary_markdown": "**题材趋势**：系统神豪增强。\n**读者爽点**：强反馈。\n**上榜变化**：在读增长。\n**值得关注**：《系统让我当神豪》。",
                        "hot_themes": ["系统", "神豪"],
                        "watch_books": ["系统让我当神豪"],
                        "risk_notes": "同质化较高",
                    },
                    {
                        "name": "东方仙侠",
                        "summary_markdown": "**题材趋势**：万界修仙增强。\n**读者爽点**：升级与无敌。\n**上榜变化**：在读增长。\n**值得关注**：《剑开万界》。",
                        "hot_themes": ["修仙", "无敌"],
                        "watch_books": ["剑开万界"],
                        "risk_notes": "需要观察留存",
                    },
                ],
                "market_summary": {
                    "7": "近 7 日都市脑洞和东方仙侠活跃。",
                    "14": "近 14 日系统、修仙题材集中。",
                    "30": "近 30 日强设定爽点稳定。",
                    "all": "全部样本显示男频新书偏强设定。",
                },
                "hot_themes": ["系统", "修仙"],
                "watch_books": [{"title": "系统让我当神豪", "category": "都市脑洞", "reason": "增速领先"}],
                "risk_notes": "部分题材同质化。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = finalize_report_from_analysis("2026-06-09", tmp_path)

    assert result["source"]["analysis"] == "Codex scheduled automation"
    latest = json.loads((tmp_path / "data" / "channels" / "male" / "latest_ranks.json").read_text(encoding="utf-8"))
    assert latest["source"]["analysis"] == "Codex scheduled automation"
    assert latest["categories"][0]["trend"]["hot_themes"] == ["系统", "神豪"]
    assert latest["market_summary"]["periods"]["7"]["source"] == "codex"


def test_codex_finalize_fails_when_category_missing(tmp_path: Path) -> None:
    write_raw(tmp_path, make_snapshot("2026-06-09"))
    analysis_dir = tmp_path / "data" / "analysis"
    analysis_dir.mkdir(parents=True)
    (analysis_dir / "2026-06-09.json").write_text(
        json.dumps({
            "date": "2026-06-09",
            "categories": [{"name": "都市脑洞", "summary_markdown": "ok"}],
            "market_summary": {"7": "a", "14": "b", "30": "c", "all": "d"},
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing Codex category analysis"):
        finalize_report_from_analysis("2026-06-09", tmp_path)


def test_cli_fallback_finalize(tmp_path: Path) -> None:
    write_raw(tmp_path, make_snapshot("2026-06-09"))

    exit_code = main(["fallback-finalize", "--date", "2026-06-09", "--output", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "data" / "channels" / "male" / "latest.json").exists()
