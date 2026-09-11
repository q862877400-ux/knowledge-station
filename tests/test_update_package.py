"""批次4：全量数据包导出/导入测试（F-26；pipeline/02 §1 data_package.py）。

覆盖：导出简报计数 == 直接 COUNT、manifest/checksum 结构、公告 PDF 与
quarantine 清单随包、篡改 checksum 拒绝零副作用、manifest 缺失/损坏拒绝、
非空库 UPD-3003 拒绝、strict 空库成功准备 + 同 checksum 幂等拒绝。
全部离线临时目录（conftest KS_DATA_DIR 会话隔离），唯一前缀防共享库串扰。
"""
from __future__ import annotations

import hashlib
import json

import pytest

from src.core.config import get_settings
from src.core.storage.sqlite_db import get_db_connection, init_schema
from src.core.update import change_repo, data_package
from src.core.update.channels.base import UpdateError
from src.core.update.data_package import REGISTRY_KEY, brief_counts
from src.core.update.inspector import get_config as read_config


# ---------------------------------------------------------------- 夹具工具
def _seed_world(prefix: str) -> None:
    """种一套最小业务数据：文档×2（含公告）/条款/批注/收藏/义务/变更事件。"""
    db = get_db_connection()
    db.execute(
        "INSERT INTO doc_meta(doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (f"{prefix}_doc", f"GB/PK {prefix.upper()} 0001-2020", f"标准{prefix}",
         f"S{prefix}", "r1", "[]", f"{prefix}_doc.pdf", f"hash_{prefix}_doc"))
    db.execute(
        "INSERT INTO doc_meta(doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash, doc_type)"
        " VALUES (?,?,?,?,?,?,?,?, 'announcement')",
        (f"{prefix}_ann", f"GOVCN-{prefix}-001", f"公告{prefix}", f"A{prefix}",
         "r1", "[]", f"{prefix}_ann_missing.pdf", f"hash_{prefix}_ann"))
    db.execute(
        "INSERT INTO clause_revision(clause_revision_id, doc_revision_id, doc_id,"
        " clause_key, clause_number, content_text, page_start, page_end)"
        " VALUES (?, 'r1', ?, 'k1', '1.1', '内容', 1, 1)",
        (f"{prefix}_clause", f"{prefix}_doc"))
    db.execute("INSERT INTO user_annotation(annotation_id, clause_key, content)"
               " VALUES (?,?,?)", (f"{prefix}_anno", "k1", "批注"))
    db.execute("INSERT INTO user_bookmark(bookmark_id, clause_key) VALUES (?,?)",
               (f"{prefix}_bm", "k1"))
    db.execute(
        "INSERT INTO legal_obligation(obligation_id, clause_revision_id,"
        " obligation_text) VALUES (?,?,?)",
        (f"{prefix}_obl", f"{prefix}_clause", "应这样做"))
    batch = change_repo.create_batch(trigger="manual", total=1)
    change_repo.append_change({"batch_id": batch["batch_id"],
                               "standard_no": f"GB/PK {prefix.upper()} 0001-2020",
                               "standard_name": f"标准{prefix}",
                               "change_type": "new_version",
                               "source_channel": "official_gb"})
    db.commit()


# ================================================================ PKG-导出
def test_pkg_01_export_brief_counts_match_direct_count(db, tmp_path):
    """导出简报计数与直接 COUNT 一致；manifest 结构完整、checksum 吻合。"""
    _seed_world("p1")
    expected = brief_counts(db)
    assert expected["docs"] >= 2 and expected["announcements"] >= 1

    pkg, manifest = data_package.export_package(tmp_path)
    assert pkg.is_dir() and (pkg / "manifest.json").exists()
    assert (pkg / "knowledge.db").exists()
    assert manifest["format"] == "ks-data-package"
    assert set(manifest["counts"]) == {
        "docs", "clauses", "annotations", "bookmarks",
        "obligations", "changes", "announcements"}
    assert manifest["counts"] == expected, "导出简报计数必须与直接 COUNT 一致"
    digest = hashlib.sha256((pkg / "knowledge.db").read_bytes()).hexdigest()
    assert manifest["db_checksum"] == digest, "db_checksum = 包内快照 SHA-256"
    assert "files/quarantine_manifest.json" in manifest["files"]
    assert json.loads((pkg / "manifest.json").read_text(encoding="utf-8")) == manifest

    # 同目录二次导出：避让重名，简报计数仍一致
    pkg2, manifest2 = data_package.export_package(tmp_path)
    assert pkg2 != pkg
    assert manifest2["counts"] == expected


def test_pkg_02_announcement_pdf_and_quarantine_list(db, tmp_path):
    """公告存档 PDF 随包拷贝；quarantine 只出清单；缺失件记 warning 不阻塞。"""
    pdf_src = tmp_path / "src" / "公告pk2.pdf"
    pdf_src.parent.mkdir()
    pdf_src.write_bytes(b"%PDF-1.4\n% fake announcement archive")
    _seed_world("p2")
    db.execute("UPDATE update_change_event SET archived_pdf_path=?"
               " WHERE standard_no LIKE 'GB/PK P2%'", (str(pdf_src),))
    db.commit()
    qdir = get_settings().data_dir / "quarantine"
    qdir.mkdir(parents=True, exist_ok=True)
    (qdir / "坏件_pk2.bin").write_bytes(b"broken-piece")

    pkg, manifest = data_package.export_package(tmp_path / "out")
    copied = pkg / "files" / "announcements" / "公告pk2.pdf"
    assert copied.exists() and copied.read_bytes() == pdf_src.read_bytes()
    assert "files/announcements/公告pk2.pdf" in manifest["files"]
    # 公告文档自身的 file_path 不存在 → 记 warning 而非失败
    assert any("缺失" in w for w in manifest["warnings"])
    names = [e["name"] for e in manifest["quarantine"]]
    assert "坏件_pk2.bin" in names
    on_disk = json.loads((pkg / "files" / "quarantine_manifest.json")
                         .read_text(encoding="utf-8"))
    assert on_disk == manifest["quarantine"]


# ================================================================ PKG-导入闸门
def test_pkg_03_tampered_checksum_rejected_zero_side_effect(db, tmp_path):
    """篡改 checksum → 拒绝且零副作用：不建保护快照、不写台账。"""
    _seed_world("p3")
    pkg, _manifest = data_package.export_package(tmp_path)
    snaps_before = db.execute("SELECT COUNT(*) FROM snapshot_meta").fetchone()[0]
    docs_before = db.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    reg_before = read_config(REGISTRY_KEY)

    db_file = pkg / "knowledge.db"
    db_file.write_bytes(db_file.read_bytes() + b"\x00tampered-bytes")
    with pytest.raises(UpdateError) as ei:
        data_package.import_package(pkg)
    assert ei.value.code == "package_checksum_mismatch"

    assert db.execute("SELECT COUNT(*) FROM snapshot_meta").fetchone()[0] \
        == snaps_before, "拒绝路径不做备份快照"
    assert db.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0] == docs_before
    assert read_config(REGISTRY_KEY) == reg_before, "台账未写入"


def test_pkg_04_manifest_missing_or_corrupt_rejected(db, tmp_path):
    """manifest 缺失 / 目录无 manifest / JSON 损坏 → 一律 package_manifest_missing。"""
    _seed_world("p4")
    pkg, _manifest = data_package.export_package(tmp_path)
    (pkg / "manifest.json").unlink()
    with pytest.raises(UpdateError) as ei:
        data_package.import_package(pkg)
    assert ei.value.code == "package_manifest_missing"

    empty = tmp_path / "nopkg"
    empty.mkdir()
    with pytest.raises(UpdateError) as ei:
        data_package.import_package(empty)
    assert ei.value.code == "package_manifest_missing"

    (pkg / "manifest.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(UpdateError) as ei:
        data_package.import_package(pkg)
    assert ei.value.code == "package_manifest_missing"


def test_pkg_05_non_empty_target_rejected_upd3003(db, tmp_path):
    """/UPD-3003 目标库非空拒绝；零副作用（连保护性快照都不做）。"""
    _seed_world("p5")  # 保证会话库非空
    pkg, _manifest = data_package.export_package(tmp_path)
    snaps_before = db.execute("SELECT COUNT(*) FROM snapshot_meta").fetchone()[0]
    reg_before = read_config(REGISTRY_KEY)

    with pytest.raises(UpdateError) as ei:
        data_package.import_package(pkg)
    assert ei.value.code == "UPD-3003"
    assert "非空" in str(ei.value)
    assert db.execute("SELECT COUNT(*) FROM snapshot_meta").fetchone()[0] \
        == snaps_before
    assert read_config(REGISTRY_KEY) == reg_before


def test_pkg_06_strict_import_prepared_then_same_checksum_rejected(db, tmp_path):
    """strict 空库成功准备（含自动快照+简报）；同 checksum 第二次导入明示拒绝。"""
    _seed_world("p6")
    pkg, manifest = data_package.export_package(tmp_path)

    scratch = tmp_path / "scratch" / "fresh.db"
    scratch.parent.mkdir()
    init_schema(scratch)
    tconn = get_db_connection(scratch)
    try:
        assert brief_counts(tconn)["docs"] == 0, "演练目标库必须为空库"
        reg_before = read_config(REGISTRY_KEY)
        result = data_package.import_package(pkg, conn=tconn)
        assert result["status"] == "prepared"
        assert result["counts"] == manifest["counts"], "导入简报与导出简报同构同值"
        assert result["db_checksum"] == manifest["db_checksum"]
        assert result["snapshot_id"], "导入前已自动做当前库快照备份"
        assert "restore_package.py" in result["restore_note"], \
            "替换步骤接线到 scripts/restore_package.py 离线恢复 CLI（2026-08-26 P2-②）"
        reg_now = read_config(REGISTRY_KEY)
        assert reg_now != reg_before and manifest["db_checksum"] in reg_now, \
            "成功路径登记 checksum 台账"

        # 幂等保护：同 checksum 包重复导入第二次拒绝并明示
        with pytest.raises(UpdateError) as ei:
            data_package.import_package(pkg, conn=tconn)
        assert ei.value.code == "package_already_imported"
        assert manifest["db_checksum"][:16] in str(ei.value), "错误信息明示 checksum"
    finally:
        tconn.close()


def test_pkg_07_unknown_mode_rejected(db, tmp_path):
    """未知导入模式在触碰任何文件前拒绝。"""
    with pytest.raises(UpdateError) as ei:
        data_package.import_package(tmp_path, mode="merge")
    assert ei.value.code == "package_bad_mode"
