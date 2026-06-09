from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from urllib.parse import quote

from .analysis import build_codex_context
from .models import RawSnapshot


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_raw_outputs(snapshot: RawSnapshot, root: Path) -> None:
    raw_dir = root / "data" / "raw"
    reports_dir = root / "reports" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    payload = snapshot.to_dict()
    write_json(raw_dir / f"{snapshot.date}.json", payload)
    write_json(raw_dir / "latest.json", payload)
    (reports_dir / f"{snapshot.date}.md").write_text(render_raw_markdown(snapshot), encoding="utf-8")


def write_final_outputs(
    snapshot: RawSnapshot,
    previous_date: str,
    trends: dict,
    source: dict[str, str],
    market_summary: dict,
    trend_rows: list[dict],
    root: Path,
) -> None:
    data_dir = root / "data"
    reports_dir = root / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    categories = []
    for category in snapshot.categories:
        trend = trends.get(category.name, {})
        categories.append({
            "name": category.name,
            "summary_markdown": trend.get("summary_markdown", ""),
            "hot_themes": trend.get("hot_themes", []),
            "watch_books": trend.get("watch_books", []),
            "risk_notes": trend.get("risk_notes", ""),
            "trend": trend,
            "books": [book.to_dict() for book in category.books],
        })
    latest_payload = {
        "date": snapshot.date,
        "prev_date": previous_date,
        "timezone": snapshot.timezone,
        "generated_at": snapshot.generated_at,
        "source": source,
        "categories": categories,
        "market_summary": market_summary,
    }

    write_json(data_dir / "latest_ranks.json", latest_payload)
    write_json(data_dir / "latest.json", latest_payload)
    write_json(data_dir / f"{snapshot.date}.json", latest_payload)
    write_json(data_dir / "market_summary.json", market_summary)
    write_json(data_dir / "dates.json", {"dates": _raw_dates(root)})
    write_json(data_dir / "trends" / f"{snapshot.date}.json", {
        "date": snapshot.date,
        "prev_date": previous_date,
        "source": source,
        "trends": trends,
    })
    write_json(data_dir / "codex_context" / f"{snapshot.date}.json", build_codex_context(snapshot, trends, market_summary))
    write_api_outputs(latest_payload, root)
    (reports_dir / f"{snapshot.date}.md").write_text(render_daily_markdown(latest_payload), encoding="utf-8")
    (root / "README.md").write_text(render_readme(latest_payload), encoding="utf-8")

    # Keep an index useful for quick automation sanity checks.
    write_json(data_dir / "trend_rows.json", {"rows": trend_rows})


def write_api_outputs(latest_payload: dict, root: Path) -> None:
    api_root = root / "api"
    lastest_dir = api_root / "lastest"
    lastest_dir.mkdir(parents=True, exist_ok=True)
    for path in lastest_dir.glob("*.json"):
        path.unlink()

    categories = latest_payload.get("categories", [])
    all_payload = {
        "type": "all",
        "date": latest_payload.get("date", ""),
        "prev_date": latest_payload.get("prev_date", ""),
        "timezone": latest_payload.get("timezone", ""),
        "source": latest_payload.get("source", {}),
        "categories": categories,
    }
    write_json(lastest_dir / "all.json", all_payload)

    used = {"all"}
    types = [{
        "type": "all",
        "url": "api/lastest/all.json",
        "category_count": len(categories),
        "book_count": sum(len(category.get("books", [])) for category in categories),
    }]
    for category in categories:
        type_name = category.get("name", "")
        filename = api_type_filename(type_name)
        base = filename
        index = 2
        while filename in used:
            filename = f"{base}_{index}"
            index += 1
        used.add(filename)
        payload = {
            "type": type_name,
            "date": latest_payload.get("date", ""),
            "prev_date": latest_payload.get("prev_date", ""),
            "timezone": latest_payload.get("timezone", ""),
            "source": latest_payload.get("source", {}),
            "category": category,
            "categories": [category],
        }
        write_json(lastest_dir / f"{filename}.json", payload)
        types.append({
            "type": type_name,
            "url": f"api/lastest/{quote(filename)}.json",
            "book_count": len(category.get("books", [])),
        })

    index_payload = {
        "date": latest_payload.get("date", ""),
        "prev_date": latest_payload.get("prev_date", ""),
        "types": types,
    }
    write_json(lastest_dir / "index.json", index_payload)
    write_json(api_root / "lastest.json", index_payload)


def api_type_filename(type_name: str) -> str:
    name = re.sub(r"[\\/]+", "_", str(type_name or "").strip())
    name = re.sub(r"[^\w\u4e00-\u9fff\s-]", "_", name)
    name = re.sub(r"\s+", "_", name).strip("._")
    return name or "unknown"


def render_readme(payload: dict) -> str:
    date = payload.get("date", "")
    timezone = payload.get("timezone", "Asia/Shanghai")
    analysis_source = payload.get("source", {}).get("analysis", "未知分析")
    lines = [
        "# 番茄男频新书榜风向标",
        "",
        "> 自动追踪番茄小说男频新书榜，生成分类排行、趋势对比和 Codex 深度分析。",
        "",
        f"## 最新榜单：{date} ({timezone})",
        "",
        f"- 分析来源：`{analysis_source}`",
        f"- 在线看板：启用 GitHub Pages 后访问 `https://Nossen.github.io/FanqieRank/`",
        "",
        render_summary_table(payload),
        "",
        "## 数据与归档",
        "",
        f"- 最新看板数据：[data/latest_ranks.json](data/latest_ranks.json)",
        f"- 最新 JSON：[data/latest.json](data/latest.json)",
        f"- Markdown 归档：[reports/{date}.md](reports/{date}.md)",
        "- 静态接口：[api/lastest.json](api/lastest.json)",
        "",
        "## 自动更新",
        "",
        "GitHub Actions 每天北京时间 16:10 后采集并发布规则兜底；Codex 定时任务每天 16:30 做深度分析、finalize、测试、提交并推送。",
        "",
        "## Attribution",
        "",
        "页面和采集思路参考 MIT 项目 [FanqieRankTracker](https://github.com/wen1701/FanqieRankTracker)，本项目改造为男频新书榜和 Codex 自动分析工作流。",
        "",
        "<!-- generated by fanqierank -->",
        "",
    ]
    return "\n".join(lines)


def render_daily_markdown(payload: dict) -> str:
    date = payload.get("date", "")
    source = payload.get("source", {})
    lines = [
        f"# 番茄男频新书榜 - {date}",
        "",
        f"- 时区：`{payload.get('timezone', 'Asia/Shanghai')}`",
        f"- 生成时间：`{payload.get('generated_at', '')}`",
        f"- 分析来源：`{source.get('analysis', '未知分析')}`",
        "",
        "## 分类概览",
        "",
        render_summary_table(payload),
        "",
        "## Codex/规则风向摘要",
        "",
        _render_market_markdown(payload.get("market_summary", {})),
        "",
        "## 分类详情",
        "",
        _render_category_cards(payload.get("categories", [])),
        "",
    ]
    return "\n".join(lines)


def render_raw_markdown(snapshot: RawSnapshot) -> str:
    lines = [
        f"# Raw Fanqie Male New Books - {snapshot.date}",
        "",
        f"- 时区：`{snapshot.timezone}`",
        f"- 生成时间：`{snapshot.generated_at}`",
        "- 说明：该文件是原始采集结果，最终展示由 fallback 或 Codex analysis finalize 生成。",
        "",
        "| 分类 | 书籍数 | Top 1 | 在读 |",
        "| --- | ---: | --- | ---: |",
    ]
    for category in snapshot.categories:
        top = category.books[0] if category.books else None
        lines.append(
            "| "
            f"{_escape_md(category.name)} | "
            f"{len(category.books)} | "
            f"{_escape_md(top.title if top else '无')} | "
            f"{_escape_md(top.reads if top else '-')} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_summary_table(payload: dict) -> str:
    lines = [
        "| 分类 | 书籍数 | 新上榜 | 掉榜 | 阅读增长焦点 | Top 1 |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for category in payload.get("categories", []):
        trend = category.get("trend", {})
        books = category.get("books", [])
        top = books[0] if books else {}
        growth = trend.get("reads_growth", [])
        focus = growth[0]["title"] if growth else "暂无"
        lines.append(
            "| "
            f"{_escape_md(category.get('name', ''))} | "
            f"{len(books)} | "
            f"{trend.get('new_count', 0)} | "
            f"{trend.get('dropped_count', 0)} | "
            f"{_escape_md(focus)} | "
            f"{_escape_md(top.get('title', '无'))} |"
        )
    return "\n".join(lines)


def _render_market_markdown(market_summary: dict) -> str:
    periods = market_summary.get("periods", {})
    if not periods:
        return "暂无全站热点数据。"
    labels = ["7", "14", "30", "all"]
    lines = []
    for key in labels:
        item = periods.get(key)
        if not item:
            continue
        lines.append(f"- **{item.get('period', key)}**：{item.get('summary', '')}")
    return "\n".join(lines)


def _render_category_cards(categories: list[dict]) -> str:
    sections: list[str] = []
    for category in categories:
        trend = category.get("trend", {})
        books = category.get("books", [])
        top_books = "、".join(f"《{book.get('title', '')}》" for book in books[:5]) or "无"
        sections.append(
            "\n".join(
                [
                    "---",
                    "",
                    "<details open>",
                    f"<summary><strong>{escape(category.get('name', '未知'))}</strong> · {len(books)} 本</summary>",
                    "",
                    f"- 新上榜：`{trend.get('new_count', 0)}`",
                    f"- 掉榜：`{trend.get('dropped_count', 0)}`",
                    f"- 热门题材：{_inline_tags(trend.get('hot_themes', []))}",
                    f"- 重点作品：{top_books}",
                    "",
                    trend.get("summary_markdown") or trend.get("summary") or "暂无分析。",
                    "",
                    "</details>",
                ]
            )
        )
    return "\n\n".join(sections)


def _raw_dates(root: Path) -> list[str]:
    raw_dir = root / "data" / "raw"
    if not raw_dir.exists():
        return []
    dates = []
    for path in raw_dir.glob("*.json"):
        if path.stem == "latest":
            continue
        if re.match(r"\d{4}-\d{2}-\d{2}$", path.stem):
            dates.append(path.stem)
    return sorted(dates)


def _inline_tags(tags: list[str]) -> str:
    if not tags:
        return "`待观察`"
    return " ".join(f"`{_escape_md(tag)}`" for tag in tags[:8])


def _escape_md(value: str) -> str:
    return str(value or "").replace("|", "\\|")
