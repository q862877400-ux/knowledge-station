"""测试：子 source 的数据必须被归集到父通道（spec 005 T602）。

## 为什么（实测）

706 个有数据的 source 里 **393 个（121,762 条）不在销号表内** —— 因为
`counts` 的键是**数据文件里的 `source` 值**，而通道的键是 `c.key`：

| 形态 | 数据里的 source | 通道 key |
|---|---|---|
| IGI 系（368 个） | `sx-igi-24` | `sx-igi` |
| 天津 enorth（24 个） | `tj-enorth-wuqing` | `tj-enorth` |
| 辽宁知识库 | `ln-8890-kb` | `ln-8890` |

原来只 `counts.get(c.key, 0)` ⇒ 取到 0 ⇒ **那些数据在覆盖报表里隐形**。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from coverage import _count_for_channel                          # noqa: E402


def test_child_source_counts_into_parent():
    """`sx-igi-24` 的条数必须计入 `sx-igi`（**24 不是通道**，只是数据里的 source）。"""
    counts = {"sx-igi": 100, "sx-igi-24": 50, "sx-igi-32": 30}
    channel_keys = {"sx-igi"}                 # ← 只有父级是通道
    assert _count_for_channel("sx-igi", counts, channel_keys) == 180


def test_exact_key_still_works():
    """**反向用例**：没有子 source 时不得多算。"""
    counts = {"mee": 163, "mem": 60}
    assert _count_for_channel("mee", counts, {"mee", "mem"}) == 163


def test_longest_prefix_wins_no_double_count():
    """**关键**：`gx-igi` 与 `gx-igi-293` **都是通道**时，子 source 只能算一次。

    否则 `gx-igi-293-….jsonl` 会被两个通道都算 ⇒ 总量虚高。
    """
    counts = {"gx-igi": 10, "gx-igi-293": 7, "gx-igi-4": 5}
    channel_keys = {"gx-igi", "gx-igi-293"}   # ← 两个都是通道
    a = _count_for_channel("gx-igi", counts, channel_keys)
    b = _count_for_channel("gx-igi-293", counts, channel_keys)
    # gx-igi-293 自己是最长匹配 ⇒ 吃自己的 7；
    # gx-igi-4 只被 gx-igi 匹配 ⇒ 归 gx-igi
    assert a == 10 + 5, f"gx-igi 应吃自己 + gx-igi-4，实际 {a}"
    assert b == 7, f"gx-igi-293 应只算自己，实际 {b}"


def test_unrelated_prefix_is_not_swallowed():
    """**反向用例**：`mee` 不得吞掉 `meeting-notes` 这种无关键。"""
    counts = {"mee": 10, "meeting-notes": 99}
    assert _count_for_channel("mee", counts, {"mee"}) == 10


def test_real_corpus_has_no_unattributed_source():
    """**端到端**：真实语料里不应有「有数据但没有任何通道能归集它」的 source。

    实测修前有 393 个（121,762 条）。谁把归集逻辑改回 `counts.get(c.key, 0)`，
    这条必红。
    """
    from channel import load_channels
    from coverage import count_by_source, build_units
    channels = load_channels()
    counts = count_by_source()
    keys = {c.key for c in channels}
    has_data = {k for k, v in counts.items() if v > 0}

    def attributed(src: str) -> bool:
        return any(src == k or src.startswith(k + "-") for k in keys)

    orphans = [k for k in has_data if not attributed(k)]
    assert not orphans, f"这些有数据的 source 没被任何通道归集：{orphans[:10]}"
