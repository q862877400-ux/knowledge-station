"""测试：`SITE-REGISTRY.md` 的**通道台账表**（spec 004 T052 / M1）。

## 为什么要有这一条

M1 要求「每个来源登记**自报总量 + 上次落盘量**」。
`channel.py` 里 `Channel` 有 `watermark_type` / `self_reported_total` 字段，
但 `SITE-REGISTRY.md` **一个都没登记**（实测 `watermark_type` 0 命中）
⇒ 接手的人得逐个读代码才知道每个通道靠什么做增量。

本组用例钉住：**表存在、覆盖全部通道、且是脚本生成的（不许手改后不更新）**。
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))          # `channel` / `common` 在 tools/gov-qa/ 下
REGISTRY = ROOT / "SITE-REGISTRY.md"
GEN = ROOT / "recon" / "gen-channel-table.py"


def _load_gen():
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("gen_channel_table", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _table_rows(text: str) -> list:
    i, j = text.find("<!-- BEGIN CHANNEL-TABLE"), text.find("<!-- END CHANNEL-TABLE")
    if i < 0 or j < 0:
        return []
    return [ln for ln in text[i:j].splitlines() if ln.startswith("| `")]


def test_registry_has_a_generated_channel_table():
    """表必须存在且**覆盖全部通道**。"""
    from channel import load_channels
    text = REGISTRY.read_text(encoding="utf-8")
    rows = _table_rows(text)
    n_chan = len(load_channels())
    assert rows, "SITE-REGISTRY 里应有受管区块 `<!-- BEGIN CHANNEL-TABLE ... -->`"
    assert len(rows) == n_chan, (
        f"台账表 {len(rows)} 行，通道 {n_chan} 个 —— 必须一一对应")


def test_channel_table_registers_watermark_type():
    """**M1 判据**：每一行都要登记水位类型（增量靠什么）。"""
    text = REGISTRY.read_text(encoding="utf-8")
    rows = _table_rows(text)
    known = {"idset", "page", "since"}
    missing = []
    for ln in rows:
        cells = [c.strip() for c in ln.split("|")]
        wm = cells[4].strip("`")
        if wm not in known:
            missing.append((cells[1], wm))
    assert not missing, f"这些行的水位类型未登记或非法：{missing[:5]}"


def test_channel_table_is_up_to_date():
    """**结构判据**：表必须与脚本重算的结果一致（防手改后不更新）。

    这条是"表会漂移"的闸 —— 加了通道、改了 `self_reported_total`、
    或语料涨了，表就过期，本用例报红。
    """
    mod = _load_gen()
    old = REGISTRY.read_text(encoding="utf-8")
    assert mod.splice(old, mod.render()) == old, (
        "通道台账表已过期 —— 跑 `python tools/gov-qa/recon/gen-channel-table.py` 重生成")


def test_generator_preserves_everything_outside_the_block():
    """**关键反向判据**：生成器**只动受管区块**，区块外一个字不改。

    本仓有过教训（批量改文档时整体偏移一行、翻出未授权的 ID）
    ⇒ 必须自证"只动了想动的那一列"。
    """
    mod = _load_gen()
    old = "前言\n\n" + mod.BEGIN + "\n旧内容\n" + mod.END + "\n\n后记\n"
    new = mod.splice(old, mod.render())
    assert new.startswith("前言\n\n"), "区块之前的内容被动过"
    assert new.endswith("后记\n"), "区块之后的内容被动过"
