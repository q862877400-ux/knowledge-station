# -*- coding: utf-8 -*-
"""`sqlite_db` 的**跨线程连接登记/关闭**（2026-09-22 为了"临时目录真能删掉"而加）。

## 这组用例在守什么（每条都有反向）

背景（实测，不是推测）：FastAPI 的**同步**路由跑在 AnyIO 线程池的 worker 线程里，那些线程自己
`get_db_connection()` 建了一份连接、且**比用例活得长**。`close_thread_connection()` 只关**当前线程**
那一份 ⇒ Windows 上 `knowledge.db` 一直被占着、临时目录删不掉（`WinError 32`），而
`TemporaryDirectory(..., ignore_cleanup_errors=True)` 把这条失败**静默吞掉** ——
后果是每跑一次 pytest 漏一个目录（清点时 `%TEMP%` 里积压 1833 个 `ks_test_*` / 59 个 `ks_scope_*`）。

1. `close_all_connections()` **真能关掉别的线程**建的那一份（并让那个文件可以被删掉）；
2. ⚠ 关的同时必须把那个线程 `_local` 里的键**摘掉** —— 不摘的话，那个（会被线程池复用的）
   线程下次 `get_db_connection()` 拿到的是**已关闭**的连接。这条是"修 A 引入 B"的唯一入口，
   所以单独判：关完之后**同一个线程**再拿一次，必须是**新的、能用的**连接；
3. `close_thread_connection()` 之后登记表里**不留**那条死登记（否则登记表会随线程更迭长起来）。
"""
from __future__ import annotations

import shutil
import sqlite3
import threading

from src.core.storage import sqlite_db


def test_close_all_connections_reaches_another_thread_and_keeps_it_usable(tmp_path):
    """① 别的线程那份被关掉（文件能删）；② 那个线程随后还能拿到**能用**的连接。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    db_file = sub / "w.db"
    holder: dict[str, object] = {}
    ready = threading.Event()
    resume = threading.Event()

    def worker() -> None:
        conn = sqlite_db.get_db_connection(db_file)
        conn.execute("CREATE TABLE IF NOT EXISTS t(x)")
        conn.commit()
        holder["conn"] = conn
        ready.set()
        assert resume.wait(10), "主线程没放行"
        try:
            conn.execute("SELECT 1")
            holder["after_close"] = "还能用（不该）"
        except sqlite3.ProgrammingError as e:
            holder["after_close"] = f"ProgrammingError：{e}"
        # ⚠ 关键判据：同一个线程再拿一次 —— 必须是**新的**且**能用**的。
        fresh = sqlite_db.get_db_connection(db_file)
        fresh.execute("SELECT 1").fetchall()
        holder["fresh_is_new"] = fresh is not conn
        holder["fresh_works"] = True

    t = threading.Thread(target=worker, name="ks-conn-registry-worker")
    t.start()
    try:
        assert ready.wait(10), "worker 线程没建好连接"
        closed = sqlite_db.close_all_connections()
        assert closed >= 1, "close_all_connections() 一个都没关（worker 线程那份被漏掉了）"
    finally:
        resume.set()
        t.join(10)
    assert not t.is_alive(), "worker 线程没退出来"
    assert str(holder["after_close"]).startswith("ProgrammingError"), (
        "别的线程那份连接**没被关掉**（还能执行 SQL）—— 那就是没修：临时目录照样删不掉"
        f"（实测 {holder['after_close']}）")
    assert holder.get("fresh_is_new") is True, (
        "关连接之后那个线程拿到的还是**同一个**（已关闭的）连接对象 —— "
        "说明 `_local` 里的键没摘掉，那个被复用的线程会用到一个死连接")
    assert holder.get("fresh_works") is True
    # 反向：文件真的释放了 ⇒ 目录删得掉（这正是当初漏目录的直接症状）。
    assert sqlite_db.close_all_connections() >= 1, "worker 后来建的那份也该被关掉"
    shutil.rmtree(sub)
    assert not sub.exists()


def test_close_thread_connection_forgets_its_registry_entry():
    """③ `close_thread_connection()` 关掉之后，登记表里**不许**再留着那条死登记。"""
    conn = sqlite_db.get_db_connection()
    assert any(entry[0] is conn for entry in sqlite_db._registry), \
        "新建的连接没进登记表 ⇒ close_all_connections() 永远找不到它"
    sqlite_db.close_thread_connection()
    assert not any(entry[0] is conn for entry in sqlite_db._registry), \
        "关掉的连接还留在登记表里（登记表会随线程更迭一直涨）"
    with sqlite_db._registry_lock:
        stale = [e for e in sqlite_db._registry if e[1].get(e[2]) is not e[0]]
    assert stale == [], f"登记表里有'键已经不指向这份连接'的死条目：{stale}"


def test_close_all_connections_is_safe_when_nothing_is_registered():
    """④ 空表/重复调用都不许炸（两个 fixture 收尾都会调它）。"""
    sqlite_db.close_all_connections()
    assert sqlite_db.close_all_connections() == 0
