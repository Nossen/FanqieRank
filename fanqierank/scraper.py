from __future__ import annotations

import time
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from .constants import DEFAULT_CHANNEL, RANK_BASE_URL, TIMEZONE, get_channel
from .models import Book, CategorySnapshot, RawSnapshot

START_CODE = 58344
CHAR_SEQUENCE = [
    "D", "在", "主", "特", "家", "军", "然", "表", "场", "4", "要", "只", "v", "和", "?", "6", "别", "还", "g", "现",
    "儿", "岁", "?", "?", "此", "象", "月", "3", "出", "战", "工", "相", "o", "男", "直", "失", "世", "F", "都", "平",
    "文", "什", "V", "O", "将", "真", "T", "那", "当", "?", "会", "立", "些", "u", "是", "十", "张", "学", "气", "大",
    "爱", "两", "命", "全", "后", "东", "性", "通", "被", "1", "它", "乐", "接", "而", "感", "车", "山", "公", "了",
    "常", "以", "何", "可", "话", "先", "p", "i", "叫", "轻", "M", "士", "w", "着", "变", "尔", "快", "l", "个",
    "说", "少", "色", "里", "安", "花", "远", "7", "难", "师", "放", "t", "报", "认", "面", "道", "S", "?", "克",
    "地", "度", "I", "好", "机", "U", "民", "写", "把", "万", "同", "水", "新", "没", "书", "电", "吃", "像", "斯",
    "5", "为", "y", "白", "几", "日", "教", "看", "但", "第", "加", "候", "作", "上", "拉", "住", "有", "法", "r",
    "事", "应", "位", "利", "你", "声", "身", "国", "问", "马", "女", "他", "Y", "比", "父", "x", "A", "H", "N",
    "s", "X", "边", "美", "对", "所", "金", "活", "回", "意", "到", "z", "从", "j", "知", "又", "内", "因", "点",
    "Q", "三", "定", "8", "R", "b", "正", "或", "夫", "向", "德", "听", "更", "?", "得", "告", "并", "本", "q",
    "过", "记", "L", "让", "打", "f", "人", "就", "者", "去", "原", "满", "体", "做", "经", "K", "走", "如", "孩",
    "c", "G", "给", "使", "物", "?", "最", "笑", "部", "?", "员", "等", "受", "k", "行", "一", "条", "果", "动", "光",
    "门", "头", "见", "往", "自", "解", "成", "处", "天", "能", "于", "名", "其", "发", "总", "母", "的", "死", "手",
    "入", "路", "进", "心", "来", "h", "时", "力", "多", "开", "已", "许", "d", "至", "由", "很", "界", "n", "小",
    "与", "Z", "想", "代", "么", "分", "生", "口", "再", "妈", "望", "次", "西", "风", "种", "带", "J", "?", "实",
    "情", "才", "这", "?", "E", "我", "神", "格", "长", "觉", "间", "年", "眼", "无", "不", "亲", "关", "结", "0",
    "友", "信", "下", "却", "重", "己", "老", "2", "音", "字", "m", "呢", "明", "之", "前", "高", "P", "B", "目",
    "太", "e", "9", "起", "稜", "她", "也", "W", "用", "方", "子", "英", "每", "理", "便", "四", "数", "期", "中",
    "C", "外", "样", "a", "海", "们", "任",
]


def decode_text(text: str) -> str:
    result: list[str] = []
    for char in text or "":
        idx = ord(char) - START_CODE
        if 0 <= idx < len(CHAR_SEQUENCE):
            result.append(CHAR_SEQUENCE[idx])
        else:
            result.append(char)
    return "".join(result)


def scrape_male_new_rank(
    report_date: str | None = None,
    timezone: str = TIMEZONE,
    limit: int = 30,
    sleep_seconds: float = 3.0,
) -> RawSnapshot:
    return scrape_new_rank(
        channel=DEFAULT_CHANNEL,
        report_date=report_date,
        timezone=timezone,
        limit=limit,
        sleep_seconds=sleep_seconds,
    )


def scrape_new_rank(
    channel: str = DEFAULT_CHANNEL,
    report_date: str | None = None,
    timezone: str = TIMEZONE,
    limit: int = 30,
    sleep_seconds: float = 3.0,
) -> RawSnapshot:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required. Install with `pip install -e .` and run `playwright install chromium`.") from exc

    channel_config = get_channel(channel)
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    date_str = report_date or now.date().isoformat()
    categories: list[CategorySnapshot] = []

    with sync_playwright() as p:
        browser = _launch_browser(p)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.goto(channel_config.init_url, wait_until="load", timeout=20_000)
        page.wait_for_selector('a[href^="/page/"]', timeout=10_000)

        category_links = page.evaluate(
            f"""
            () => Array.from(document.querySelectorAll('a'))
                .filter(a => (a.getAttribute('href') || '').startsWith('{channel_config.rank_prefix}'))
                .map(a => ({{ name: a.innerText.trim(), href: a.getAttribute('href') }}))
                .filter(item => item.name && item.href)
            """
        )

        seen: set[str] = set()
        for category in category_links:
            name = decode_text(str(category["name"])).strip()
            href = str(category["href"])
            if not name or href in seen:
                continue
            seen.add(href)
            _load_category(page, href)
            books = [_book_from_payload(payload) for payload in _extract_books(page)[:limit]]
            categories.append(CategorySnapshot(name=name, books=books))
            time.sleep(sleep_seconds)

        browser.close()

    generated_at = datetime.now(dt_timezone.utc).isoformat().replace("+00:00", "Z")
    return RawSnapshot(
        date=date_str,
        timezone=timezone,
        generated_at=generated_at,
        source={
            "rank": channel_config.rank_name,
            "channel": channel_config.key,
            "channel_label": channel_config.label,
            "url": channel_config.init_url,
            "collector": "Playwright",
        },
        categories=categories,
    )


def _launch_browser(playwright):
    try:
        return playwright.chromium.launch(headless=True, channel="chrome")
    except Exception:
        return playwright.chromium.launch(headless=True)


def _load_category(page, href: str) -> None:
    try:
        page.locator(f"a[href='{href}']").first.click(timeout=5_000)
    except Exception:
        page.goto(f"{RANK_BASE_URL}{href}", wait_until="load", timeout=20_000)
    time.sleep(1.5)
    page.wait_for_selector('a[href^="/page/"]', timeout=10_000)
    for _ in range(3):
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        time.sleep(0.8)


def _extract_books(page) -> list[dict[str, str]]:
    return page.evaluate(
        """
        () => {
            const bookMap = new Map();
            const links = document.querySelectorAll('a[href^="/page/"]');
            links.forEach(link => {
                let container = link.parentElement;
                let depth = 0;
                while (container && depth < 7) {
                    if (container.querySelector('img') && container.innerText.includes('在读')) {
                        const href = link.getAttribute('href');
                        if (!bookMap.has(href)) bookMap.set(href, container);
                        break;
                    }
                    container = container.parentElement;
                    depth++;
                }
            });
            return Array.from(bookMap.values()).map(item => {
                const link = item.querySelector('a[href^="/page/"]');
                const img = item.querySelector('img');
                const lines = item.innerText.split('\\n').map(line => line.trim()).filter(Boolean);
                let title = img && img.getAttribute('alt') ? img.getAttribute('alt').trim() : '';
                if (!title && link) title = link.innerText.trim();
                let author = '';
                const authorNode = item.querySelector('.author, .author-name') || item.querySelector('a[href^="/author-page/"]');
                if (authorNode) author = authorNode.innerText.trim();
                if (!author && lines.length > 1) author = lines[1];
                const readsLine = lines.find(line => line.includes('在读')) || '未知';
                const introNode = item.querySelector('.intro, .abstract, .desc');
                let intro = introNode ? introNode.innerText.trim() : '';
                if (!intro) {
                    intro = lines
                        .filter(line => !line.includes('在读') && line !== title && line !== author && !/^\\d+$/.test(line))
                        .slice(1, 4)
                        .join(' ');
                }
                return {
                    title: title || '未知',
                    author: author || '未知',
                    reads: readsLine,
                    intro: intro || '暂无简介',
                    cover: img ? (img.getAttribute('src') || '') : '',
                    url: link ? (link.getAttribute('href') || '') : ''
                };
            });
        }
        """
    )


def _book_from_payload(payload: dict[str, str]) -> Book:
    reads = decode_text(payload.get("reads", "未知"))
    if "在读" in reads:
        reads = reads.split("在读", 1)[1].replace(":", "").replace("：", "").strip()
    url = payload.get("url", "")
    if url.startswith("/"):
        url = f"{RANK_BASE_URL}{url}"
    return Book(
        title=decode_text(payload.get("title", "未知")).strip() or "未知",
        author=decode_text(payload.get("author", "未知")).strip() or "未知",
        reads=reads or "未知",
        intro=decode_text(payload.get("intro", "暂无简介")).replace("\n", " ").strip() or "暂无简介",
        cover=payload.get("cover", ""),
        url=url,
    )
