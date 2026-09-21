import gc
import os
import shutil
import tempfile
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolate_data_dir():
    """全量测试的会话级临时数据目录。

    ⚠⚠ **2026-09-22 修（同一个病根，会话级这一份漏得更多）**：以前是
    `tempfile.TemporaryDirectory(prefix="ks_test_", ignore_cleanup_errors=True)` ——
    FastAPI 的**同步**路由跑在 AnyIO 线程池的 worker 线程里，那些线程自己握着一份库连接、
    比用例活得长，`close_thread_connection()` 关不到它们 ⇒ Windows 上 `knowledge.db`
    一直被占着（`WinError 32`），`ignore_cleanup_errors=True` 把失败**静默吞掉**
    ⇒ **每跑一次 pytest 漏一个目录**（2026-09-22 清点时 `%TEMP%` 里已积压 *1833* 个 `ks_test_*`）。
    现在：`close_all_connections()` 真关所有线程那一份（并摘掉那个线程的键），清理自己来、
    失败**抛出去**（不许静默）。取证与手法见 `src/core/storage/sqlite_db.py::close_all_connections`。
    """
    from src.core.storage.sqlite_db import close_all_connections, close_thread_connection

    td = Path(tempfile.mkdtemp(prefix="ks_test_"))
    old = os.environ.get("KS_DATA_DIR")
    os.environ["KS_DATA_DIR"] = str(td)
    from src.core import config
    config.reset_settings()
    try:
        yield td
    finally:
        config.reset_settings()
        close_thread_connection()
        close_all_connections()
        gc.collect()
        if old is None:
            os.environ.pop("KS_DATA_DIR", None)
        else:
            os.environ["KS_DATA_DIR"] = old
        last: OSError | None = None
        for delay in (0.0, 0.2, 0.5, 1.0):
            if delay:
                time.sleep(delay)
            try:
                shutil.rmtree(td)
                last = None
                break
            except OSError as e:  # noqa: PERF203 - 退避重试，故意逐个接
                last = e
        if last is not None:
            raise AssertionError(
                "会话级临时数据目录没清掉（清理失败**不许静默**）："
                f"{td} —— {type(last).__name__}: {last}")


@pytest.fixture()
def db(_isolate_data_dir):
    """初始化好 schema 的库连接（会话级临时库；测试数据 id 需唯一化避免残留）。

    ⚠ **必须镜像生产的启动引导**（2026-09-17 冷启动缺陷，§10.43）：生产是
    `create_app()` → `init_schema()` → `ensure_additive_columns()`。
    这个 fixture 以前只做前两步，于是 `catalog_hidden` 那类**不在 schema.sql 里**的
    追加列**不存在**——结果是一条**顺序依赖的假绿**：
    `test_eff_09_export_empty_db` 单跑**红**（`no such column: catalog_hidden`），
    放在文件里跑**绿**（前一条用例经由 `delete_document` 触发了写路径迁移）。
    现在这里与生产走**同一个入口**，测试库的形状就与真库一致了。
    """
    from src.core.storage.sqlite_db import init_schema, get_db_connection, close_thread_connection
    from src.core.storage.clause_repo import ensure_additive_columns
    from src.core.storage.material_repo import ensure_additive_columns as ensure_material_columns
    init_schema()
    ensure_additive_columns()
    ensure_material_columns()
    yield get_db_connection()
    close_thread_connection()


@pytest.fixture()
def client(_isolate_data_dir):
    """带 token 的 FastAPI TestClient。"""
    from fastapi.testclient import TestClient
    from src.core.api.server import create_app
    token = "test-token-123"
    app = create_app(token)
    with TestClient(app) as c:
        yield c, token


@pytest.fixture(autouse=True)
def _rerank_offline_for_tests(request, monkeypatch):
    """全量测试默认禁用 reranker（模型推理极慢），走 R30 降级路径保持检索快速。

    专项 rerank 测试（模块名含 reranker）不受影响。门禁锁的是基础检索质量；
    rerank 增量有效性由 tests/test_reranker.py 专项用例保证。
    """
    if "reranker" in request.node.name:
        yield
        return
    from src.core.retrieval import reranker
    monkeypatch.setattr(reranker, "is_available", lambda: False)
    yield
