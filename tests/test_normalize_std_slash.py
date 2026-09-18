# -*- coding: utf-8 -*-
"""存量全角斜杠回填脚本的用例（`scripts/normalize-standard-no-slash.py`，§11.0 R6c-2c）。

动业主真库的脚本，最该被钉住的是**撞车保护**：归一后若与另一行同值就必须**跳过**，
否则回填本身会制造重复（`standard_no` 是查重依据）。
用临时 SQLite 造最小表，不碰真库。
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


def _db(rows: list[tuple[str, str, str, str]]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE doc_meta (doc_id TEXT PRIMARY KEY, standard_no TEXT, "
                 "short_code TEXT, standard_name TEXT)")
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


def test_会撞车的行必须跳过(mod):
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


def test_没有全角就不产生变更(mod):
    conn = _db([("d1", "GB/T 1.1-2020", "GB/T1.12020", "标准化工作导则")])
    assert mod._plan(conn) == ([], [])


def test_standard_name_里的全角也归一(mod):
    conn = _db([("d1", "GB/T 1.1-2020", "GB/T1.12020", "标准／名称")])
    changes, _ = mod._plan(conn)
    assert [(c["column"], c["new"]) for c in changes] == [("standard_name", "标准/名称")]
