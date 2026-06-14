from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .constants import CODEX_MARKET_PERIODS, GENRE_GROUPS, MARKET_KEYWORDS
from .models import CodexAnalysis, RawSnapshot


def parse_reads(reads: str) -> float:
    value = str(reads or "").strip().replace(",", "")
    if not value or value == "未知":
        return 0
    for marker in ["在读：", "在读:", "在读"]:
        value = value.replace(marker, "")
    try:
        if "亿" in value:
            return float(value.replace("亿", "")) * 100_000_000
        if "万" in value:
            return float(value.replace("万", "")) * 10_000
        return float(value)
    except ValueError:
        return 0


def format_reads(value: float) -> str:
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.1f}亿"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.1f}万"
    return str(round(value))


def format_reads_change(value: float) -> str:
    prefix = "+" if value > 0 else ""
    return f"{prefix}{format_reads(value)}"


def compare_snapshots(current: RawSnapshot, previous: RawSnapshot | None) -> dict[str, dict[str, Any]]:
    if previous is None:
        return {
            category.name: {
                "new_count": 0,
                "dropped_count": 0,
                "new_books": [],
                "dropped_books": [],
                "top_risers": [],
                "top_fallers": [],
                "reads_growth": [],
                "summary": "首日数据，暂无趋势对比。",
                "summary_markdown": "首日数据，暂无趋势对比。",
                "hot_themes": [],
                "watch_books": [],
                "risk_notes": "",
            }
            for category in current.categories
        }

    previous_index: dict[str, dict[str, dict[str, Any]]] = {}
    for category in previous.categories:
        previous_index[category.name] = {
            book.url: {
                "rank": index + 1,
                "title": book.title,
                "reads": book.reads,
                "intro": book.intro,
            }
            for index, book in enumerate(category.books)
        }

    trends: dict[str, dict[str, Any]] = {}
    for category in current.categories:
        prev_books = previous_index.get(category.name, {})
        seen_urls: set[str] = set()
        new_books: list[str] = []
        dropped_books: list[dict[str, str]] = []
        risers: list[dict[str, str]] = []
        fallers: list[dict[str, str]] = []
        reads_growth: list[dict[str, str]] = []

        for index, book in enumerate(category.books):
            current_rank = index + 1
            seen_urls.add(book.url)
            prev = prev_books.get(book.url)
            if prev is None:
                new_books.append(book.title)
                continue

            rank_change = int(prev["rank"]) - current_rank
            if rank_change > 0:
                risers.append({"title": book.title, "change": f"+{rank_change}"})
            elif rank_change < 0:
                fallers.append({"title": book.title, "change": str(rank_change)})

            diff = parse_reads(book.reads) - parse_reads(str(prev.get("reads") or ""))
            if diff:
                reads_growth.append({"title": book.title, "growth": format_reads_change(diff)})

        for url, info in prev_books.items():
            if url not in seen_urls:
                dropped_books.append({
                    "title": str(info.get("title") or "未知"),
                    "intro": str(info.get("intro") or "暂无简介")[:120],
                })

        risers.sort(key=lambda item: int(item["change"].replace("+", "")), reverse=True)
        fallers.sort(key=lambda item: int(item["change"]))
        reads_growth.sort(key=lambda item: parse_reads(item["growth"]), reverse=True)

        trend = {
            "new_count": len(new_books),
            "dropped_count": len(dropped_books),
            "new_books": new_books[:8],
            "dropped_books": dropped_books[:8],
            "top_risers": risers[:5],
            "top_fallers": fallers[:5],
            "reads_growth": reads_growth[:5],
            "summary": "",
            "summary_markdown": "",
            "hot_themes": infer_category_themes(category.name, [book.to_dict() for book in category.books]),
            "watch_books": [book.title for book in category.books[:3]],
            "risk_notes": "",
        }
        trend["summary"] = build_rule_category_summary(category.name, trend)
        trend["summary_markdown"] = build_rule_category_markdown(category.name, trend)
        trends[category.name] = trend

    return trends


def infer_category_themes(category_name: str, books: list[dict[str, Any]], limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for book in books:
        text = f"{category_name} {book.get('title', '')} {book.get('intro', '')}"
        for keyword in MARKET_KEYWORDS:
            if keyword in text:
                counter[keyword] += 1
    return [name for name, _count in counter.most_common(limit)]


def build_rule_category_summary(category_name: str, trend: dict[str, Any]) -> str:
    parts: list[str] = []
    if trend.get("new_count"):
        parts.append(f"新增{trend['new_count']}本上榜")
    if trend.get("dropped_count"):
        parts.append(f"{trend['dropped_count']}本掉出榜单")
    if trend.get("top_risers"):
        item = trend["top_risers"][0]
        parts.append(f"《{item['title']}》排名上升{item['change']}位")
    if trend.get("reads_growth"):
        item = trend["reads_growth"][0]
        parts.append(f"《{item['title']}》在读变化{item['growth']}")
    if not parts:
        parts.append("榜单暂无明显波动")
    return f"{category_name}：" + "；".join(parts) + "。"


def build_rule_category_markdown(category_name: str, trend: dict[str, Any]) -> str:
    themes = "、".join(trend.get("hot_themes", [])[:5]) or "待观察"
    new_books = "、".join(f"《{title}》" for title in trend.get("new_books", [])[:4]) or "暂无"
    watch_books = "、".join(f"《{title}》" for title in trend.get("watch_books", [])[:3]) or "暂无"
    return "\n".join(
        [
            f"**题材趋势**：{category_name} 当前高频信号为 {themes}。",
            f"**读者爽点**：规则兜底显示读者仍偏好清晰目标、强设定和稳定更新带来的即时反馈。",
            f"**上榜变化**：{build_rule_category_summary(category_name, trend)}新上榜作品：{new_books}。",
            f"**值得关注**：优先观察 {watch_books} 的在读增速和后续排名稳定性。",
        ]
    )


def build_market_summary(
    latest: RawSnapshot,
    trends_by_date: list[dict[str, Any]],
    source: str,
    codex_market_summary: dict[str, str] | None = None,
) -> dict[str, Any]:
    periods: dict[str, Any] = {}
    for key in CODEX_MARKET_PERIODS:
        rows = trends_by_date if key == "all" else trends_by_date[-int(key):]
        hot_types = collect_hot_types(latest, rows)
        hot_genres = collect_hot_genres(hot_types)
        hot_themes = collect_hot_themes(latest, rows)
        label = "全部样本" if key == "all" else f"近 {key} 日"
        summary = (codex_market_summary or {}).get(key) or build_rule_market_text(label, hot_genres, hot_types, hot_themes)
        periods[key] = {
            "period": label,
            "source": "codex" if (codex_market_summary or {}).get(key) else "rule",
            "summary": summary,
            "hot_genres": hot_genres[:5],
            "hot_types": hot_types[:8],
            "hot_themes": hot_themes[:16],
        }
    return {
        "date": latest.date,
        "timezone": latest.timezone,
        "source": source,
        "periods": periods,
    }


def collect_hot_types(latest: RawSnapshot, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    categories = [category.name for category in latest.categories]
    result: list[dict[str, Any]] = []
    for name in categories:
        read_growth_total = 0.0
        read_count = 0
        new_count = 0
        dropped_count = 0
        active_days = 0
        for row in rows:
            trend = (row.get("trends") or {}).get(name)
            if not trend:
                continue
            reads_growth = trend.get("reads_growth", [])
            growth = sum(parse_reads(item.get("growth", "")) for item in reads_growth)
            read_growth_total += growth
            read_count += len(reads_growth)
            new_count += int(trend.get("new_count") or 0)
            dropped_count += int(trend.get("dropped_count") or 0)
            if growth or trend.get("new_count") or trend.get("dropped_count"):
                active_days += 1
        if read_growth_total <= 0 and new_count <= 0:
            continue
        result.append({
            "name": name,
            "read_growth_total": read_growth_total,
            "read_count": read_count,
            "new_count": new_count,
            "dropped_count": dropped_count,
            "active_days": active_days,
        })
    return sorted(result, key=lambda item: (item["read_growth_total"], item["new_count"]), reverse=True)


def collect_hot_genres(hot_types: list[dict[str, Any]]) -> list[dict[str, Any]]:
    type_map = {item["name"]: item for item in hot_types}
    result: list[dict[str, Any]] = []
    for group in GENRE_GROUPS:
        matched = [type_map[name] for name in group["categories"] if name in type_map]
        if not matched:
            continue
        read_growth_total = sum(item["read_growth_total"] for item in matched)
        new_count = sum(item["new_count"] for item in matched)
        if read_growth_total <= 0 and new_count <= 0:
            continue
        result.append({
            "name": group["name"],
            "categories": [item["name"] for item in matched],
            "read_growth_total": read_growth_total,
            "read_count": sum(item["read_count"] for item in matched),
            "new_count": new_count,
            "active_days": sum(item["active_days"] for item in matched),
        })
    return sorted(result, key=lambda item: (item["read_growth_total"], item["new_count"]), reverse=True)


def collect_hot_themes(latest: RawSnapshot, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    book_map = {
        book.title: book
        for category in latest.categories
        for book in category.books
    }
    category_by_title = {
        book.title: category.name
        for category in latest.categories
        for book in category.books
    }
    counts: dict[str, dict[str, Any]] = {
        keyword: {"name": keyword, "count": 0, "categories": set()}
        for keyword in MARKET_KEYWORDS
    }
    for row in rows:
        for category_name, trend in (row.get("trends") or {}).items():
            for title in trend.get("new_books", []):
                book = book_map.get(title)
                text = f"{title} {book.intro if book else ''}"
                for keyword in MARKET_KEYWORDS:
                    if keyword in text:
                        counts[keyword]["count"] += 1
                        counts[keyword]["categories"].add(category_by_title.get(title, category_name))
    result = []
    for item in counts.values():
        if item["count"] <= 0:
            continue
        result.append({
            "name": item["name"],
            "count": item["count"],
            "category_count": len(item["categories"]),
        })
    return sorted(result, key=lambda item: (item["count"], item["category_count"]), reverse=True)


def build_rule_market_text(
    label: str,
    hot_genres: list[dict[str, Any]],
    hot_types: list[dict[str, Any]],
    hot_themes: list[dict[str, Any]],
) -> str:
    top_genres = "、".join(item["name"] for item in hot_genres[:2])
    top_types = "、".join(item["name"] for item in hot_types[:3])
    top_themes = "、".join(item["name"] for item in hot_themes[:6])
    if not top_genres and not top_types:
        return f"{label}暂无足够趋势样本，先积累连续榜单后再判断频道风向。"
    return (
        f"{label}里，{top_genres or top_types} 的阅读增长和上榜波动更集中；"
        f"具体分类以 {top_types or '待观察'} 更活跃，题材关键词集中在 {top_themes or '强设定爽点'}。"
    )


def validate_codex_analysis(analysis: CodexAnalysis, snapshot: RawSnapshot) -> None:
    if analysis.date and analysis.date != snapshot.date:
        raise ValueError(f"Analysis date {analysis.date} does not match raw date {snapshot.date}")

    required_categories = {category.name for category in snapshot.categories}
    provided = {category.name for category in analysis.categories}
    missing = sorted(required_categories - provided)
    extra = sorted(provided - required_categories)
    if missing:
        raise ValueError(f"Missing Codex category analysis: {', '.join(missing)}")
    if extra:
        raise ValueError(f"Unknown Codex category analysis: {', '.join(extra)}")

    empty = [category.name for category in analysis.categories if not category.summary_markdown]
    if empty:
        raise ValueError(f"Empty Codex category summary: {', '.join(empty)}")

    missing_periods = [key for key in CODEX_MARKET_PERIODS if not analysis.market_summary.get(key)]
    if missing_periods:
        raise ValueError(f"Missing Codex market summary periods: {', '.join(missing_periods)}")


def apply_codex_analysis(trends: dict[str, dict[str, Any]], analysis: CodexAnalysis) -> dict[str, dict[str, Any]]:
    by_name = {category.name: category for category in analysis.categories}
    updated: dict[str, dict[str, Any]] = {}
    for name, trend in trends.items():
        item = by_name[name]
        merged = dict(trend)
        merged["summary"] = item.summary_markdown
        merged["summary_markdown"] = item.summary_markdown
        merged["hot_themes"] = item.hot_themes or merged.get("hot_themes", [])
        merged["watch_books"] = item.watch_books or merged.get("watch_books", [])
        merged["risk_notes"] = item.risk_notes
        updated[name] = merged
    return updated


def trend_rows_with_current(existing_rows: list[dict[str, Any]], current_row: dict[str, Any]) -> list[dict[str, Any]]:
    by_date = {row.get("date"): row for row in existing_rows if row.get("date")}
    by_date[current_row["date"]] = current_row
    return [by_date[key] for key in sorted(by_date)]


def build_codex_context(snapshot: RawSnapshot, trends: dict[str, dict[str, Any]], market_summary: dict[str, Any]) -> dict[str, Any]:
    channel = snapshot.source.get("channel", "male")
    channel_label = snapshot.source.get("channel_label", "男频")
    return {
        "channel": channel,
        "channel_label": channel_label,
        "date": snapshot.date,
        "timezone": snapshot.timezone,
        "instruction": (
            f"Generate data/channels/{channel}/analysis/YYYY-MM-DD.json for 番茄{channel_label}新书榜. "
            "Cover every category exactly once. "
            "Use category.summary_markdown with sections: 题材趋势, 读者爽点, 上榜变化, 值得关注作品. "
            "Provide market_summary for keys 7, 14, 30, all."
        ),
        "required_market_summary_keys": CODEX_MARKET_PERIODS,
        "categories": [
            {
                "name": category.name,
                "trend": trends.get(category.name, {}),
                "books": [book.to_dict() for book in category.books[:20]],
            }
            for category in snapshot.categories
        ],
        "market_summary": market_summary,
    }
