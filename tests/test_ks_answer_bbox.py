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
    fake_db([_row("rev1", 7, "[76.0, 643.43, 117.0, 655.43]")])
    evidence = [{"clause_revision_id": "rev1", "page_start": 7}]
    attach_bboxes(evidence)
    assert evidence[0]["bbox"] == [76.0, 643.43, 117.0, 655.43]
    assert evidence[0]["bbox_page"] == 7


# --------------------------------------------------------------------------
# ② 跨页时优先取 page_start 那一页
# --------------------------------------------------------------------------
def test_attach_bboxes_prefers_page_start(fake_db):
    fake_db([
        _row("rev1", 8, "[1.0, 1.0, 2.0, 2.0]", order=0),   # 页 8 在前（sort_order 小）
        _row("rev1", 7, "[9.0, 9.0, 10.0, 10.0]", order=1),  # 但 page_start=7
    ])
    evidence = [{"clause_revision_id": "rev1", "page_start": 7}]
    attach_bboxes(evidence)
    assert evidence[0]["bbox_page"] == 7, "箭头必须指条款**起始页**，不是 sort_order 第一页"
    assert evidence[0]["bbox"] == [9.0, 9.0, 10.0, 10.0]


def test_attach_bboxes_falls_back_to_first_when_page_start_missing(fake_db):
    fake_db([_row("rev1", 3, "[1.0, 2.0, 3.0, 4.0]")])
    evidence = [{"clause_revision_id": "rev1"}]  # 没有 page_start
    attach_bboxes(evidence)
    assert evidence[0]["bbox_page"] == 3


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
        _row("rev1", 1, "[1.0, 2.0, 3.0]", order=1),        # 3 个数
        _row("rev1", 1, "[1.0, 2.0, 3.0, null]", order=2),  # 含 null
        _row("rev1", 1, "[1.0, 2.0, 3.0, 4.0]", order=3),   # 唯一合法的
    ])
    evidence = [{"clause_revision_id": "rev1", "page_start": 1}]
    attach_bboxes(evidence)
    assert evidence[0]["bbox"] == [1.0, 2.0, 3.0, 4.0]


def test_attach_bboxes_rejects_non_finite(fake_db):
    fake_db([_row("rev1", 1, "[1.0, 2.0, 3.0, Infinity]")])
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
        _row("revA", 1, "[1.0, 1.0, 2.0, 2.0]"),
        _row("revB", 5, "[3.0, 3.0, 4.0, 4.0]"),
    ])
    evidence = [
        {"clause_revision_id": "revA", "page_start": 1},
        {"clause_revision_id": "revB", "page_start": 5},
        {"clause_revision_id": "revC", "page_start": 1},  # 库里没有
    ]
    attach_bboxes(evidence)
    assert evidence[0]["bbox"] == [1.0, 1.0, 2.0, 2.0]
    assert evidence[1]["bbox"] == [3.0, 3.0, 4.0, 4.0]
    assert "bbox" not in evidence[2]
