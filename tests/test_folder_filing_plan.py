"""归位计划与预览清单的用例（KB-FOLDER-PLAN §五第 1 步）。

全部用**小 fixture 库**（`db` fixture = `KS_DATA_DIR` 下的临时库），绝不碰真库。
覆盖：分类→目录映射必须与 `classify_document` 同源、无分类进「待分类」不建目录、
含更深层计数、异常不静默塞目录、计划可重复、清单含业主点名要的几段。
"""
from __future__ import annotations

import itertools

from src.core.knowledge import folder_filing_plan as fp
from src.core.knowledge.doc_catalog import classify_document

_seq = itertools.count()


def nm(base: str) -> str:
    return f"{base}-{next(_seq)}"


def doc(doc_id: str, std: str, name: str, tags, *, hierarchy=None,
        doc_type="standard", hidden=0) -> dict:
    import json
    return {"doc_id": doc_id, "standard_no": std, "standard_name": name,
            "legal_hierarchy": hierarchy, "doc_type": doc_type,
            "domain_tags": tags if isinstance(tags, str) else json.dumps(tags),
            "catalog_hidden": hidden}


def paths_of(plan: dict) -> set[tuple[str, ...]]:
    return {tuple(n["path"]) for n in plan["nodes"]}


# ─────────────────────────── 分类 → 目录映射 ───────────────────────────

def test_plan_uses_the_same_classification_as_the_catalog():
    """**接线断言**：计划给的路径必须就是 `classify_document` 那四级，
    （不许在计划里另写一份判断——两份判断迟早漂移，"预览说进 A、真跑进 B"最坏）。"""
    d = doc("ffp1", "GB 50016-2014", "建筑设计防火规范", ["CCS:P16 工程防火"])
    plan = fp.plan_filing([d])
    expect_path = fp.path_of(classify_document({**d, "domain_tags": ["CCS:P16 工程防火"]}))
    assert tuple(plan["assignments"][0]["path"]) == expect_path
    assert paths_of(plan) == {expect_path[:1], expect_path[:2], expect_path[:3], expect_path}
    # 每一级都是一个目录节点，且篇数=含更深层
    for n in plan["nodes"]:
        assert n["docs_deep"] == 1
    assert plan["nodes"][-1]["docs_direct"] == 1


def test_plan_puts_unclassified_into_pending_without_folders():
    docs = [
        doc("ffp_u1", "GB/T 99999-2020", "某无分类标准", []),          # 其他标准
        doc("ffp_u2", "某通知", "某未定级法规", [], hierarchy="不存在的层级",
            doc_type="法律法规"),                                        # 未定级
        doc("ffp_ok", "GB 50017-2017", "钢结构设计标准", ["CCS:P16 工程防火"]),
    ]
    plan = fp.plan_filing(docs)
    assert [x["doc_id"] for x in plan["no_class"]] == ["ffp_u1", "ffp_u2"]
    assert {x["bucket"] for x in plan["no_class"]} == {"其他标准", "未定级"}
    assert all(x["reason"] for x in plan["no_class"])       # 每篇都要有成因话术
    assert plan["planned_docs"] == 1
    # 无分类的那些**不许**出现在任何目录路径里，也不许建它们的目录
    all_segs = {seg for p in paths_of(plan) for seg in p}
    assert "其他标准" not in all_segs and "未定级" not in all_segs
    assert plan["anomalies"] == []
    s = fp.summarize_plan(plan)
    assert s["no_class_total"] == 2
    assert s["no_class_by_bucket"] == {"其他标准": 1, "未定级": 1}
    assert s["planned_docs"] == 1


def test_plan_excludes_hidden_docs():
    docs = [doc("ffp_h", "GB 50017-2017", "隐藏", ["CCS:P16 工程防火"], hidden=1),
            doc("ffp_v", "GB 50017-2017", "可见", ["CCS:P16 工程防火"])]
    plan = fp.plan_filing(docs)
    assert plan["hidden_docs"] == ["ffp_h"]
    assert plan["planned_docs"] == 1
    assert fp.summarize_plan(plan)["hidden_docs"] == 1


def test_plan_deep_and_direct_counts():
    docs = [doc(f"ffp_d{i}", f"GB 500{i}-2017", f"标准{i}", ["CCS:P16 工程防火"])
            for i in range(3)]
    plan = fp.plan_filing(docs)
    by_path = {tuple(n["path"]): n for n in plan["nodes"]}
    l4 = [n for n in plan["nodes"] if n["depth"] == 4]
    assert len(l4) == 1 and l4[0]["docs_direct"] == 3 and l4[0]["docs_deep"] == 3
    l1 = by_path[(l4[0]["path"][0],)]
    assert l1["docs_deep"] == 3 and l1["docs_direct"] == 0


def test_plan_records_anomalies_instead_of_guessing(monkeypatch):
    """值为空 / 名字超上限 ⇒ 进 anomalies，**不**静默塞进某个目录。"""
    monkeypatch.setattr(fp, "classify_document",
                        lambda d: {"top": "std", "top_name": "T", "level2": "L2",
                                   "level3": "L3", "level4": "  ", "order": 2})
    plan = fp.plan_filing([doc("ffp_a1", "GB 1-2020", "x", [])])
    assert plan["planned_docs"] == 0 and plan["nodes"] == []
    assert [a["kind"] for a in plan["anomalies"]] == ["empty_level"]

    monkeypatch.setattr(fp, "classify_document",
                        lambda d: {"top": "std", "top_name": "T",
                                   "level2": "X" * (fp.folder_store.MAX_NAME_LEN + 1),
                                   "level3": "L3", "level4": "L4", "order": 2})
    plan = fp.plan_filing([doc("ffp_a2", "GB 1-2020", "x", [])])
    assert plan["planned_docs"] == 0
    assert [a["kind"] for a in plan["anomalies"]] == ["name_too_long"]
    assert "上限" in plan["anomalies"][0]["detail"]


def test_plan_duplicate_and_missing_ids_are_anomalies():
    docs = [doc("ffp_dup", "GB 1-2020", "x", ["CCS:P16 工程防火"]),
            doc("ffp_dup", "GB 2-2020", "y", ["CCS:P16 工程防火"]),
            {"standard_no": "GB 3-2020"}]
    plan = fp.plan_filing(docs)
    kinds = sorted(a["kind"] for a in plan["anomalies"])
    assert kinds == ["duplicate_doc_id", "missing_doc_id"]
    assert plan["planned_docs"] == 1


def test_plan_is_repeatable():
    docs = [doc("ffp_r1", "GB 50016-2014", "防火", ["CCS:P16 工程防火"]),
            doc("ffp_r2", "GB/T 99999-2020", "无分类", [])]
    a = fp.plan_filing(docs)
    b = fp.plan_filing(docs)
    assert a == b


# ─────────────────────────── 落到小 fixture 库 ───────────────────────────

def _insert(db, d: dict) -> None:
    db.execute(
        "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash, legal_hierarchy, doc_type)"
        " VALUES (?,?,?,?,'r1',?,?,?,?,?)",
        (d["doc_id"], d["standard_no"], d["standard_name"], d["doc_id"],
         d["domain_tags"], "a.pdf", f"h-{d['doc_id']}", d["legal_hierarchy"], d["doc_type"]))
    db.commit()


def test_apply_plan_on_small_fixture_db(db):
    """小 fixture 库上真跑一遍：目录树、归属、状态、含更深层计数都读得回来。"""
    from src.core.knowledge import folder_store as fs
    docs = [
        doc(f"ffp_ap_a", "GB 50016-2014", "建筑设计防火规范", ["CCS:P16 工程防火"]),
        doc(f"ffp_ap_b", "GB 50017-2017", "钢结构设计标准", ["CCS:P16 工程防火"]),
        doc(f"ffp_ap_c", "GB/T 99999-2020", "无分类的", []),
    ]
    for d in docs:
        _insert(db, d)
    mine = [dict(r) for r in db.execute(
        "SELECT doc_id, standard_no, standard_name, legal_hierarchy, doc_type,"
        " domain_tags, catalog_hidden FROM doc_meta WHERE doc_id LIKE 'ffp_ap_%'")]
    plan = fp.plan_filing(mine)
    assert plan["planned_docs"] == 2 and len(plan["no_class"]) == 1

    res = fp.apply_plan(None, plan, placed_by="test-fixture")
    assert res["folders_created"] == len(plan["nodes"])
    assert res["members_added"] == 2 and res["states_set"] == 3

    # 读回来核对（不靠写函数的返回值自说自话）
    l1 = fs.list_folder(None)
    tops = [s for s in l1["subfolders"] if s["name"].startswith("国家标准")]
    assert tops and tops[0]["file_count_deep"] >= 2
    lv2 = fs.list_folder(tops[0]["folder_id"])
    p_major = next(s for s in lv2["subfolders"] if s["name"].startswith("P "))
    assert p_major["file_count_deep"] == 2
    lv3 = fs.list_folder(p_major["folder_id"])
    p_range = next(s for s in lv3["subfolders"] if s["name"].startswith("P15/19"))
    assert p_range["file_count_deep"] == 2
    # 无分类的那篇进「待分类」且状态是排队
    pending = {x["doc_id"]: x for x in fs.list_pending_filing(limit=5000)["items"]}
    assert pending["ffp_ap_c"]["stage"] == "queued"
    assert "ffp_ap_a" not in pending
    assert fs.get_filing_state("ffp_ap_a")["stage"] == "filed"
    assert fs.get_filing_state("ffp_ap_a")["placed_by"] == "test-fixture"


# ─────────────────────────── 清单文本 ───────────────────────────

def _report(plan: dict) -> dict:
    return fp.build_report(
        plan, generated_at="2026-09-21T00:00:00",
        real_db={"path": "X:/knowledge.db", "size": 123, "mtime_before": "T0",
                 "mtime_after": "T0", "untouched": True},
        copy_db="X:/tmp/copy.db", copy_removed=True,
        timing={"copy": 1.0, "read_docs": 0.02, "classify": 0.05, "apply": 0.18,
                "est_real_seconds": 0.25},
        apply_result={"folders_created": 4, "members_added": 1, "states_set": 2},
        verify={"folders_in_db": 4})


def test_render_text_has_the_sections_the_owner_asked_for():
    docs = [doc("ffp_t1", "GB 50016-2014", "建筑设计防火规范", ["CCS:P16 工程防火"]),
            doc("ffp_t2", "GB/T 99999-2020", "某个没有分类的标准", [])]
    text = fp.render_text(_report(fp.plan_filing(docs)))
    assert "归位预览清单" in text
    assert "总共 **2** 篇" in text
    assert "没有分类的 1 篇" in text
    assert "一级目录各多少篇" in text
    assert "国家标准·行业标准·团体标准" in text
    assert "现在没有分类的那些（逐篇）" in text
    assert "某个没有分类的标准" in text          # 逐篇列出，不是只给个数
    assert "## 五、异常" in text
    assert "估算真库上跑一次约 0.25 秒" in text
    assert "**真库未被改动**：True" in text
