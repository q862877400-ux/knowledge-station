"""`debug_dump` 的**保留策略**（唯一所有者）——两类记录**各自清理**，互不挤占。

## 为什么要有这个模块（2026-09-25 实测的真缺陷）

`debug_dump` 一张表承载**两类完全不同的东西**：

* **外发审计**（`trigger_type='egress'`）：每次云端调用写一条，**量很大**
  （实测占 992/1000，约 **110 条/天**）；
* **提问证据**（`trigger_type='user_export'`）：答案路径写的，带 `retrieval_result`
  （命中了哪些标准号+条款号）——**量小、但不可再生**。

原先**两处写入各自把整张表裁到最新 1000 行**（两处都硬编码 `LIMIT 1000`）。
⇒ 谁写得多谁说话：**外发审计把提问证据挤出去**。
实测后果（2026-09-25 读真库）：**1,000 行里只剩 8 行带检索结果**；
而 9-16 的审计行还在 ⇒ 滚动窗约 **9 天** ⇒ **真实提问最多活 9 天就被删**。

⚠ 这不只是"少收了数据"，而是**收进来又被销毁**。而且它卡着两条线：
检索长周期计划 P1 的**盈亏平衡点**（真实目标里"多条定义"的比例）靠它算；
P5 的"真实提问分布"也把它列为前置。

## 修法

**按 `trigger_type` 各自清理**（`prune()`），于是：

* 外发审计**保 1000 条**（与原先同量级，审计视图不受影响）；
* 提问证据**保 5000 条**（新增上限；按实测约 10 条/天量级 ≈ 一年以上，
  单行约 5 KB ⇒ 上限约 25 MB，**有界**，不会无限长）。

⚠ 两类相加上限 6000 行；这比原先的 1000 行**更大**，是**为了让提问证据活下来**
（旧行为下它连一天都活不到——被审计挤掉）。
"""
from __future__ import annotations

import sqlite3

#: 外发审计保留条数（与历史行为同量级）。
KEEP_EGRESS = 1000
#: 提问证据保留条数。**故意比审计大**：它不可再生，且 P1/P5 都要用。
KEEP_QUESTION_EVIDENCE = 5000

#: 两类记录的 `trigger_type` 取值（与 `egress_audit._AUDIT_TRIGGER_TYPES` 同口径；
#: 两份都对，但**各自的用途不同**：那份是"审计聚合时算不算外发记录"，
#: 这份是"清理时按谁分组"。改一处要想想另一处。）
TYPE_EGRESS = "egress"
TYPE_QUESTION = "user_export"


def prune(conn: sqlite3.Connection, trigger_type: str, keep: int) -> int:
    """只裁**这一类**记录到最新 `keep` 条；**不动别的类型**。返回删掉的条数。

    ⚠ 为什么必须带 `WHERE trigger_type = ?`：不带就是全表裁——那正是本缺陷的成因
    （外发审计量大 ⇒ 把提问证据挤出去）。**这条 `WHERE` 是修复的全部要点**，
    删掉它就等于退回旧行为。
    """
    cur = conn.execute(
        "DELETE FROM debug_dump WHERE trigger_type = ? AND dump_id NOT IN ("
        " SELECT dump_id FROM debug_dump WHERE trigger_type = ?"
        " ORDER BY created_at DESC, rowid DESC LIMIT ?)",
        (trigger_type, trigger_type, keep))
    return int(cur.rowcount or 0)
