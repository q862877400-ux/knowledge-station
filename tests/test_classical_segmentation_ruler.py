# -*- coding: utf-8 -*-
"""P3.2 尺子（`scripts/measure-classical-chinese-segmentation.py`）的单测。

**为什么必须测**（不是形式主义）：这把尺子上的三个判据各自都有一条**很容易踩回去**的坑，
每一条都在本轮真实发生过：

1. **单字占比必须按"出现次数"算，不是"含该词的段数"** ——
   第一版用了 `fts5vocab` 的 `doc`，同一份语料得出 **31.8%**，而另一把尺子量的是 **30.2%**；
   两个数并存时读者无法判断哪个对。判据见 `test_single_ratio_counts_occurrences_...`。
2. **字级口径的查询式不能复用 `fts_match_expr`** ——
   它有"丢弃单字符词"那条规则（为现状口径设的），在字级索引下会把查询**清空**。
   ⇒ "选字级就必须同时改 `fts_match_expr`"是这条路**必须付出的代价**，不是免费的索引选项。
   判据见 `test_char_level_requires_relaxing_the_single_char_drop`。
3. **n-gram 的计数单位是"段"不是"次"** —— 否则一个词在一段里反复出现会把词表挤满。
   判据见 `test_ngram_counts_segments_not_occurrences`。

⚠ 本文件**不测** `main()`（那要 1.86 MB 语料 + 几十秒），
只测判据所依赖的**纯函数**；尺子的可复跑性由"连跑两次剔除耗时行后逐字节相同"另行取证。
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "measure-classical-chinese-segmentation.py"


def _load():
    spec = importlib.util.spec_from_file_location("ks_classical_seg_ruler", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


RULER = _load()

#: 实测锚点：jieba（现代汉语词典）把这两个字切成**两个单字** ⇒ 现状查询式被清空。
#: 这不是"某个怪词"，是古籍语料里高频出现的**人名/地名**（陳留、黃巾）。
FRAGMENTED = "陳留"
#: 对照锚点：jieba 认得的词 ⇒ 现状查询式正常。
WHOLE = "關公"


def test_char_seg_gives_one_token_per_cjk_char():
    """B 口径：每个汉字一个 token；非汉字段沿用生产分词（不另造一套）。"""
    assert RULER.char_seg("關公") == "關 公"
    assert RULER.char_seg("甲乙丙") == "甲 乙 丙"


def test_char_level_requires_relaxing_the_single_char_drop():
    """★ 这条路的核心代价：**字级查询不能复用 `fts_match_expr`**。

    现状函数把单字符词丢掉（那条规则是为现状口径设的）；字级索引下"字"就是检索单位，
    丢掉它 = 把查询清空 ⇒ **0 命中**。所以"选字级"与"改 `fts_match_expr`"是**绑定的**。
    """
    from src.core.text_utils import fts_match_expr, segment_for_fts

    # 机制前提：这个词确实被切成了单字（若 jieba 升级后认得它，这条会红 —— 那是**该红**的）
    assert segment_for_fts(FRAGMENTED).split() == ["陳", "留"]
    assert fts_match_expr(FRAGMENTED, latin_prefix=False) == ""      # 现状：查询被清空
    # 字级口径：同一个查询必须能表达出来
    assert RULER.char_and_expr(FRAGMENTED) == '"陳" "留"'
    assert RULER.char_or_expr(FRAGMENTED) == '"陳" OR "留"'
    # 对照：jieba 认得的词，现状查询式正常 ⇒ 上面那条不是"函数坏了"
    assert fts_match_expr(WHOLE, latin_prefix=False) == '"關公"'


def test_no_drop_expr_differs_from_production_only_by_the_single_char_rule():
    """A+ 口径：**索引不动**，只关掉"丢弃单字符词"这条规则。

    它是三条路里唯一不需要重建索引的，所以它到底改了什么必须钉死 ——
    对**多字词**，两者必须逐字节相同（否则 A+ 就不是"只改一处"了）。
    """
    from src.core.text_utils import fts_match_expr

    assert RULER.no_drop_expr(FRAGMENTED) == '"陳" OR "留"'
    assert fts_match_expr(FRAGMENTED, latin_prefix=False) == ""
    # 多字词上两者一致（这里的词没被切成单字 ⇒ 规则没被触发）
    assert RULER.no_drop_expr(WHOLE) == fts_match_expr(WHOLE, latin_prefix=False)
    # 空查询的兜底：A+ 下不再出现空表达式
    assert RULER.no_drop_expr("").strip() == ""


def test_single_ratio_counts_occurrences_not_documents():
    """★ 单字占比必须按**出现次数**（`cnt`）算。

    第一版按 `doc`（含该词的段数）算 ⇒ 同一份语料 31.8% vs 另一把尺子的 30.2%，
    两个数并存、读者无法判断。这里用一个 2 行的假表把两条口径**分开**：
    `的` 只在第 1 行出现、但出现 3 次 ⇒ `doc`=1、`cnt`=3 ⇒ 只有 `cnt` 口径会给出 3。
    """
    conn = sqlite3.connect(":memory:")
    conn.execute(RULER.DDL.format(tbl="t"))
    conn.execute("INSERT INTO t(clause_revision_id,content_segmented) VALUES('r0',?)", ("的 的 的",))
    conn.execute("INSERT INTO t(clause_revision_id,content_segmented) VALUES('r1',?)", ("甲乙 丙丁",))
    conn.execute("CREATE VIRTUAL TABLE v_t USING fts5vocab(t, 'row')")
    all_t, sing, sing_cjk = RULER.single_ratio("t", conn)
    # 按 doc 口径这三个数会是 3 / 1 / 1（每个词只算"出现在几段里"）⇒ 与下面全都不同。
    assert all_t == 5                      # 3 + 2 个 token
    assert sing == 3                       # `的` 出现 3 次
    assert sing_cjk == 3                   # `的` 是汉字
    conn.close()


def test_ngram_counts_segments_not_occurrences():
    """n-gram 的计数单位是**段**：一个词在同一段里出现 5 次只算 1。

    否则"高频片段"会把词表挤满，自挖词典会被单段重复文本带偏。
    """
    segs = ["甲乙丙甲", "甲乙丙", "甲乙丙"]
    assert RULER.ngram_counts(segs, 3, min_count=3)["甲乙丙"] == 3
    # 同一段里出现两次的串只算 1 段 ⇒ 不到 3 段就不入选
    assert "甲甲乙" not in RULER.ngram_counts(["甲甲乙甲乙甲乙", "甲甲乙甲乙"], 3, min_count=3)
