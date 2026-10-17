"""`KS_MODELS_DIR` 覆盖：模型缓存可重定向，且**只**重定向模型缓存。

为什么要有这条（实测背景，2026-09-21 复核定性）：
`tests/conftest.py` 是 **session 级 autouse**，每个 pytest 会话都换一个全新的
`KS_DATA_DIR`（`%TEMP%\\ks_test_*`）⇒ `models_dir`（默认 `<data_dir>/models`）每次都是空的
⇒ **每一次全量都要重新下载** BGE 权重（~91MB；实测会话目录被填到 748MB）。本机
`ALL_PROXY=http://127.0.0.1:7897` 那个代理半死不活时下载会**挂死**，于是向量通道不可用、
"依赖检索"的用例降级失败 —— 一次**与环境有关、与被测代码无关**的假红。
门禁现在把 `KS_MODELS_DIR` 指到一个**常驻**缓存目录，模型只落地一次。

本文件钉住三件事：① 不设变量时**落到包内**（`<仓>/var/models/ks`，2026-10-18 起）；
② 设了就照办；③ 覆盖**不许**连带改动 `data_dir` / `db_path`
（否则一次"共享模型缓存"会顺手把数据库也搬走）。
"""

from __future__ import annotations

from pathlib import Path

from src.core.config import Settings

#: 包内模型目录 —— 与 `config._default_models_dir` **同一口径**（从本文件位置算，不写死）
_REPO = Path(__file__).resolve().parents[1]


def test_models_dir_defaults_inside_the_bundle(monkeypatch):
    """⚠ 2026-10-18 契约变更：默认从 `<data_dir>/models` 改成**包内**
    `<仓>/var/models/ks`（业主令「不要依赖环境中的其他东西」）。

    改之前的断言是 `Settings().models_dir == Path(tmp_path) / "models"` —— 那钉的是
    **旧契约**。行为**有意**变了，所以测试跟着变（本仓纪律：改了行为就改它的测试并说明为什么）。
    """
    monkeypatch.delenv("KS_MODELS_DIR", raising=False)
    monkeypatch.setenv("KS_DATA_DIR", str("/tmp/whatever"))
    assert Settings().models_dir == _REPO / "var" / "models" / "ks"


def test_models_dir_does_not_follow_data_dir_anymore(monkeypatch, tmp_path):
    """反向钉子：换 `KS_DATA_DIR` **不再**带着模型目录跑。

    这是新契约与旧契约的**分辨点** —— 旧实现下 `models_dir` 恒等于 `<data_dir>/models`，
    本断言会红；新实现下它钉在包内。⇒ 有人把默认值改回去，这条会咬住。
    """
    monkeypatch.delenv("KS_MODELS_DIR", raising=False)
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path / "some-data"))
    assert Settings().models_dir != Path(tmp_path / "some-data") / "models"


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
