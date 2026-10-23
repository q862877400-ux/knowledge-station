# -*- coding: utf-8 -*-
"""测量与修复脚本的共享口径（**只放"必须一致"的东西**）。

## 为什么有这个文件（2026-10-23 统一化第四批）

两段代码在**两个脚本里逐字存在**，而且它们分叉会**直接让结论不可比**：

1. `chunk_text` —— 两把尺子（`measure-classical-chinese-segmentation.py` /
   `measure-cross-language-fts.py`）都用它把语料切块。原 docstring 自己写着
   「与另一把尺子逐字一致」。**两把尺子切法不同 ⇒ 两次测量的读数不可比**，
   而这类测量结论是要写进方案文档当依据的。
2. `db_stat` —— 两个修复脚本（`normalize-standard-no-slash.py` /
   `repair-missing-standard-no.py`）用它记录「写前/写后的库指纹」。
   **指纹口径不同 ⇒ 回滚清单没法自证「改的就是这些行、库也没被别的东西动过」**。

## 与 `_stdparse.py` 的分工

- `_stdparse.py`：文件名 → 标准号/名称（**派生规则**）
- 本文件：切块口径 / 库指纹（**测量与修复口径**）

两块都"必须全仓一致"，但来源不同，所以没合到一个文件里。

## 副作用约束

本模块**无副作用**：不 rebind `sys.stdout`、不建目录、不连库。
理由同 `_stdparse.py` 抬头：脚本被 import 时不该改变调用方的 IO 行为。
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path


def chunk_text(text: str, size: int = 1000) -> list[str]:
    """按空行切段，再把相邻段拼到约 `size` 字；**不跨段切断**。

    为什么按空行而不按字符硬切：语料是标准/法规正文，硬切会把一句话劈成两半，
    半句话进检索会让「这句话能不能被召回」的测量失真。

    Args:
        text: 原文（`\\r\\n` 会被归一成 `\\n`）。
        size: 每块的目标字数上限。段落本身超长时**整段成一块**（不切）。

    Returns:
        切好的文本块列表；空输入返回空列表。

    Note:
        这个函数是**测量口径**：改变它必须同时重跑所有引用它的尺子，
        否则新旧读数不可比。
    """
    paras = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
    out: list[str] = []
    buf = ""
    for p in paras:
        if not p:
            continue
        if len(buf) + len(p) + 2 > size and buf:
            out.append(buf)
            buf = p
        else:
            buf = (buf + "\n\n" + p) if buf else p
    if buf:
        out.append(buf)
    return out


def db_stat() -> dict:
    """当前生产库的 `(路径, 大小, mtime, sha256)`。

    ## 为什么必须有它（复核 b31 的收尾建议）

    **"可回滚"不能只是口头承诺**：回滚清单必须逐行记 `doc_id → 原值`，
    并且**带上写前/写后的库指纹** —— 否则事后无法证明「改的就是这些行、
    库也没被别的东西动过」。

    ## 分块大小是 4 MiB

    比 `file_digest.CHUNK_SIZE`（64 KiB）大，因为这里读的是 2.9 GB 的单文件库，
    块太小会让 `read()` 调用次数成为主要开销。**这个值也是历史回滚记录的契约**，
    改了会让旧指纹对不上。

    Returns:
        `{"path", "size", "mtime", "sha256"}`；`mtime` 是秒级 ISO 串。
    """
    from src.core.config import get_settings  # 函数内导入：保持模块无副作用

    p = Path(get_settings().db_path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return {
        "path": str(p),
        "size": p.stat().st_size,
        "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
        "sha256": h.hexdigest(),
    }
