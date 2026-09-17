import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolate_data_dir():
    with tempfile.TemporaryDirectory(prefix="ks_test_", ignore_cleanup_errors=True) as td:
        import os
        old = os.environ.get("KS_DATA_DIR")
        os.environ["KS_DATA_DIR"] = td
        from src.core import config
        config.reset_settings()
        yield Path(td)
        config.reset_settings()
        if old is None:
            os.environ.pop("KS_DATA_DIR", None)
        else:
            os.environ["KS_DATA_DIR"] = old


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
