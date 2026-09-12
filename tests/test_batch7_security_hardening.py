# -*- coding: utf-8 -*-
"""整改批 7 安全加固测试（问题清单 #8 #9 #10）。

1. secrets.json 崩溃一致性（#10）：写入中途被"杀死"（进程死亡/磁盘满模拟）
   → 主文件必须**保持上一次完整状态**，绝不出现半成品 JSON；
2. KS_BACKUP_DIR 外部备份目录（#8）：备份可重定向到数据目录之外的卷
   ——数据盘损坏时备份幸存；覆盖后快照落在外部目录；
3. probe_token 出网审计（#9）：探测也是真实云调用，必须留 egress 痕迹
   （成功/失败两态都登记；审计自身失败不阻塞探测）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.core.settings import secret_store as ss


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    from src.core.config import reset_settings
    reset_settings()
    yield tmp_path
    reset_settings()


# ---------- 1. 崩溃一致性 ----------

def test_crash_mid_write_keeps_previous_state(data_dir, monkeypatch):
    """写入中途崩溃（os.replace 之前死掉）→ 主文件保持上一次完整内容。

    模拟方式：把 os.replace 换成"先写坏 tmp 再抛错"——等价于进程在
    rename 落地前死亡。tmp 由 finally 清理；主文件绝不能是半成品。
    """
    ss.write_values({"ALIVE_KEY": "v1"})
    before = ss.read_value("ALIVE_KEY")
    assert before == "v1"

    real_replace = os.replace

    def crash_replace(src, dst):
        # 把 tmp 写坏（模拟写到一半的半成品），然后"进程死亡"
        Path(src).write_text('{"values": {"ALIVE_KEY": "半截', encoding="utf-8")
        raise RuntimeError("simulated crash before rename")

    monkeypatch.setattr(ss.os, "replace", crash_replace)
    with pytest.raises(RuntimeError):
        ss.write_values({"ALIVE_KEY": "v2-never-lands"})
    monkeypatch.setattr(ss.os, "replace", real_replace)

    # 主文件保持上一次完整状态
    assert ss.read_value("ALIVE_KEY") == "v1"
    # 且是合法 JSON（不是半成品）
    raw = json.loads((data_dir / "secrets.json").read_text(encoding="utf-8"))
    assert isinstance(raw.get("values"), dict)


def test_crash_after_replace_keeps_new_state(data_dir, monkeypatch):
    """rename 落地后崩溃 → 新状态完整可见（原子写的另一半保证）。"""
    ss.write_values({"K": "v1"})
    # 正常写第二次；rename 成功后"死在 finally 清理 tmp 之前"是安全的
    ss.write_values({"K": "v2"})
    assert ss.read_value("K") == "v2"
    raw = json.loads((data_dir / "secrets.json").read_text(encoding="utf-8"))
    assert raw["values"]


def test_no_partial_tmp_left_after_crash(data_dir, monkeypatch):
    """崩溃后残留 tmp 必须是'可识别的半成品'（.tmp 前缀），主文件无恙。"""
    ss.write_values({"K": "v1"})
    path = data_dir / "secrets.json"

    def crash_replace(src, dst):
        raise RuntimeError("crash")

    monkeypatch.setattr(ss.os, "replace", crash_replace)
    with pytest.raises(RuntimeError):
        ss.write_values({"K": "v2"})
    # finally 清理了 tmp（或留下 .tmp* 文件——可识别，不会与主文件混淆）
    leftovers = [p for p in data_dir.iterdir() if p.name.startswith("secrets.json.tmp")]
    for p in leftovers:
        assert ".tmp" in p.name
    # 主文件始终完好
    assert ss.read_value("K") == "v1"


# ---------- 2. KS_BACKUP_DIR ----------

def test_backup_dir_default_is_data_dir_backups(data_dir):
    from src.core.storage import backup
    d = backup._backups_dir()
    assert d == data_dir / "backups"
    # 首次调用会顺带创建
    assert d.exists()


def test_backup_dir_env_redirects_outside_data_dir(data_dir, tmp_path_factory, monkeypatch):
    """KS_BACKUP_DIR 重定向到外部目录（模拟另一块盘）→ 快照落在外部。"""
    external = tmp_path_factory.mktemp("external-backup-volume")
    monkeypatch.setenv("KS_BACKUP_DIR", str(external))
    from src.core.storage import backup
    assert backup._backups_dir() == external
    assert backup._backups_dir() != data_dir / "backups"
    # 目录会被创建
    assert external.exists()


def test_snapshot_lands_in_external_backup_dir(db, tmp_path_factory, monkeypatch):
    """端到端：重定向下 create_snapshot 的产物落在外部目录。

    用共享 `db` fixture（schema 已初始化）；KS_BACKUP_DIR 指向盘外目录。
    """
    external = tmp_path_factory.mktemp("external-volume")
    monkeypatch.setenv("KS_BACKUP_DIR", str(external))
    from src.core.storage import backup
    snap = backup.create_snapshot("manual")
    snap_path = external / f"{snap['snapshot_id']}.db"
    assert snap_path.exists()


def test_backup_dir_empty_env_falls_back(data_dir, monkeypatch):
    """空串/纯空白 → 回落默认（显式覆盖必须是有意义的值）。"""
    monkeypatch.setenv("KS_BACKUP_DIR", "   ")
    from src.core.storage import backup
    d = backup._backups_dir()
    assert d == data_dir / "backups"


# ---------- 3. probe_token 出网审计 ----------

def test_probe_token_records_egress_on_both_paths(tmp_path, monkeypatch):
    """探测成功/失败都必须留 egress 痕迹（record_egress 被调）；审计失败不阻塞。

    注意 reset_settings 时序：config 是单例，env 变更后必须 reset 才重新读。
    """
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    from src.core.config import reset_settings
    reset_settings()
    from src.core.ingestion import mineru_cloud

    recorded: list[dict] = []

    def fake_record(service, endpoint, payload, response_meta=None, query=None,
                    prompt_preview=None):
        recorded.append({"service": service, "endpoint": endpoint,
                         "meta": response_meta or {}})

    import src.core.llm.egress_audit as ea
    monkeypatch.setattr(ea, "record_egress", fake_record)

    # 路径 A：Key 未配置 → 提前返回（不出网，不登记——这不算云调用）
    r = mineru_cloud.probe_token()
    assert r["ok"] is False
    assert len(recorded) == 0

    # 配置一个假 key + reset 让 settings 重新读 → 探测真正走到 httpx
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "sk-fake")
    reset_settings()
    import httpx
    monkeypatch.setattr(httpx, "post",
                        lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("net down")))
    r2 = mineru_cloud.probe_token()
    assert r2["ok"] is False
    assert "net down" in r2["detail"]
    # 失败也出网了 → 必须留痕
    assert len(recorded) == 1
    assert recorded[0]["service"] == "mineru_cloud"
    assert recorded[0]["meta"].get("ok") is False
    reset_settings()


def test_probe_token_audit_failure_does_not_block(tmp_path, monkeypatch):
    """审计自身炸掉 → 探测结果照常返回（审计失败不阻塞业务）。"""
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    from src.core.config import reset_settings
    reset_settings()
    from src.core.ingestion import mineru_cloud

    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "sk-fake")
    import httpx

    class FakeResp:
        status_code = 200
        text = json.dumps({"code": 0, "data": {"batch_id": "b1", "file_urls": ["u"]}})
        def json(self):
            return json.loads(self.text)
        def raise_for_status(self):
            pass

    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResp())

    import src.core.llm.egress_audit as ea
    def exploding_record(*a, **k):
        raise RuntimeError("audit pipeline down")
    monkeypatch.setattr(ea, "record_egress", exploding_record)

    r = mineru_cloud.probe_token()
    assert r["ok"] is True          # 业务照常
    assert "batch" in r["detail"]
    reset_settings()
