"""检查器的共用小工具。

## 为什么有这个文件（2026-10-24 尺子抓到我自己）

把「检查」拆成 `05-deep.py` 与 `06-content.py` 时，我把 `first_sentence`
**各写了一份**。尺子当场判红（跨文件同函数体 8 → **9** 组）——
正是我在别处反复指出的那个毛病，这次犯在自己身上。

⇒ 合并到这里，两个脚本都 `from _common import first_sentence`。

## 注意 import 路径

`scripts/survey/` 不是包（没有 `__init__.py`）。`run-all.py` 用
`python scripts/survey/xx.py` 启动，那时 `sys.path[0]` 就是 `scripts/survey/`，
所以 `from _common import ...` 能直接用。
"""
from __future__ import annotations

import json
from pathlib import Path


def first_sentence(doc: str, limit: int = 160) -> str:
    """取 docstring / 说明文字的第一句。

    Args:
        doc: 原文（可能是多行 docstring）。
        limit: 返回字符串上限（按字符，不按显示宽度）。

    Returns:
        第一句（补上中文句号）。空输入返回空串。

    Note:
        - 跳过 `#` 开头的标题行（很多模块 docstring 第一行是标题）；
        - 按 `。` / `；` / 换行切；
        - **不压缩、不改写** —— 这一层只做「搬运」，概括是下一棒的事。
    """
    if not doc:
        return ""
    lines = [ln for ln in doc.strip().splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        return ""
    text = lines[0].strip()
    for sep in ("。", "；", "\n"):
        if sep in text:
            text = text.split(sep)[0]
    if text and not text.endswith("。"):
        text += "。"
    return text[:limit]


def dump(name: str, payload: dict, data_dir=None) -> None:
    """把一份机器可读数据写进 `docs/survey/data/<name>.json`。

    参数:
        name: 文件名（不含 `.json`）。
        payload: 要写的字典。
        data_dir: 输出目录；默认 `<仓根>/docs/survey/data`。

    Note:
        这是两个检查脚本共用的写法。第一版我在 `05-deep.py` 与 `06-content.py`
        各写了一份，被尺子当场判成一组跨文件同函数体（8 → 9）。
    """
    root = Path(__file__).resolve().parents[2]
    d = data_dir or (root / "docs" / "survey" / "data")
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  → {p.relative_to(root)}  ({len(json.dumps(payload)) // 1024} KB)")
