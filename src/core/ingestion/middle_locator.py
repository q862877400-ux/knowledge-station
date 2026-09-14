"""middle.json 产物定位的统一模式契约（2026-09-14 立）。

背景（执行报告 20260914 · OCR 循环轮次 1 实测）：MinerU 云产物 zip 已不再
携带 ``*_middle.json``，同构产物改名 ``layout.json``（batch 93f04cb7 实证）。
当时只修了 ``mineru_cloud._find_middle`` 一处；本循环第二轮入库即暴露
``run_full_ingest`` 里 ``rglob("*_middle.json")`` 硬编码不认 layout.json →
云通道 25s 成功返回的产物被误判「未找到 middle.json」。

普查全库共 3 处消费者硬编码（pipeline.run_full_ingest / middle_geo /
figure_locator）。本模块是这些模式的**单一所有者**：

- ``MIDDLE_PATTERNS``: middle 产物的文件名模式（老命名 → 新命名，按序）。
- ``iter_middle_files(root)``: 按序产出 root 下全部 middle 产物（防穿越）。

新命名出现时只改这里，不再散落三处。测试：tests/test_middle_locator.py。
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator, List

#: middle 产物文件名模式，按优先级排序。2026-09-14 云改名事件：zip 内裸名
#: layout.json，_normalize_landing 落位后为 <stem>_layout.json——两种形态都要认。
MIDDLE_PATTERNS: tuple[str, ...] = (
    "*_middle.json", "middle.json", "*_layout.json", "layout.json")


def iter_middle_files(root: Path) -> Iterator[Path]:
    """按 MIDDLE_PATTERNS 顺序产出 root 下的 middle 产物文件。

    模式内按路径排序保证稳定序；root 无效/不存在产出空。防穿越由调用方
    （middle_geo 有防穿越纪律，其余场景 root 本身可信）——本函数只做定位。
    """
    root = Path(root)
    if not root.is_dir():
        return
    seen: set[Path] = set()
    for pattern in MIDDLE_PATTERNS:
        for p in sorted(root.rglob(pattern)):
            rp = Path(p)
            if rp not in seen:
                seen.add(rp)
                yield rp


def find_middle_files(root: Path) -> List[Path]:
    """iter_middle_files 的列表版（多数消费者用列表）。"""
    return list(iter_middle_files(root))
