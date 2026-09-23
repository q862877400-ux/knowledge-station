"""重导（「重来一次」）**不许把用户的整理成果弄丢**（2026-09-24 审计 A1，P0）。

## 这一组在守什么

审计 A1 的四处代码实证：重导会**新开一个 ``doc_id``、删掉旧文档**，但

* 旧 doc_id 上"在哪些目录里"（``folder_member``，多对多）**没有搬到**新 doc_id；
* ``delete_document`` / ``delete_documents`` **也不清**旧 doc_id 的 ``folder_member`` /
  ``doc_filing_state``；
* 而 ``schema.sql`` 里 ``folder_member.item_id`` 是**多态列 ⇒ 没有表级 FK** ⇒ 没有级联兜底。

⇒ 用户点一次「重新解析」，那篇文件就从它被归位的目录里**消失**（同时库里留下
一排指向不存在文档的悬空挂靠行）。本组判据四条，**每条都有反向**：

1. 重导后新 doc_id 的**归属集合 == 旧集合**（多对多，一条不少、一条不多）；
2. 删除文档后**没有悬空挂靠 / 悬空状态行**（两条删除路各判一次）；
3. **反向**：不属于它的挂靠**一条都不许动**（别人的归属、目录与目录之间的边、别的状态行）；
4. **目录"篇数"不虚增**（``list_folder`` 的 ``files_total`` / ``file_count_direct``）。

另有一组钉住 ``doc_filing_state`` 的搬运口径（``stage`` 必须说**这一次**的实话）：

* 已归位的那篇重导成功 ⇒ 仍是 ``filed``、归位记录（``placed_*``）逐字还在；
* 待确认的那篇重导成功 ⇒ ``confirming``（**不许**被钉在「识别中」，那是重导自己的标记）；
* 旧行是 ``failed``、这次解析成功 ⇒ **不许**照搬回 ``failed``（一次成功的重解析被盖住）；
* 已归位的那篇这次解析失败（正文为零）⇒ ``failed``（不假装成功）+ 归属照旧搬过去。

⚠ 全部在**本模块私有**的临时数据目录里跑：真库 2.2 GB / 6417 篇，一根手指都不碰。
⚠ 解析器换成**合成 blocks**（``monkeypatch`` 掉 ``run_parser_isolated``）：本组验的是
   **换 doc_id 时的搬运与清理**，不是 MinerU（不换的话每条用例要跑一次真解析，几分钟起）。
   真链路其余部分一字未动：``split_items_into_clauses`` → ``build_clause_models`` → 真入库事务。
"""
from __future__ import annotations

import itertools
import os
import tempfile
from pathlib import Path

import fitz
import pytest

from src.core.ingestion import parser_worker
from src.core.ingestion import pipeline as pipeline_mod
from src.core.knowledge import folder_store as fs
from src.core.storage import clause_repo
from src.core.storage.doc_delete import delete_documents


@pytest.fixture(scope="module", autouse=True)
def _own_data_dir():
    """**本模块私有的临时数据目录**（跑完即弃，其他模块零影响）。

    做法与 ``tests/test_filing_state_pipeline.py`` 那份先例逐字同源：module 级 = 本模块内
    等效独立运行，且不会在会话中途把全局 ``KS_DATA_DIR`` 改掉影响别的模块。
    """
    with tempfile.TemporaryDirectory(prefix="ks_keepfiling_", ignore_cleanup_errors=True) as td:
        old = os.environ.get("KS_DATA_DIR")
        os.environ["KS_DATA_DIR"] = td
        from src.core import config
        config.reset_settings()
        # 默认连接缓存的 key 固定是 "conn_default"（不看路径）：前序模块可能已把该线程连接
        # 指向旧库 ⇒ 清掉，让本模块在新数据目录上重连。
        from src.core.storage.sqlite_db import close_thread_connection
        close_thread_connection()
        yield Path(td)
        config.reset_settings()
        close_thread_connection()
        if old is None:
            os.environ.pop("KS_DATA_DIR", None)
        else:
            os.environ["KS_DATA_DIR"] = old


#: 一页够切出真条款的正文（条款号 + 中文正文）。
REAL_BLOCKS = [
    "1 范围",
    "本标准规定了危险化学品企业特殊作业的安全要求。",
    "2 规范性引用文件",
    "下列文件对于本文件的应用是必不可少的。",
    "3 术语和定义",
    "3.1 特殊作业 指在生产经营过程中可能对操作者造成伤害的作业。",
    "4 基本要求",
    "4.1 作业前应进行风险辨识并办理作业审批手续。",
]
#: 一页"一个字都没提出来"的正文（盗版站水印那种）⇒ 入库判 ``failed``。
WATERMARK_BLOCKS = ["学兔兔 www.bzfxw.com", "学兔兔 www.bzfxw.com"]


def _write_pdf(path: Path, first_line: str) -> Path:
    """一页真实 PDF（只为了让 ``run_full_ingest`` 的前置检查有文件可开）。"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), first_line)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def synthetic_parser(monkeypatch):
    """把 ``run_parser_isolated`` 换成**给定 blocks 的合成结果**（真链路，只有解析这一步是假的）。"""
    def _install(blocks: list[str]) -> None:
        def _fake(pdf_path, output_dir, timeout=900, force_deep=False, deep_fallback=True):
            return {
                "blocks": [{"text": t, "page_number": 1, "bbox": [60.0, 600.0, 530.0, 720.0]}
                           for t in blocks],
                "geometries": {1: {"width": 595.0, "height": 842.0, "rotation": 0}},
                "deep_output": None,
                "is_ocr": False,
            }
        monkeypatch.setattr(pipeline_mod, "run_parser_isolated", _fake)
        monkeypatch.setattr(parser_worker, "run_parser_isolated", _fake)
    return _install


@pytest.fixture(autouse=True)
def _offline_embedder(monkeypatch):
    """向量引擎强制离线（不打的实测后果：真加载会去 huggingface **下模型**，用例挂在网络等待里）。"""
    from src.core.retrieval import embedder as _emb
    monkeypatch.setattr(_emb, "is_available", lambda: False)
    yield


_seq = itertools.count(1)


def _uniq_no() -> str:
    """本模块唯一的标准号（``doc_meta.standard_no`` 有唯一约束）。"""
    return f"GB/T 93{next(_seq):03d}-2021"


def _mkfolder(base: str) -> str:
    """建一个本模块唯一的目录（同名同层会被两条部分唯一索引拒绝）。"""
    return fs.create_folder(f"{base}-{next(_seq)}", None)["folder_id"]


def _new_pdf(tmp_path: Path, name: str) -> Path:
    return _write_pdf(tmp_path / name, f"GB/T 93{next(_seq):03d}-2021")


def _members_of(doc_id: str, db) -> set[str]:
    return {r[0] for r in db.execute(
        "SELECT folder_id FROM folder_member WHERE item_kind='file' AND item_id=?",
        (doc_id,))}


def _file_member_rows(db) -> set[tuple[str, str]]:
    """全库"文件挂在哪"的行（用于反向判据：不许动不属于它的那些）。"""
    return {(r[0], r[1]) for r in db.execute(
        "SELECT folder_id, item_id FROM folder_member WHERE item_kind='file'")}


# ═════════════ 判据 ①③④：重导后归属集合相等、别人的一条不动、篇数不虚增 ═════════════

def test_reingest_moves_every_membership_and_touches_nothing_else(db, tmp_path, synthetic_parser):
    """重导一篇归在两个目录里的文件 ⇒ 新 doc_id 的归属集合 == 旧集合；别人的一条不动。"""
    synthetic_parser(REAL_BLOCKS)
    pdf = _new_pdf(tmp_path, "carry.pdf")
    no = _uniq_no()
    out = pipeline_mod.run_full_ingest(pdf, no, "搬运用例的原文档")
    assert out["status"] == "ok", out
    old_doc = out["doc_id"]

    a, b, c = _mkfolder("搬运A"), _mkfolder("搬运B"), _mkfolder("搬运C")
    fs.mark_filed(old_doc, a, placed_by="local-user")          # 主归位（写 placed_*）
    fs.add_member(b, "file", old_doc)                          # 多对多的第二处归属

    # 反向用的"别人的东西"：两篇别的文档各自归位（其中一篇与它同目录 a）
    other1 = _mv_doc(db, "carry_other1")
    other2 = _mv_doc(db, "carry_other2")
    fs.add_member(a, "file", other1)
    fs.add_member(c, "file", other2)
    fs.set_filing_state(other1, "confirming")
    fs.set_filing_state(other2, "filed", placed_folder_id=c)
    decoys_before = _file_member_rows(db) - {(a, old_doc), (b, old_doc)}
    states_before = {other1: fs.get_filing_state(other1), other2: fs.get_filing_state(other2)}

    old_members = _members_of(old_doc, db)
    assert old_members == {a, b}, old_members
    files_total_a_before = fs.list_folder(a)["files_total"]
    assert files_total_a_before == 2                          # 本篇 + other1
    # 目录"篇数"的那个出口（顶层每个目录的直接/含深层篇数）
    counts_before = {s["folder_id"]: (s["file_count_direct"], s["file_count_deep"])
                     for s in fs.list_folder(None)["subfolders"]}

    # ── 重导（同一份文件、同一个标准号；reingest=True 会新开 doc_id 并删旧文档）──
    out2 = pipeline_mod.run_full_ingest(pdf, no, "搬运用例的重导文档", reingest=True)
    assert out2["status"] == "ok" and out2["reingested"] is True, out2
    new_doc = out2["doc_id"]
    assert new_doc != old_doc
    carried = out2["filing_assets_carried"]
    assert carried is not None, "重导必须给出搬运结果（None = 一条都没搬）"
    assert carried["moved_members"] == 2, carried

    # ① 归属集合 == 旧集合（一条不少、一条不多）
    assert _members_of(new_doc, db) == old_members, (_members_of(new_doc, db), old_members)
    # ② 旧 doc_id 上一条都不留（悬空挂靠）
    assert _members_of(old_doc, db) == set()
    assert fs.get_filing_state(old_doc) is None, "旧文档的状态行没清掉（悬空状态行）"
    # ③ 反向：别人的挂靠与状态行一条都不许动
    assert _file_member_rows(db) - {(a, new_doc), (b, new_doc)} == decoys_before
    for did, st_before in states_before.items():
        assert fs.get_filing_state(did) == st_before, f"{did} 的状态行被重导搅动了"
    # ④ 目录篇数不虚增（重导前后同一个数；`list_folder` 是界面读的那个出口）
    assert fs.list_folder(a)["files_total"] == files_total_a_before
    assert fs.list_folder(b)["files_total"] == 1
    counts_after = {s["folder_id"]: (s["file_count_direct"], s["file_count_deep"])
                    for s in fs.list_folder(None)["subfolders"]}
    assert counts_after[a] == counts_before[a], (counts_after[a], counts_before[a])
    assert counts_after[b] == counts_before[b], (counts_after[b], counts_before[b])
    assert counts_after[c] == counts_before[c], (counts_after[c], counts_before[c])
    # 归位记录（placed_*）逐字搬过来 —— 用户的"谁在什么时候放进了哪个目录"
    st = fs.get_filing_state(new_doc)
    assert st is not None and st["placed_folder_id"] == a and st["placed_by"] == "local-user"
    assert st["placed_at"] is not None
    # 已归位的那篇重导成功之后**仍然是**已归位（不许掉回「待确认」）
    assert st["stage"] == "filed", st


def _mv_doc(db, doc_id: str) -> str:
    """插一篇最小可用的文档行（只为了有归属主体）。"""
    db.execute(
        "INSERT OR IGNORE INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES (?,?,?,?,'r1','[]','a.pdf',?)",
        (doc_id, doc_id, f"名-{doc_id}", doc_id, f"h-{doc_id}"))
    db.commit()
    return doc_id


# ═════════════ 判据 ②：两条删除路都不许留悬空挂靠 / 悬空状态行 ═════════════

def test_both_delete_paths_clear_membership_and_state(db):
    """``clause_repo.delete_document``（单篇）与 ``doc_delete.delete_documents``（批量）
    都必须把这一篇的挂靠与状态行清掉；**别人的**（含目录与目录之间的边）一条不动。"""
    d1 = _mv_doc(db, "del_keep_1")
    d2 = _mv_doc(db, "del_keep_2")
    keep = _mv_doc(db, "del_keep_3")
    f1, f2 = _mkfolder("删A"), _mkfolder("删B")
    for d in (d1, d2):
        fs.add_member(f1, "file", d)
        fs.set_filing_state(d, "confirming")
    fs.add_member(f1, "file", keep)
    fs.add_member(f2, "file", keep)
    fs.set_filing_state(keep, "filed", placed_folder_id=f1)
    # 目录与目录之间的边（item_kind='folder'）：**一个字都不许动**
    sub = fs.create_folder("删A子", f1)["folder_id"]
    folder_edges_before = {(r[0], r[1]) for r in db.execute(
        "SELECT folder_id, item_id FROM folder_member WHERE item_kind='folder'")}
    # ⚠ 库是**本模块共用**的（module 级临时数据目录）⇒ 反向判据不能拿"全库等于某两行"来判，
    #   要比**删除前后差集恰好是目标那几行**（否则同模块别的用例留下的行会把它判假红）。
    rows_before = _file_member_rows(db)
    assert {(f1, keep), (f2, keep)} <= rows_before

    clause_repo.delete_document(d1)
    assert _members_of(d1, db) == set(), "单篇删除留下了悬空挂靠"
    assert fs.get_filing_state(d1) is None, "单篇删除留下了悬空状态行"
    assert rows_before - _file_member_rows(db) == {(f1, d1)}, "单篇删除动了不属于它的挂靠"

    delete_documents([d2])
    assert _members_of(d2, db) == set(), "批量删除留下了悬空挂靠"
    assert fs.get_filing_state(d2) is None, "批量删除留下了悬空状态行"
    assert rows_before - _file_member_rows(db) == {(f1, d1), (f1, d2)}, \
        "批量删除动了不属于它的挂靠"

    # 反向：别人的挂靠与状态行原样；目录边原样
    assert {(f1, keep), (f2, keep)} <= _file_member_rows(db)
    assert fs.get_filing_state(keep)["stage"] == "filed"
    assert fs.list_folder(f1)["files_total"] == 1 and fs.list_folder(f2)["files_total"] == 1
    assert {(r[0], r[1]) for r in db.execute(
        "SELECT folder_id, item_id FROM folder_member WHERE item_kind='folder'")} \
        == folder_edges_before
    assert db.execute("SELECT COUNT(*) FROM folder WHERE folder_id=?", (sub,)).fetchone()[0] == 1


# ═════════════ doc_filing_state 的搬运口径（stage 说这一次的实话） ═════════════

def test_reingest_keeps_failed_old_state_from_smearing_a_success(db, tmp_path, synthetic_parser):
    """旧行是 ``failed``、这次解析成功 ⇒ 新行**不许**还是 ``failed``（也不许停在 recognizing）。"""
    synthetic_parser(WATERMARK_BLOCKS)
    pdf = _new_pdf(tmp_path, "wasbad.pdf")
    no = _uniq_no()
    first = pipeline_mod.run_full_ingest(pdf, no, "先入库的水印页")
    assert first["catalog_hidden"] is True
    assert fs.get_filing_state(first["doc_id"])["stage"] == "failed"

    synthetic_parser(REAL_BLOCKS)
    out = pipeline_mod.run_full_ingest(pdf, no, "重导后的真标准", reingest=True)
    assert out["status"] == "ok", out
    st = fs.get_filing_state(out["doc_id"])
    assert st["stage"] == "confirming", f"成功的重解析被盖回 {st['stage']}（照搬旧 stage 的形态）"
    assert st["failure_kind"] is None, st


def test_reingest_of_failed_parse_marks_failed_even_when_membership_carried(
        db, tmp_path, synthetic_parser):
    """已归位的那篇这次解析**失败**（正文为零）⇒ ``failed``（不假装成功），归属照旧搬过去。"""
    synthetic_parser(REAL_BLOCKS)
    pdf = _new_pdf(tmp_path, "wasgood.pdf")
    no = _uniq_no()
    first = pipeline_mod.run_full_ingest(pdf, no, "先入库的正常标准")
    assert first["status"] == "ok" and first["catalog_hidden"] is False
    f = _mkfolder("失败也搬")
    fs.mark_filed(first["doc_id"], f)

    synthetic_parser(WATERMARK_BLOCKS)
    out = pipeline_mod.run_full_ingest(pdf, no, "重导后正文为零", reingest=True)
    assert out["status"] == "ok" and out["catalog_hidden"] is True, out
    assert _members_of(out["doc_id"], db) == {f}, "解析失败就不搬归属了？归属与解析成败无关"
    st = fs.get_filing_state(out["doc_id"])
    assert st["stage"] == "failed", st
    assert st["placed_folder_id"] == f, "归位记录丢了"


def test_no_carry_without_an_old_document(db, tmp_path, synthetic_parser):
    """**反向哨兵**：没有旧文档可替换（全新标准号 / 普通入库）⇒ 一条都不搬。"""
    synthetic_parser(REAL_BLOCKS)
    pdf = _new_pdf(tmp_path, "fresh.pdf")
    out = pipeline_mod.run_full_ingest(pdf, _uniq_no(), "全新的一篇")
    assert out["status"] == "ok"
    assert out["filing_assets_carried"] is None, "没有旧文档却报了搬运结果（数字是编的）"
    assert _members_of(out["doc_id"], db) == set()


def test_restore_refuses_a_missing_target_and_is_idempotent(db):
    """原地判 ``restore_filing_assets``：目标文档不存在 ⇒ ``doc_not_found``（**且什么都没写**）；
    同一条归属重复搬 ⇒ 第二次不再新增（篇数不虚增）。"""
    from src.core.exceptions import KnowledgeStationError

    d = _mv_doc(db, "restore_src")
    f = _mkfolder("原地判")
    fs.add_member(f, "file", d)
    snap = fs.snapshot_filing_assets(d)
    assert snap["members"] == [f]

    with pytest.raises(KnowledgeStationError) as ei:
        fs.restore_filing_assets(snap, "restore_missing_target", stage="confirming")
    assert "doc_not_found" in str(getattr(ei.value, "code", "") or ei.value)
    assert _members_of("restore_missing_target", db) == set(), "目标不存在却写了挂靠行"

    fs.restore_filing_assets(snap, d, stage="confirming")
    again = fs.restore_filing_assets(snap, d, stage="confirming")
    assert again["moved_members"] == 0, "重复搬同一条归属会虚增篇数"
    assert _members_of(d, db) == {f}
    # 快照是只读的：拍快照不改库里的状态行（口径与 plan_reingest 一致）
    before = fs.get_filing_state(d)
    fs.snapshot_filing_assets(d)
    assert fs.get_filing_state(d) == before


# ═════════════ 复核打回 1/2（2026-09-24）：失败要说出来 / 已删目录不许插悬空行 ═════════════

def test_carry_failure_is_reported_not_silent(db, tmp_path, synthetic_parser, monkeypatch):
    """搬运**失败**必须与"没有旧文档要搬"分得开（``filing_assets_carry_error`` 非空）。

    ⚠ 为什么单独一条：``filing_assets_carried is None`` 有两种含义，把它们混成一种
    就是"把失败说成没有"——本仓明令禁止的假话形态。
    """
    synthetic_parser(REAL_BLOCKS)
    pdf = _new_pdf(tmp_path, "carryboom.pdf")
    no = _uniq_no()
    first = pipeline_mod.run_full_ingest(pdf, no, "搬运会炸的原文档")
    assert first["status"] == "ok"
    f = _mkfolder("搬运炸")
    fs.mark_filed(first["doc_id"], f)

    def _boom(*a, **kw):
        raise RuntimeError("搬运炸了（本用例故意打断）")

    # ⚠ 用 `monkeypatch.context()`（不是 `undo()`）：undo 会把夹具打的补丁
    #   （合成解析器 + 强制离线向量引擎）一起撤掉 ⇒ 反向那一跑会去跑真解析/真下模型。
    with monkeypatch.context() as m:
        m.setattr(fs, "restore_filing_assets", _boom)
        out = pipeline_mod.run_full_ingest(pdf, no, "搬运会炸的重导", reingest=True)
        assert out["status"] == "ok", out      # 搬运失败**不许**把一次成功的入库变成失败
        assert out["filing_assets_carried"] is None
        err = out["filing_assets_carry_error"]
        assert err and "RuntimeError" in err and "搬运炸了" in err, \
            f"搬运失败被静默成『没有要搬的』：{err!r}"
    # 反向：同一套流程、这次不炸 ⇒ 两个字段反过来（carried 有值、error 为 None）
    f2 = _mkfolder("搬运正常")
    fs.mark_filed(out["doc_id"], f2)
    ok = pipeline_mod.run_full_ingest(pdf, no, "搬运正常的一跑", reingest=True)
    assert ok["filing_assets_carried"] is not None, ok.get("filing_assets_carry_error")
    assert ok["filing_assets_carried"]["moved_members"] == 1, ok["filing_assets_carried"]
    assert ok["filing_assets_carry_error"] is None, ok["filing_assets_carry_error"]


def test_restore_skips_folders_deleted_after_the_snapshot(db):
    """拍快照之后、落盘之前目录被删掉 ⇒ **不插**那条悬空挂靠；其余照搬、计数如实。

    ⚠ 为什么可能发生：``folder_member`` **表级没有任何 FK**（见 schema.sql 那段），
    而拍快照到落盘之间隔着一次真入库事务（几十秒起）—— 这期间用户删掉那个目录，
    照原样插进去就是一条指向不存在目录的行（本批要消灭的那一类悬空行）。
    """
    src = _mv_doc(db, "stale_src")
    dst = _mv_doc(db, "stale_dst")
    keep, gone = _mkfolder("还在的目录"), _mkfolder("快照后被删的目录")
    fs.add_member(keep, "file", src)
    fs.add_member(gone, "file", src)
    snap = fs.snapshot_filing_assets(src)
    assert set(snap["members"]) == {keep, gone}

    # 目录行没了（= 快照之后被删；带成员行一起删，与 folder_store 真删目录的形态一致）
    db.execute("DELETE FROM folder WHERE folder_id=?", (gone,))
    db.execute("DELETE FROM folder_member WHERE folder_id=?", (gone,))
    db.commit()

    out = fs.restore_filing_assets(snap, dst, stage="confirming")
    assert out["missing_folders"] == [gone], out
    assert out["skipped_missing_folders"] == 1, out
    assert out["moved_members"] == 1, out
    assert _members_of(dst, db) == {keep}, "把已删目录的挂靠行插进去了（悬空挂靠）"
    # stage：**真的搬成了**一条归属 ⇒ 仍是「已归位」；一条都没搬成才退回这一次的结论
    assert out["stage"] == "filed", out
    fs.restore_filing_assets(snap, src, stage="confirming")   # 反向：源文档自己不受影响
    assert _members_of(src, db) == {keep}


def test_restore_says_the_truth_when_every_folder_was_deleted(db):
    """快照里的目录**全被删** ⇒ 一条都没搬成 ⇒ **不许**说它还归位在某个目录里。

    ⚠ 这条是独立复核对 `0b05841` 的打回（2026-09-24，MED）：那一笔把 `final_stage` 从
    "看快照里有几条归属"改成"看**真的搬成了几条**"（`folder_store.restore_filing_assets`
    的 `moved`），但**这半个改动当时没有任何判据看管** —— 复核把它换回 `members` 时
    **8 条用例全过、退出码 0**。原因是上一条用例只覆盖"**部分**目录被删"（那一跑 `moved=1`，
    两种写法同判 `filed`）；唯一能把两者分开的形态是**目录全被删**（`moved=0`），而它没人造。
    ⇒ 本条补的正是那一种。判据：① 返回值与**落库**的 stage 都必须是这一次的结论；
    ② 一条挂靠行都不许插进去；③ 再搬一次仍如实（幂等）。
    """
    src = _mv_doc(db, "allgone_src")
    dst = _mv_doc(db, "allgone_dst")
    f1, f2 = _mkfolder("全删A"), _mkfolder("全删B")
    fs.add_member(f1, "file", src)
    fs.add_member(f2, "file", src)
    snap = fs.snapshot_filing_assets(src)
    assert set(snap["members"]) == {f1, f2}, snap

    # 快照之后两个目录都被删（带成员行一起删，与 folder_store 真删目录的形态一致）
    for fid in (f1, f2):
        db.execute("DELETE FROM folder WHERE folder_id=?", (fid,))
        db.execute("DELETE FROM folder_member WHERE folder_id=?", (fid,))
    db.commit()

    out = fs.restore_filing_assets(snap, dst, stage="confirming")
    assert out["moved_members"] == 0, out
    assert out["skipped_missing_folders"] == 2, out
    assert set(out["missing_folders"]) == {f1, f2}, out
    assert _members_of(dst, db) == set(), "目录全没了还往 folder_member 里插行（悬空挂靠）"
    assert out["stage"] == "confirming", (
        f"一条归属都没搬成，却仍报 {out['stage']!r} —— 「已归位」必须看**真搬成了几条**"
        "（把 moved 换回 members 会在这里红）")
    assert fs.get_filing_state(dst)["stage"] == "confirming", "落库的 stage 与返回值不一致"

    # 幂等：同一条快照再搬一次，仍然一条都搬不成、仍说这一次的结论
    again = fs.restore_filing_assets(snap, dst, stage="confirming")
    assert again["moved_members"] == 0 and again["stage"] == "confirming", again
    assert _members_of(dst, db) == set()

