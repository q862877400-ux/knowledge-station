"""spec 009 的引擎侧判据（**红箭头第①环**）。

判什么：
  ① `attach_bboxes` 对**有 span 的条款**补上 `bbox`（4 个有限数）与 `bbox_page`（int）；
  ② `bbox_page` 优先取 `page_start` 那一页的 span（条款跨页时箭头指起始页）；
  ③ 对**没有 span 的条款**：两个字段**都不出现**（不是 0、不是空数组）——
     这是"不编造坐标"的红线（0 会画出左上角一个错箭头，比没箭头更糟）；
  ④ 库不可用 / 查询失败 ⇒ **不抛错、静默返回**（坐标是增强，不是回答的前置条件）；
  ⑤ bbox 形状不对（不是 4 个数）⇒ 跳过该行，不写进去。

判据必须**有牙**：每条都能被一个具体的改动打红（见文件末尾的变异说明）。
"""
from __future__ import annotations

import sqlite3

import pytest

from src.core.llm.ks_answer import attach_bboxes


# --------------------------------------------------------------------------
# 一个最小的假连接：只实现 execute()，用来喂受控数据（不碰真库）
# --------------------------------------------------------------------------
class _FakeRow(dict):
    """sqlite3.Row 支持按列名取值；dict 子类即可满足本函数的两处取值。"""


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows
        self.calls = 0

    def execute(self, sql, params=()):  # noqa: ARG002 - 判据只关心返回
        self.calls += 1
        return _FakeCursor(self._rows)


@pytest.fixture()
def fake_db(monkeypatch):
    """把 get_db_connection 换成受控连接。"""
    import src.core.storage.sqlite_db as sqlite_db

    def install(rows):
        conn = _FakeConn(rows)
        monkeypatch.setattr(sqlite_db, "get_db_connection", lambda: conn)
        return conn

    return install


def _row(rev, page, bbox_json, order=0):
    return _FakeRow(clause_revision_id=rev, page_number=page, bbox_json=bbox_json, sort_order=order)


# --------------------------------------------------------------------------
# ① 有 span ⇒ 补上 bbox / bbox_page
# --------------------------------------------------------------------------
def test_attach_bboxes_fills_bbox_and_page(fake_db):
    fake_db([_row("rev1", 7, "[76.0, 643.43, 176.0, 656.43]")])
    evidence = [{"clause_revision_id": "rev1", "page_start": 7}]
    attach_bboxes(evidence)
    assert evidence[0]["bbox"] == [76.0, 643.43, 176.0, 656.43]
    assert evidence[0]["bbox_page"] == 7


# --------------------------------------------------------------------------
# ② 跨页时优先取 page_start 那一页
# --------------------------------------------------------------------------
def test_attach_bboxes_prefers_page_start(fake_db):
    fake_db([
        _row("rev1", 8, "[10.0, 100.0, 110.0, 113.0]", order=0),   # 页 8 在前（sort_order 小）
        _row("rev1", 7, "[20.0, 200.0, 120.0, 213.0]", order=1),  # 但 page_start=7
    ])
    evidence = [{"clause_revision_id": "rev1", "page_start": 7}]
    attach_bboxes(evidence)
    assert evidence[0]["bbox_page"] == 7, "箭头必须指条款**起始页**，不是 sort_order 第一页"
    assert evidence[0]["bbox"] == [20.0, 200.0, 120.0, 213.0]


def test_attach_bboxes_falls_back_to_first_when_page_start_missing(fake_db):
    fake_db([_row("rev1", 3, "[40.0, 400.0, 140.0, 413.0]")])
    evidence = [{"clause_revision_id": "rev1"}]  # 没有 page_start
    attach_bboxes(evidence)
    assert evidence[0]["bbox_page"] == 3


# --------------------------------------------------------------------------
# ②b ★ 跨页时**不许**把别页的坐标写进去（我自己复核时发现的风险）
# --------------------------------------------------------------------------
def test_attach_bboxes_skips_when_no_span_on_page_start(fake_db):
    """`page_start=5` 但该条款的 span 只在第 9 页 ⇒ **留空**，不许退化到 spans[0]。

    为什么：前端证据 tab 判"箭头画哪页"用的是 `page_start`（它**完全没用 `bbox_page`**，
    `KsEvidenceTab.tsx` 里 `bboxPage` 出现 0 次）⇒ 把第 9 页的坐标配第 5 页的 page，
    箭头会画在**错页的错误位置**上。留空则会走证据 tab 的既有兜底（它按目标页筛 span），
    那条路是**正确**的。
    """
    fake_db([_row("rev1", 9, "[40.0, 400.0, 140.0, 413.0]")])
    evidence = [{"clause_revision_id": "rev1", "page_start": 5}]
    attach_bboxes(evidence)
    assert "bbox" not in evidence[0], "跨页时不许把别页的坐标写进去（会画错页）"
    assert "bbox_page" not in evidence[0]


def test_attach_bboxes_uses_page_start_span_when_cross_page(fake_db):
    """跨页条款：只要 `page_start` 那一页**有** span，就取它（不取 sort_order 第一个）。"""
    fake_db([
        _row("rev1", 9, "[10.0, 100.0, 110.0, 113.0]", order=0),
        _row("rev1", 5, "[20.0, 200.0, 120.0, 213.0]", order=1),
    ])
    evidence = [{"clause_revision_id": "rev1", "page_start": 5}]
    attach_bboxes(evidence)
    assert evidence[0]["bbox_page"] == 5
    assert evidence[0]["bbox"] == [20.0, 200.0, 120.0, 213.0]


# --------------------------------------------------------------------------
# ③ ★ 没有 span ⇒ **不许编造**（这是红线）
# --------------------------------------------------------------------------
def test_attach_bboxes_leaves_absent_when_no_span(fake_db):
    fake_db([])  # 该条款一个 span 都没有（如 docx 直解的文档）
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)
    assert "bbox" not in evidence[0], "取不到坐标时**不许**写 bbox（更不许写 0）"
    assert "bbox_page" not in evidence[0]


def test_attach_bboxes_never_writes_zero_placeholder(fake_db):
    """**假证据**防线：0 兜底会让前端在页面左上角画一个错箭头。"""
    fake_db([_row("rev1", 1, "[]")])  # 形状不对（空数组）
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)
    assert "bbox" not in evidence[0]


def test_attach_bboxes_skips_malformed_bbox(fake_db):
    fake_db([
        _row("rev1", 1, "not json", order=0),
        _row("rev1", 1, "[40.0, 400.0, 140.0]", order=1),        # 3 个数
        _row("rev1", 1, "[40.0, 400.0, 140.0, null]", order=2),  # 含 null
        _row("rev1", 1, "[40.0, 400.0, 140.0, 413.0]", order=3),   # 唯一合法的
    ])
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)
    assert evidence[0]["bbox"] == [40.0, 400.0, 140.0, 413.0]


def test_attach_bboxes_rejects_non_finite(fake_db):
    fake_db([_row("rev1", 1, "[40.0, 400.0, 140.0, Infinity]")])
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)
    # JSON 的 Infinity 是非标准扩展；json.loads 能读出来，但 isfinite 必须拒掉
    assert "bbox" not in evidence[0]


# --------------------------------------------------------------------------
# ④ 失败不阻塞（坐标是增强，不是回答的前置条件）
# --------------------------------------------------------------------------
def test_attach_bboxes_survives_db_error(monkeypatch):
    import src.core.storage.sqlite_db as sqlite_db

    class _Boom:
        def execute(self, *a, **k):
            raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(sqlite_db, "get_db_connection", lambda: _Boom())
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)  # 不许抛
    assert "bbox" not in evidence[0]


def test_attach_bboxes_survives_missing_connection(monkeypatch):
    import src.core.storage.sqlite_db as sqlite_db

    def _boom():
        raise RuntimeError("no db")

    monkeypatch.setattr(sqlite_db, "get_db_connection", _boom)
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)  # 不许抛
    assert "bbox" not in evidence[0]


# --------------------------------------------------------------------------
# ⑤ 边界：空列表 / 无 rev / 多条混排
# --------------------------------------------------------------------------
def test_attach_bboxes_noop_on_empty(fake_db):
    conn = fake_db([])
    attach_bboxes([])
    assert conn.calls == 0, "空证据不该去查库"


def test_attach_bboxes_noop_when_no_revs(fake_db):
    conn = fake_db([])
    attach_bboxes([{"doc_id": "d1"}])  # 没有 clause_revision_id
    assert conn.calls == 0


def test_attach_bboxes_handles_multiple_revs(fake_db):
    fake_db([
        _row("revA", 1, "[10.0, 100.0, 110.0, 113.0]"),
        _row("revB", 5, "[30.0, 300.0, 130.0, 313.0]"),
    ])
    evidence = [
        {"clause_revision_id": "revA", "page_start": 1},
        {"clause_revision_id": "revB", "page_start": 5},
        {"clause_revision_id": "revC", "page_start": 1},  # 库里没有
    ]
    attach_bboxes(evidence)
    assert evidence[0]["bbox"] == [10.0, 100.0, 110.0, 113.0]
    assert evidence[1]["bbox"] == [30.0, 300.0, 130.0, 313.0]
    assert "bbox" not in evidence[2]


# --------------------------------------------------------------------------
# ⑥ ★★ 退化框拒收（spec 010，业主「红箭头还是没有」的真因之一）
# --------------------------------------------------------------------------
def test_attach_bboxes_rejects_degenerate_box(fake_db):
    """**退化框必须拒收** —— 真库实测 `GB 17681-2024` 全篇 370/370 条都是这种碎片。

    业主那轮的实测值：`[0.1, 784.33, 0.88, 784.4]` ⇒ 宽 **0.79pt**、高 **0.07pt**。
    画出来的"箭头"只有**一个点**那么大、**肉眼看不见** ⇒ 那等于骗用户"标好了"，
    比不画更糟。⇒ 不写坐标，让前端如实说"这一条取不到定位"。
    """
    fake_db([_row("rev1", 9, "[0.1, 784.33, 0.88, 784.4]")])
    evidence = [{"clause_revision_id": "rev1", "page_start": 9}]
    attach_bboxes(evidence)
    assert "bbox" not in evidence[0], "退化框（宽0.79×高0.07pt）不许写进证据"
    assert "bbox_page" not in evidence[0]


def test_attach_bboxes_rejects_thin_box(fake_db):
    """只满足一个维度也不许 —— 宽 200pt 但高 0.5pt 的"一条线"同样看不见。"""
    fake_db([_row("rev1", 1, "[10.0, 100.0, 210.0, 100.5]")])
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)
    assert "bbox" not in evidence[0]


def test_attach_bboxes_rejects_narrow_box(fake_db):
    """高 13pt（正常）但宽 2pt 的窄条也不许（画出来是一根看不见的竖线）。"""
    fake_db([_row("rev1", 1, "[10.0, 100.0, 12.0, 113.0]")])
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)
    assert "bbox" not in evidence[0]


def test_attach_bboxes_accepts_normal_line(fake_db):
    """**正常正文行必须通过**（防"阈值太松把正常行也拒了"）—— 用真库实测的中位量级。"""
    fake_db([_row("rev1", 1, "[73.0, 360.9, 334.0, 372.9]")])   # 261×12pt，真库实测值
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)
    assert evidence[0]["bbox"] == [73.0, 360.9, 334.0, 372.9]
    assert evidence[0]["bbox_page"] == 1


def test_degenerate_thresholds_are_the_documented_values():
    """阈值是**规范值**（有实测依据），不许随手改。

    依据（全库 184 万 span **随机抽样** 20 万）：尺寸分布**双峰** ——
    0–1pt 碎片占 13.6%、≥10pt 正常行占 86%，中间的 **1–5pt 几乎为空**（20 万里只有 7 条）
    ⇒ 5/3 落在**两峰之间的空隙**里 ⇒ 不误伤正常行。

    ⚠ **更正留痕（2026-10-12 复核时自己发现）**：原写"正常正文行宽 p0.1 = 11pt、高 p0.1 = 6pt；
    取 5/3 ⇒ 误伤率 0.02%"——**那是错的**，且是**抽样偏差**（`LIMIT 200000` 按行序取，
    集中在少数正常文档 ⇒ 偏低 686 倍）。真实**退化率 13.6%**。
    "退化率"与"误伤率"被混为一谈，一并更正。
    """
    from src.core.llm.ks_answer import DEGENERATE_BBOX_MIN_W, DEGENERATE_BBOX_MIN_H
    assert DEGENERATE_BBOX_MIN_W == 5.0
    assert DEGENERATE_BBOX_MIN_H == 3.0


def test_attach_bboxes_skips_degenerate_but_keeps_normal(fake_db):
    """同一条款有多个 span 时：退化框被跳过，**正常框仍被采用**（不是整条丢弃）。"""
    fake_db([
        _row("rev1", 1, "[0.1, 784.33, 0.88, 784.4]", order=0),   # 退化（排最前）
        _row("rev1", 1, "[73.0, 360.9, 334.0, 372.9]", order=1),   # 正常
    ])
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)
    assert evidence[0]["bbox"] == [73.0, 360.9, 334.0, 372.9], \
        "退化框被跳过后，应当用同一页里那个正常的 span"


def test_attach_bboxes_all_degenerate_leaves_empty(fake_db):
    """该条款的 span **全是**退化框 ⇒ 留空（不许拿任意一个凑数）。"""
    fake_db([
        _row("rev1", 9, "[0.1, 784.33, 0.88, 784.4]", order=0),
        _row("rev1", 9, "[0.12, 784.56, 0.18, 784.57]", order=1),
    ])
    evidence = [{"clause_revision_id": "rev1", "page_start": 9}]
    attach_bboxes(evidence)
    assert "bbox" not in evidence[0]
