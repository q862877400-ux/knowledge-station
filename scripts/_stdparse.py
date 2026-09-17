# -*- coding: utf-8 -*-
"""无副作用的共享模块：文件名 → 标准号/名称提取。供 program_compare / debug_loop_driver 复用。
不 rebind sys.stdout（避免该副作用在导入方引发 closed-file 异常）。"""
import re
from pathlib import Path

from src.core.text_utils import clean_standard_name

# 文件名标准号提取（与 std_bulk_import.py 一致；兼容全角斜杠 ／、GB/GBT/GBZ）
_STD_RE = re.compile(
    r"^(GB\s*(?:[／/]Z|Z)?\s*(?:[／/]?\s*T)?)\s*(\d+(?:\.\d+)*)\s*[-—–]\s*(\d{4})")


def derive_standard(pdf) -> tuple[str, str]:
    """从文件名提取 (standard_no, standard_name)。standard_no 归一位 ASCII（全角／→/，压缩空格）。

    ⚠ 2026-09-17 修：原实现先算出干净 `name`，**紧接着又用原始 `stem` 覆盖回去**
    （`name = stem.replace(std_no, "", 1)…`），把刚剥掉的副本后缀 `(1)` 又带回来了；
    且 `std_no` 是 ASCII `/` 而 stem 常是全角 `／`，那次 `replace` **根本不命中**。
    现统一走 `text_utils.clean_standard_name`（按"号 + 年"剥开头前缀，容忍全角与前缀族差异），
    保证派生结果与库里已有的 :139 行脏数据同口径、不会再灌出新的。
    """
    stem = Path(pdf).stem
    m = _STD_RE.match(stem)
    if not m:
        s2 = re.sub(r"\s*\([0-9]+\)\s*$", "", stem)
        m = _STD_RE.match(s2)
    std_no = ""
    if m:
        std_no = f"{m.group(1)}{m.group(2)}-{m.group(3)}"
        # 全角／→ASCII /，压缩连续空白
        std_no = re.sub(r"\s+", " ", std_no.replace("／", "/")).strip()
    return std_no, clean_standard_name(stem, standard_no=std_no or None)
