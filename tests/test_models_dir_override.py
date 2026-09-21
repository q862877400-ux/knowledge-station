"""`KS_MODELS_DIR` 覆盖：模型缓存可重定向，且**只**重定向模型缓存。

为什么要有这条（实测背景，2026-09-21 复核定性）：
`tests/conftest.py` 是 **session 级 autouse**，每个 pytest 会话都换一个全新的
`KS_DATA_DIR`（`%TEMP%\\ks_test_*`）⇒ `models_dir`（默认 `<data_dir>/models`）每次都是空的
⇒ **每一次全量都要重新下载** BGE 权重（~91MB；实测会话目录被填到 748MB）。本机
`ALL_PROXY=http://127.0.0.1:7897` 那个代理半死不活时下载会**挂死**，于是向量通道不可用、
"依赖检索"的用例降级失败 —— 一次**与环境有关、与被测代码无关**的假红。
门禁现在把 `KS_MODELS_DIR` 指到一个**常驻**缓存目录，模型只落地一次。

本文件钉住三件事：① 不设变量时行为不变（`<data_dir>/models`）；② 设了就照办；
③ 覆盖**不许**连带改动 `data_dir` / `db_path`（否则一次"共享模型缓存"会顺手把数据库也搬走）。
"""

from __future__ import annotations

from pathlib import Path

from src.core.config import Settings


def test_models_dir_defaults_under_data_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("KS_MODELS_DIR", raising=False)
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    assert Settings().models_dir == Path(tmp_path) / "models"


def test_models_dir_honours_override(tmp_path, monkeypatch):
    shared = tmp_path / "shared-models"
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("KS_MODELS_DIR", str(shared))
    assert Settings().models_dir == shared


def test_models_override_does_not_move_data_or_db(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setenv("KS_DATA_DIR", str(data))
    monkeypatch.setenv("KS_MODELS_DIR", str(tmp_path / "shared-models"))
    s = Settings()
    assert s.data_dir == data
    assert s.db_path == data / "database" / "knowledge.db"


def test_models_override_dir_is_created_by_ensure_dirs(tmp_path, monkeypatch):
    shared = tmp_path / "shared-models"
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("KS_MODELS_DIR", str(shared))
    s = Settings()
    assert not shared.exists()
    s.ensure_dirs()
    assert shared.is_dir()
