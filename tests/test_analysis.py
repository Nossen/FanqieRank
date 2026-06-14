from __future__ import annotations

from fanqierank.analysis import parse_reads
from fanqierank.constants import CHANNELS, MALE_CATEGORIES


def test_parse_reads_supports_chinese_units() -> None:
    assert parse_reads("1.2万") == 12000
    assert parse_reads("2亿") == 200000000
    assert parse_reads("在读：3.5万") == 35000
    assert parse_reads("未知") == 0


def test_male_category_inventory_has_expected_size() -> None:
    assert len(MALE_CATEGORIES) == 19
    assert "都市脑洞" in MALE_CATEGORIES
    assert "男频衍生" in MALE_CATEGORIES


def test_channel_inventory_has_male_and_female() -> None:
    assert CHANNELS["male"].rank_prefix == "/rank/1_1_"
    assert CHANNELS["female"].init_url.endswith("/rank/0_1_1139")
