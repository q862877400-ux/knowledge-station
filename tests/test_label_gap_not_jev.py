"""**B3-⑦「6797 篇打层级标签」为什么不由 Jev 填**（2026-09-24 量测结论，附事实）。

同 B3-⑥ 的纪律：先量，量不过就不做。业主口径是「确实很好用而且性能要求低再打包」。

## 量到的事实（真库只读）

| 事实 | 2026-09-24 量 | **2026-10-09 复量** |
|---|---|---|
| `doc_meta` 合计 | **6797**（`standard` 6417 + `法律法规` 380） | **8983**（`standard` 7173 + `法律法规` 1810） |
| `ccs_code` **有值**的 | **0**（6795 篇全空） | **0**（8983 篇仍全空） |
| `domain_tags` 里**已带 CCS** 的 | 6087 | **6838**（涨了 ⇒ 能力仍在） |
| `doc_ccs_state` 行数 | **50**（业主 9/23 按过一次"补全分类号"） | **806**（补全机制在推进，但离 7173 篇还差得远） |
| 法规树 `legal_hierarchy` | 规范性文件 261 / 其他 84 / 部门规章 19 / 征求意见稿 16 | **一字未变** |

> **⚠ 2026-10-09 复量（第 17 轮，自动续接链）—— 按本文件自己的规矩办的**：
> 本条是**绊线**（库一变就红，逼人先查再动）。真库从 6797 长到 8983 篇 ⇒ 它按设计红了。
> **逐条复核结论**：① `ccs_code` **仍然是 0**（8983 篇一篇都没填）；② `domain_tags` 带 CCS 的
> **6087 → 6838（涨）**；③ `doc_ccs_state` **50 → 806**（机制在推进，但 806 ≪ 7173）；
> ④ 法规树分布**一字未变**。
> ⇒ **原结论「缺口在"没跑完"、不在"没能力"」仍然成立**（依据：能力侧只涨不跌、`ccs_code` 侧仍然全空、
> 补全机制远未跑完）。下面 `FACTS` 已换成复量值；**没有**改判据、**没有**放宽阈值。

## 结论：**缺口不在"分类能力"，在"没跑完"**

- 标准树那 6415 篇**不是没人分类**：`domain_tags` 里已有 CCS，分类器按它走；
  空的是 `ccs_code` 那一列，因为**既有的批量补完（"补全分类号"按钮）只跑了一批 50 篇**。
- 法规树那 380 篇**已经分到位**（规范性文件/部门规章/征求意见稿，都是入库时按标题判的）。

⇒ **让 Jev 去填 CCS = 造第二份分类真源**（AGENTS.md 铁律：单一出处/防漂移），
  而且**绕过了既有的"补全分类号"入口与它的状态机**（`doc_ccs_state`：outcome/source/attempts）。
  真正该做的是**把既有入口跑完**（那是业主一个按钮的事），不是加一个新模型。

## 留给业主的一句话

若他要"先按领域筛一筛"，**最省事的是把"补全分类号"跑完**（现成入口、现成状态机、可回看）；
Jev 在这里的价值只剩"给没跑过的那批**猜一个候选**"，那恰好是既有机制里 `keyword_form`
那一环的活——**同一件事已有归属**。
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

#: ⚠ 2026-10-18 改（两次）：原先写死 `C:\Users\Zegel\AppData\Roaming\KnowledgeStation\...`（**包外**）。
#:   ① 业主令「不依赖包外任何东西」+ 旧库已删 ⇒ 必须改成算出来的路径。
#:   ② ⚠ **不能**用 `get_settings().db_path`：门禁的 pytest 跑在 `conftest` 的**临时空库**上
#:      ⇒ 那几条"真库事实"判据会**假红**（空库什么都不符）。
#:   ⇒ 与 `tests/test_catalog_hidden_retrieval.py` 同一套：**只认显式点名的真库**。
_REPO = Path(__file__).resolve().parents[1]
REAL_DB = os.environ.get("KS_REAL_DB") or str(_REPO / "var" / "data" / "database" / "knowledge.db")
#: 没显式点名 ⇒ 这条在门禁里**结构上验不了**，如实跳过（不假装通过）
_EXPLICIT = bool(os.environ.get("KS_REAL_DB"))
#: 迁移前后应当恒等的事实（真库量测时的取值；变了说明库被别处改过，先查再动）
#: ⚠ 2026-10-09（第 17 轮）**复量后的值**：真库从 6797 长到 8983 篇 ⇒ 绊线按设计红了，
#: 逐条复核后原结论仍然成立（见文件头那张表的复量列与下面的复核说明）。
FACTS = {"total": 8983, "standard": 7173, "law": 1810,
         # 独立复核 2026-09-24 补：结论**建立在这两个事实上**（缺口在"没跑完"、不在"没能力"）：
         #   · 6838 篇的 `domain_tags` 里**已经带 CCS** ⇒ 分类能力早就有了（复量：6087 → 6838，只涨不跌）；
         #   · `doc_ccs_state` **806** 行 ⇒ "补全分类号"在推进，但 806 ≪ 7173 ⇒ **仍然没跑完**。
         "domain_tags_with_ccs": 6838, "doc_ccs_state_rows": 806}


def _ro():
    return sqlite3.connect("file:" + REAL_DB.replace("\\", "/") + "?mode=ro", uri=True)


def _require_real_db():
    """**真库不在就显式 skip，不许静默通过**（独立复核 2026-09-24 指出 `if not exists(): return`
    会让判据恒真——换台机器/库还没建时，测试"通过"但什么都没验）。

    ⚠ 2026-10-18 加：**没显式点名 `KS_REAL_DB` 也 skip** —— 门禁的 pytest 跑在
    `conftest` 的临时空库上，而本文件的判据全部建立在那 8,983 篇的**真库事实**上
    （`FACTS`）；在空库上跑必然全红，那是**假红**、不是回归。
    """
    import pytest
    if not _EXPLICIT:
        pytest.skip("未显式点名真库（设 KS_REAL_DB=<path> 才跑；门禁跑的是临时空库）")
    if not Path(REAL_DB).exists():
        pytest.skip(f"真库不在：{REAL_DB}（静默 return 会让这条判据恒真）")


def test_facts_still_hold():
    """量测结论的前提是这些事实；库变了就先查来龙去脉，别拿旧结论当新依据。

    ⚠ 独立复核 2026-09-24 指出：原先只锁了 3 个计数，**没锁"分类其实已经做了"那两个事实**
    （`domain_tags` 里的 CCS、`doc_ccs_state` 的 50 行）——而**结论正是建立在这两个事实上**
    （缺口在"没跑完"、不在"没能力"）。它们一变，结论就失效却不会红。已补。
    """
    _require_real_db()
    c = _ro()
    try:
        total = c.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
        std = c.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_type='standard'").fetchone()[0]
        law = c.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_type<>'standard'").fetchone()[0]
        ccs = c.execute("SELECT COUNT(*) FROM doc_meta WHERE ccs_code IS NOT NULL"
                        " AND ccs_code<>''").fetchone()[0]
        with_ccs_tags = c.execute(
            "SELECT COUNT(*) FROM doc_meta WHERE domain_tags LIKE '%CCS:%'").fetchone()[0]
        state_rows = c.execute("SELECT COUNT(*) FROM doc_ccs_state").fetchone()[0]
    finally:
        c.close()
    assert (total, std, law) == (FACTS["total"], FACTS["standard"], FACTS["law"]), \
        "真库行数变了（量测前提失效）：先查是谁改的，别直接套旧结论"
    # 关键前提：CCS 补完机制仍**没跑完**（若已跑完，这条结论就该重估）
    assert ccs < FACTS["standard"], (
        f"ccs_code 已有 {ccs} 篇 ⇒ 『既有批量补完没跑完』这个前提变了，重估 B3-⑦")
    # 另一个前提：**分类能力早就有了**（domain_tags 里已带 CCS）——它变少才说明能力退化，
    # 它变多不影响结论（结论靠的是"ccs_code 空"那一侧）。
    assert with_ccs_tags >= FACTS["domain_tags_with_ccs"], (
        f"domain_tags 带 CCS 的从 {FACTS['domain_tags_with_ccs']} 掉到 {with_ccs_tags}"
        f" ⇒ 『分类能力早就有了』这个前提变了（是不是回退过？）")
    # 第三个前提：业主按过一次"补全分类号"（若已跑完，结论同样要重估）
    assert state_rows >= FACTS["doc_ccs_state_rows"], (
        f"doc_ccs_state 从 {FACTS['doc_ccs_state_rows']} 涨到 {state_rows}"
        f" ⇒ 补全机制在推进，『没跑完』要重新量")


def test_change_signal_column_exists_after_migration():
    """`change_signal` 列：真库已 ALTER 补上（2026-09-24），全新库由 schema.sql 直接带。

    ⚠ 这条是 2026-09-24 真机才发现的：代码加了列、真库**没跑过新代码** ⇒ 查询端点一查就
    `no such column`。真库已补（回退记录 `var/tmp/change-signal-backup.json`）。
    """
    _require_real_db()
    c = _ro()
    try:
        cols = [r[1] for r in c.execute("PRAGMA table_info(doc_meta)")]
    finally:
        c.close()
    assert "change_signal" in cols, "真库缺 change_signal 列（跑一次 init_schema 即可补）"


def test_decision_recorded():
    """本文件是**决策留痕**（不是待办）：B3-⑦ 不由 Jev 填，理由=单一真源/既有机制已有归属。"""
    doc = Path(__file__).read_text(encoding="utf-8")
    assert "造第二份分类真源" in doc
    assert "补全分类号" in doc, "必须写清既有机制的名字，否则下轮会重提"
    # ⚠ 2026-10-09：这个数原来是 6797（写这份记录时的真库规模）。**它不是"魔数"，是"写这份记录时
    #   真库多大"的标记** —— 复量后跟着换成 8983，含义不变（这份记录对应哪一次量测）。
    assert json.loads(json.dumps(FACTS))["total"] == 8983
