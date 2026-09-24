"""**B3-⑦「6797 篇打层级标签」为什么不由 Jev 填**（2026-09-24 量测结论，附事实）。

同 B3-⑥ 的纪律：先量，量不过就不做。业主口径是「确实很好用而且性能要求低再打包」。

## 量到的事实（真库只读）

| 事实 | 数 |
|---|---|
| `doc_meta` 合计 | **6797**（`standard` 6417 + `法律法规` 380） |
| `ccs_code` **有值**的 | **0**（6795 篇全空） |
| `domain_tags` 里**已带 CCS** 的 | 有（如 `["CCS:C65 劳动安全技术综合"]`）——分类器认它 |
| `doc_ccs_state` 行数 | **50**（= 业主 9/23 按了一次"补全分类号"，跑满一批就停了） |
| 法规树 `legal_hierarchy` | 规范性文件 261 / 其他 84 / 部门规章 19 / 征求意见稿 16 |

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
import sqlite3
from pathlib import Path

REAL_DB = r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db"
#: 迁移前后应当恒等的事实（真库量测时的取值；变了说明库被别处改过，先查再动）
FACTS = {"total": 6797, "standard": 6417, "law": 380}


def _ro():
    return sqlite3.connect("file:" + REAL_DB.replace("\\", "/") + "?mode=ro", uri=True)


def test_facts_still_hold():
    """量测结论的前提是这些事实；库变了就先查来龙去脉，别拿旧结论当新依据。"""
    if not Path(REAL_DB).exists():
        return
    c = _ro()
    try:
        total = c.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
        std = c.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_type='standard'").fetchone()[0]
        law = c.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_type<>'standard'").fetchone()[0]
        ccs = c.execute("SELECT COUNT(*) FROM doc_meta WHERE ccs_code IS NOT NULL"
                        " AND ccs_code<>''").fetchone()[0]
    finally:
        c.close()
    assert (total, std, law) == (FACTS["total"], FACTS["standard"], FACTS["law"]), \
        "真库行数变了（量测前提失效）：先查是谁改的，别直接套旧结论"
    # 关键前提：CCS 补完机制仍**没跑完**（若已跑完，这条结论就该重估）
    assert ccs < FACTS["standard"], (
        f"ccs_code 已有 {ccs} 篇 ⇒ 『既有批量补完没跑完』这个前提变了，重估 B3-⑦")


def test_change_signal_column_exists_after_migration():
    """`change_signal` 列：真库已 ALTER 补上（2026-09-24），全新库由 schema.sql 直接带。

    ⚠ 这条是 2026-09-24 真机才发现的：代码加了列、真库**没跑过新代码** ⇒ 查询端点一查就
    `no such column`。真库已补（回退记录 `var/tmp/change-signal-backup.json`）。
    """
    if not Path(REAL_DB).exists():
        return
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
    assert json.loads(json.dumps(FACTS))["total"] == 6797
