# -*- coding: utf-8 -*-
"""引擎**冷启动**：一个全新的库（从未入库过任何文档）也要能服务读取端点。

## 为什么单独一个文件（2026-09-17 实测的缺陷，§10.43）
`schema.sql` 用 `CREATE TABLE IF NOT EXISTS`，而 `catalog_hidden` / `page_breaks` /
`figure_html` 这三列**不在 schema.sql 里**——只由 `storage/clause_repo` 的迁移函数添加。
此前那条迁移只挂在**写路径**上（`insert_document` → `_ensure_content_hash_once`），
于是：

    一次性引擎（空 KS_DATA_DIR）+ `GET /api/v1/report/effect?window=all`
    → **500**，traceback：`sqlite3.OperationalError: no such column: catalog_hidden`
      at `src/core/exports/effect_report.py:133`

也就是**新装的库、还没有入库任何文档时，界面上的「效力报告」第一眼就是服务器错误**。
同一类读者还有 `api/server.py` 的两个目录端点。

## ⚠ 为什么**不能**用会话共享的那个夹具（两次踩到）
`tests/conftest.py` 的 `_isolate_data_dir` 是 **session 级**：整个测试会话共用一个库。
于是：
1. `test_effect_report.py` 的 autouse 夹具 `_clean_doc_meta(db)` 会拉起 `db` 夹具 ⇒
   那个夹具自己（正确地）跑了迁移 ⇒ **把要验的启动路径遮住**（变异体 M 实测 GREEN）；
2. 即使不用那个文件，**先跑过的任何入库用例**也会经由写路径把列补上 ⇒ 同样是假绿。
⇒ 所以本文件用**自己的一次性数据目录**（`_fresh_client`）：只走 HTTP，且库是真的空。
这样"删掉 `create_app()` 里的迁移"这条变异**无论测试顺序**都会红。
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def _fresh_client(tmp_path, monkeypatch):
    """**本用例自己的**空数据目录 + 只走 HTTP 的 TestClient。

    为什么要自己切目录：会话级夹具共享一个库，任何先跑过的入库都会让"未迁移的空库"
    这个条件不再成立（见模块 docstring）。这里显式切环境变量 + `reset_settings()` +
    丢掉线程局部连接（`get_db_connection()` 的默认键**不含路径**，不清就会连到旧库）。
    """
    from src.core import config
    from src.core.storage.sqlite_db import close_thread_connection

    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    config.reset_settings()
    close_thread_connection()

    from fastapi.testclient import TestClient
    from src.core.api.server import create_app
    token = "test-token-cold-start"
    with TestClient(create_app(token)) as c:
        yield c, token

    close_thread_connection()
    config.reset_settings()


def test_effect_report_serves_a_brand_new_db(_fresh_client):
    """冷启动：效力报告不能 500（这是那个缺陷的精确复现式）。"""
    c, token = _fresh_client
    r = c.get("/api/v1/report/effect?window=all",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == 200, body
    assert body["data"]["total"] == 0, body          # 这个库确实一份文档都没有


def test_document_catalog_endpoints_serve_a_brand_new_db(_fresh_client):
    """同一类读者（`server.py` 里也用 `catalog_hidden`）在空库上同样不能 500。"""
    c, token = _fresh_client
    for path in ("/api/v1/documents", "/api/v1/documents/categories"):
        r = c.get(path, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, (path, r.status_code, r.text[:200])


def test_effect_report_docs_endpoint_serves_a_brand_new_db(_fresh_client):
    """明细端点也走同一个 `_load_docs()`（避免"只修了汇总"）。

    ⚠ `l2` 是**必填**（路由签名 `effect_report_docs(top, l2, …)`），所以这里必须给一个
    合法大类名——参数校验失败（422）与"列不存在"（500）是两件事，别混。
    """
    c, token = _fresh_client
    r = c.get("/api/v1/report/effect/docs?top=std&l2=C%20%E5%8C%BB%E8%8D%AF%E3%80%81"
              "%E5%8D%AB%E7%94%9F%E3%80%81%E5%8A%B3%E5%8A%A8%E4%BF%9D%E6%8A%A4",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text


def test_bootstrap_guarantees_the_columns_readers_use():
    """**契约级**钉子：`init_schema()` + `ensure_additive_columns()` 之后，
    读者用到的追加列必须都在（顺序无关，不依赖任何路由）。

    为什么值得单独一条：`schema.sql` 只是 `CREATE TABLE IF NOT EXISTS`，
    **新库的形状取决于谁在什么时候跑迁移**。这条把"引导之后形状是什么"钉死。
    """
    from src.core.storage.sqlite_db import get_db_connection, init_schema
    from src.core.storage.clause_repo import ensure_additive_columns

    init_schema()
    ensure_additive_columns()
    conn = get_db_connection()
    need = {
        "doc_meta": {"catalog_hidden"},
        "clause_revision": {"content_hash", "page_breaks", "figure_html"},
    }
    for table, cols in need.items():
        have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        assert cols <= have, (table, sorted(cols - have))
