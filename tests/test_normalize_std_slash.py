# -*- coding: utf-8 -*-
"""存量全角斜杠回填脚本的用例（`scripts/normalize-standard-no-slash.py`，§11.0 R6c-2c/2d）。

动业主真库的脚本，最该被钉住的是**撞车保护**：归一后若与另一行同值就必须**跳过**，
否则回填本身会制造重复（`standard_no` 是查重依据）。
用临时 SQLite 造最小表，不碰真库。

⚠ 2026-09-18 独立复核 b32 之后**补了四类**（它证明旧用例挡不住这些）：
  1. **计划内自撞**：两行都全角、归一到同一个**尚不存在**的值——旧代码只查"库里已存在"，
     在 `short_code`（真库只有非唯一索引）上会**静默写重复**并报成功；
  2. **(列, 目标值) 不许重复**（同一件事的另一面，写成清单级断言）；
  3. **中断必须回滚**（`write_transaction` 已改 `except BaseException`）；
  4. **同进程第二次调用**不炸（旧代码 `conn2.close()` 关掉了共享线程局部连接）。
"""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "normalize-standard-no-slash.py"


@pytest.fixture()
def mod():
    spec = importlib.util.spec_from_file_location("_normalize_slash", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m


def _db(rows: list[tuple[str, str, str, str]], *, unique: bool = False) -> sqlite3.Connection:
    """最小 doc_meta。

    `unique=True` 时给 `standard_no` 加 UNIQUE——**真库就是这样**（`short_code` 没有），
    这个差异决定"撞车是报错还是静默写重复"，所以要让用例能分别造出来。
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE doc_meta (doc_id TEXT PRIMARY KEY, standard_no TEXT"
                 + (" UNIQUE" if unique else "") + ", short_code TEXT, standard_name TEXT)")
    conn.executemany("INSERT INTO doc_meta VALUES (?,?,?,?)", rows)
    return conn


def test_普通行会被归一(mod):
    conn = _db([("d1", "GB／T 10001.1-2023", "GB／T10001.12023", "公共信息图形符号")])
    changes, skipped = mod._plan(conn)
    assert not skipped
    got = {(c["column"], c["old"], c["new"]) for c in changes}
    assert ("standard_no", "GB／T 10001.1-2023", "GB/T 10001.1-2023") in got
    assert ("short_code", "GB／T10001.12023", "GB/T10001.12023") in got
    # 只换字符形状：空格与破折号**不许**动
    for _, old, new in got:
        assert old.replace("／", "/") == new


def test_与已存在的行撞车必须跳过(mod):
    """同一标准的两个文件：一条已是半角、一条是全角 ⇒ 全角那条要**跳过**（不制造重复）。"""
    conn = _db([
        ("half", "GB/T 14308-2010", "GB/T143082010", "旅游饭店星级的划分与评定"),
        ("full", "GB／T 14308-2010", "GB／T143082010", "旅游饭店星级的划分与评定"),
    ])
    changes, skipped = mod._plan(conn)
    assert changes == []
    assert {s["column"] for s in skipped} == {"standard_no", "short_code"}
    assert all(s["doc_id"] == "full" for s in skipped)
    assert all("不制造重复" in s["why"] for s in skipped)


def test_计划内自撞也要跳过(mod):
    """⚠ 复核 b32 的 4.4：两行全角、归一到**同一个尚不存在**的目标。

    旧代码只查"库里已存在"，于是**两行都进清单**——`standard_no` 有 UNIQUE 会整批失败，
    但 `short_code`（真库**只有非唯一索引**）会**静默写进两行一样的值**还报"integrity ok"。
    现在必须跳掉一条，并在 `why` 里说明是"计划内"。
    """
    conn = _db([
        ("a", "GB／T 3333-2003", "GB／T33332003", "甲"),
        ("b", "GB／T3333-2003", "GB／T33332003", "乙"),   # 写法不同、折完同值
    ])
    changes, skipped = mod._plan(conn)
    for col in ("standard_no", "short_code"):
        news = [c["new"] for c in changes if c["column"] == col]
        assert len(news) == len(set(news)), f"{col} 计划内出现重复目标: {news}"
    assert any("计划内" in s["why"] for s in skipped), skipped
    assert {s["doc_id"] for s in skipped} == {"b"}


def test_清单内列与目标值不重复(mod):
    """清单级断言（上面那条是行为级）——防以后改坏判重逻辑。"""
    conn = _db([("a", "GB／T 1111-2001", "GB／T11112001", "甲"),
                ("b", "GB／T1111-2001", "GB／T11112001", "乙")])
    changes, _ = mod._plan(conn)
    keys = [(c["column"], c["new"]) for c in changes]
    assert len(keys) == len(set(keys))


def test_没有全角就不产生变更(mod):
    conn = _db([("d1", "GB/T 1.1-2020", "GB/T1.12020", "标准化工作导则")])
    assert mod._plan(conn) == ([], [])


def test_standard_name_里的全角也归一(mod):
    conn = _db([("d1", "GB/T 1.1-2020", "GB/T1.12020", "标准／名称")])
    changes, _ = mod._plan(conn)
    assert [(c["column"], c["new"]) for c in changes] == [("standard_name", "标准/名称")]


class Test单事务语义:
    """复核 b32 的 4.5：中断要回滚，且"写后核对"不能读未提交状态。"""

    def test_中断会回滚(self, db):
        """`write_transaction` 必须对 `BaseException` 也回滚。

        `KeyboardInterrupt` **不是** `Exception` 子类——旧实现写 `except Exception`，
        Ctrl-C 打在事务中间**不回滚**，随后的"写后核对"读的是未提交状态，
        可能报一份"从未入库的成功"（b32 实测 `in_transaction=True`）。
        """
        from src.core.storage.sqlite_db import write_transaction

        db.execute("CREATE TABLE IF NOT EXISTS t_interrupt (k TEXT PRIMARY KEY, v TEXT)")
        db.commit()
        with pytest.raises(KeyboardInterrupt):
            with write_transaction() as w:
                w.execute("INSERT INTO t_interrupt VALUES ('k1','v1')")
                raise KeyboardInterrupt
        assert db.execute("SELECT COUNT(*) FROM t_interrupt").fetchone()[0] == 0
        assert db.in_transaction is False

    def test_同进程第二次调用不炸(self, db):
        """旧代码 `conn2.close()` 会把线程局部共享连接关掉 ⇒ 第二次 `ProgrammingError`。

        这里不去调 `main()`（它会真写库），只钉住"共享连接不会被脚本关掉"这件事：
        **剥掉注释后**源码里不许再出现 `conn2`（我第一版直接搜全文，被自己注释里写的
        `conn2.close()` 判红了——"检查代码"要先分清楚代码和注释）。
        """
        src = SCRIPT.read_text(encoding="utf-8")
        code = "\n".join(ln.split("#", 1)[0] for ln in src.splitlines())
        assert "conn2" not in code, "conn2 会关掉线程局部共享连接（b32 的 4.6）"
