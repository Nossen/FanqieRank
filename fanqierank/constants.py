from __future__ import annotations

from dataclasses import dataclass

RANK_BASE_URL = "https://fanqienovel.com"
TIMEZONE = "Asia/Shanghai"
DEFAULT_CHANNEL = "male"
ALL_CHANNELS = "all"


@dataclass(frozen=True)
class ChannelConfig:
    key: str
    label: str
    rank_name: str
    init_url: str
    rank_prefix: str
    legacy_root: bool = False


CHANNELS = {
    "male": ChannelConfig(
        key="male",
        label="男频",
        rank_name="Fanqie male new-book rank",
        init_url=f"{RANK_BASE_URL}/rank/1_1_1141",
        rank_prefix="/rank/1_1_",
        legacy_root=True,
    ),
    "female": ChannelConfig(
        key="female",
        label="女频",
        rank_name="Fanqie female new-book rank",
        init_url=f"{RANK_BASE_URL}/rank/0_1_1139",
        rank_prefix="/rank/0_1_",
    ),
}

MALE_NEW_RANK_PREFIX = CHANNELS["male"].rank_prefix
FEMALE_NEW_RANK_PREFIX = CHANNELS["female"].rank_prefix
DEFAULT_INIT_URL = CHANNELS["male"].init_url
SNAPSHOT_PREFIX = "fanqie_male_new_ranks"

MALE_CATEGORIES = [
    "西方奇幻",
    "东方仙侠",
    "科幻末世",
    "都市日常",
    "都市修真",
    "都市高武",
    "历史古代",
    "战神赘婿",
    "都市种田",
    "传统玄幻",
    "历史脑洞",
    "悬疑脑洞",
    "都市脑洞",
    "玄幻脑洞",
    "悬疑灵异",
    "抗战谍战",
    "游戏体育",
    "动漫衍生",
    "男频衍生",
]

GENRE_GROUPS = [
    {"name": "玄幻仙侠", "categories": ["东方仙侠", "传统玄幻", "玄幻脑洞", "西方奇幻"]},
    {"name": "都市爽文", "categories": ["都市日常", "都市修真", "都市高武", "都市脑洞", "战神赘婿", "都市种田"]},
    {"name": "历史军事", "categories": ["历史古代", "历史脑洞", "抗战谍战"]},
    {"name": "科幻末世", "categories": ["科幻末世"]},
    {"name": "悬疑灵异", "categories": ["悬疑脑洞", "悬疑灵异"]},
    {"name": "衍生同人", "categories": ["动漫衍生", "男频衍生"]},
    {"name": "游戏体育", "categories": ["游戏体育"]},
    {"name": "古言宫斗", "categories": ["古风世情", "宫斗宅斗", "古言脑洞", "民国言情"]},
    {"name": "现言甜宠", "categories": ["现言脑洞", "青春甜宠", "豪门总裁", "职场婚恋", "星光璀璨"]},
    {"name": "女频幻想", "categories": ["玄幻言情", "快穿", "女频衍生", "女频悬疑"]},
    {"name": "年代种田", "categories": ["种田", "年代"]},
]

MARKET_KEYWORDS = [
    "系统",
    "无敌",
    "修仙",
    "仙侠",
    "玄幻",
    "脑洞",
    "高武",
    "都市",
    "神豪",
    "赘婿",
    "战神",
    "种田",
    "历史",
    "穿越",
    "重生",
    "架空",
    "争霸",
    "抗战",
    "谍战",
    "末世",
    "科幻",
    "异能",
    "天灾",
    "灵气复苏",
    "诡异",
    "悬疑",
    "灵异",
    "无限流",
    "诸天",
    "万界",
    "副本",
    "游戏",
    "体育",
    "足球",
    "篮球",
    "动漫",
    "同人",
    "衍生",
    "领主",
    "巫师",
    "西幻",
    "多女主",
    "单女主",
    "无女主",
    "杀伐果断",
    "幕后",
    "反派",
    "签到",
    "模拟器",
    "御兽",
    "国运",
    "直播",
    "古言",
    "现言",
    "甜宠",
    "宫斗",
    "宅斗",
    "快穿",
    "豪门",
    "总裁",
    "婚恋",
    "职场",
    "年代",
    "女强",
    "团宠",
    "虐渣",
    "萌宝",
    "娱乐圈",
    "星光",
    "民国",
]

CODEX_MARKET_PERIODS = ["7", "14", "30", "all"]


def get_channel(channel: str | None) -> ChannelConfig:
    key = channel or DEFAULT_CHANNEL
    if key not in CHANNELS:
        raise ValueError(f"Unknown channel: {channel}")
    return CHANNELS[key]


def expand_channels(channel: str | None) -> list[ChannelConfig]:
    key = channel or DEFAULT_CHANNEL
    if key == ALL_CHANNELS:
        return [CHANNELS["male"], CHANNELS["female"]]
    return [get_channel(key)]
