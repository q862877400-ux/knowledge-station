# -*- coding: utf-8 -*-
"""P0·0.10 尺子（`eval/recall-funnel/exp-12-long-clause-tail/measure.py`）的单测。

**为什么必须测**（不是形式主义）：这把尺子上的判据各自都有一条**很容易踩回去**的坑：

1. **head/tail 必须按"字符"切在 512，不是按 token** —— 生产是在**代码层**
   `content_text[:512]`（`clause_repo.py:285`/`:426`）截断的，模型窗口（512 token）是**第二道**。
   两道的口径混了，量出来的"尾巴"就不是生产里真的丢的那一段。
   判据见 `test_head_tail_split_is_512_chars` + `test_production_still_uses_the_512_char_cap`。
2. **`tail_only` 必须同时扣掉 head 与 title 的词** —— 送进嵌入的是 `f"{title}\n{content_text[:512]}"`，
   title 也在向量里；只扣 head 会把 title 里的词误判成"尾巴独有"。
   判据见 `test_tail_only_excludes_head_and_title`。
3. **"丢掉多少 token"必须拆成两段**（去掉代码上限能白捡的 `gain` + 模型窗口仍挡的 `residual`），
   否则会把"代码上限"的账算到"模型窗口"头上 —— 这两者的修法完全不同。
   判据见 `test_token_drop_partition_adds_up`。

⚠ 本文件**不测** `main()`（要真库 + 分词器，几十秒），只测判据所依赖的**纯函数**。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "eval" / "recall-funnel" / "exp-12-long-clause-tail" / "measure.py"
CLAUSE_REPO = REPO / "src" / "core" / "storage" / "clause_repo.py"


def _load():
    spec = importlib.util.spec_from_file_location("ks_long_clause_tail_ruler", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


RULER = _load()


def test_head_tail_split_is_512_chars():
    """按字符切在 512：短于 512 ⇒ tail 为空；长于 ⇒ tail 正好是第 512 字符之后。"""
    text = "甲" * 600
    head, tail = RULER.split_head_tail(text)
    assert len(head) == 512 and len(tail) == 88
    short = "乙" * 100
    assert RULER.split_head_tail(short) == (short, "")
    assert RULER.HEAD_CHARS == 512


def test_production_still_uses_the_512_char_cap():
    """★ 契约锚：尺子的 512 必须**真的**对应生产代码里的截断点。

    若有人把 `clause_repo.py` 的 `content_text[:512]` 改了（比如去掉上限），
    这把尺子量出来的"尾巴"就不再是生产里丢的那一段 ⇒ 本测试要变红提醒。
    """
    src = CLAUSE_REPO.read_text(encoding="utf-8")
    assert f"content_text[:{RULER.HEAD_CHARS}]" in src, (
        f"生产 `clause_repo.py` 里找不到 `content_text[:{RULER.HEAD_CHARS}]` —— "
        "截断点变了，尺子的口径要同步改")


def test_tail_only_excludes_head_and_title():
    """`tail_only` = tail 词 − head 词 − title 词（title 也在向量里，必须一起扣）。"""
    # head 段（前 512 字）只含"苹果"，tail 段含"香蕉"；title 含"橘子"
    text = "苹果" * 300 + "香蕉" * 50          # 600 + 100 = 700 字
    t_only = RULER.tail_only_words(text, "橘子")
    assert "香蕉" in t_only
    assert "苹果" not in t_only
    # title 里的词若只出现在 tail，也必须被扣掉（因为 title 进了向量）
    text2 = "苹果" * 300 + "橘子" * 5
    assert "橘子" not in RULER.tail_only_words(text2, "橘子")


def test_token_drop_partition_adds_up():
    """★ 两段账：`gain`（去掉代码上限能白捡）+ `residual`（模型窗口仍挡）= 总丢量。"""
    # full 599 > window 512 > head 411：gain=101、residual=87，合计 188 = 599-411
    g, r = RULER.token_drop_partition(599, 411, 512)
    assert (g, r) == (101, 87)
    assert g + r == 599 - 411
    # 全文没超窗口（full 400 < 512）⇒ 一段都不丢
    assert RULER.token_drop_partition(400, 400, 512) == (0, 0)
    # head 恰好到窗口：gain=0，只剩 residual
    assert RULER.token_drop_partition(800, 512, 512) == (0, 288)


def test_token_drop_partition_never_negative():
    """边界：head 自己就超窗口（实测 2/4000）⇒ gain 不能为负。"""
    g, r = RULER.token_drop_partition(900, 600, 512)
    assert g == 0 and r == 388
