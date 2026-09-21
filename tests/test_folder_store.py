"""多级目录存储层用例（KB-FOLDER-PLAN 第 1 步）。

覆盖业主点名的边界：
- 多对多（一个文件进两个目录）；
- 复制目录后**共享成员**（改原目录不影响副本；从原目录拿掉后副本仍有它）；
- 挪目录**拒绝成环**；
- 删目录三种情形：空目录直接删 / 非空必须给模式 / reparent（一级目录必须报错）/
  purge（**同时在别处的文件不被真删，只丢归属**）；
- 分页与「含更深层的文件数」；范围集合（含更深层）；
- 名字/层数上限的可读报错。

⚠ `purge` 会**真的删文档**，所以另有一条 `test_purge_uses_given_db_path`：显式传一个
独立库文件，证明"在副本上操作删的是副本"，而不是默认库（真库）。
"""
from __future__ import annotations

import itertools

import pytest

from src.core.exceptions import KnowledgeStationError
from src.core.knowledge import folder_store as fs

_seq = itertools.count()


def nm(base: str) -> str:
    """本次会话内唯一的目录名（db fixture 是 session 级 ⇒ 名字不能撞）。"""
    return f"{base}-{next(_seq)}"


def mkdoc(db, doc_id: str) -> str:
    db.execute(
        "INSERT OR IGNORE INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES (?,?,?,?,'r1','[]','a.pdf',?)",
        (doc_id, doc_id, f"名-{doc_id}", doc_id, f"h-{doc_id}"))
    db.commit()
    return doc_id


def expect_code(code: str, fn, *a, **kw):
    with pytest.raises(KnowledgeStationError) as ei:
        fn(*a, **kw)
    assert ei.value.code == code, f"期望 {code}，实得 {ei.value.code}：{ei.value}"
    return ei.value


# ─────────────────────────── 建 / 改名 / 名字与层数上限 ───────────────────────────

def test_create_and_same_name_same_level_rejected(db):
    root = fs.create_folder(nm("国标"))
    # 同层同名（根层）拒绝
    expect_code("folder_name_conflict", fs.create_folder, root["name"])
    # 异层同名允许
    child = fs.create_folder(root["name"], root["folder_id"])
    assert child["parent_id"] == root["folder_id"]
    # 同一层里再同名拒绝
    expect_code("folder_name_conflict", fs.create_folder, root["name"], root["folder_id"])


def test_rename_folder_and_conflict(db):
    a = fs.create_folder(nm("甲"))
    b = fs.create_folder(nm("乙"))
    out = fs.rename_folder(a["folder_id"], "甲改")
    assert out["name"] == "甲改"
    expect_code("folder_name_conflict", fs.rename_folder, a["folder_id"], b["name"])
    # 改成自己原来的名字不算冲突
    assert fs.rename_folder(a["folder_id"], "甲改")["name"] == "甲改"


def test_name_and_depth_limits_have_readable_errors(db):
    expect_code("invalid_folder_name", fs.create_folder, "   ")
    expect_code("invalid_folder_name", fs.create_folder, "x" * (fs.MAX_NAME_LEN + 1))
    # 层数上限
    parent = None
    for i in range(fs.MAX_DEPTH):
        parent = fs.create_folder(nm(f"层{i}"), parent["folder_id"] if parent else None)
    expect_code("folder_depth_exceeded", fs.create_folder, nm("超深"), parent["folder_id"])


def test_folder_name_allows_slash(db):
    """⚠ CCS 区间名自带斜杠（P15/19）⇒ 目录名必须允许 `/`，否则真实分类树建不出来。"""
    f = fs.create_folder("P15/19 工程抗震、工程防火、人防工程")
    assert "/" in f["name"]


# ─────────────────────────── 多对多 ───────────────────────────

def test_one_file_in_two_folders(db):
    d = mkdoc(db, f"mm_{next(_seq)}")
    a = fs.create_folder(nm("多对多A"))
    b = fs.create_folder(nm("多对多B"))
    fs.add_member(a["folder_id"], "file", d)
    fs.add_member(b["folder_id"], "file", d)
    assert [x["doc_id"] for x in fs.list_folder(a["folder_id"])["files"]] == [d]
    assert [x["doc_id"] for x in fs.list_folder(b["folder_id"])["files"]] == [d]
    # 从一处拿掉，另一处不动
    fs.remove_member(a["folder_id"], "file", d)
    assert fs.list_folder(a["folder_id"])["files"] == []
    assert [x["doc_id"] for x in fs.list_folder(b["folder_id"])["files"]] == [d]


def test_add_member_is_idempotent_and_unknown_doc_rejected(db):
    d = mkdoc(db, f"idem_{next(_seq)}")
    a = fs.create_folder(nm("幂等"))
    assert fs.add_member(a["folder_id"], "file", d)["added"] is True
    assert fs.add_member(a["folder_id"], "file", d)["added"] is False
    expect_code("doc_not_found", fs.add_member, a["folder_id"], "file", "no_such_doc")
    expect_code("invalid_item_kind", fs.add_member, a["folder_id"], "bogus", d)
    expect_code("folder_not_found", fs.add_member, "no_such_folder", "file", d)


def test_move_member_between_folders(db):
    d = mkdoc(db, f"mv_{next(_seq)}")
    a = fs.create_folder(nm("挪出"))
    b = fs.create_folder(nm("挪入"))
    fs.add_member(a["folder_id"], "file", d)
    fs.move_member("file", d, a["folder_id"], b["folder_id"])
    assert fs.list_folder(a["folder_id"])["files"] == []
    assert [x["doc_id"] for x in fs.list_folder(b["folder_id"])["files"]] == [d]


# ─────────────────────────── 复制目录：共享成员 ───────────────────────────

def test_copy_folder_shares_members_and_is_independent(db):
    d = mkdoc(db, f"cp_{next(_seq)}")
    src = fs.create_folder(nm("原目录"))
    sub = fs.create_folder(nm("原子目录"), src["folder_id"])
    fs.add_member(src["folder_id"], "file", d)

    copy = fs.copy_folder(src["folder_id"])
    assert copy["name"] == f"{src['name']} (副本)"
    assert copy["copied_members"] == 2          # 一个文件 + 一个子目录，都是**同一份**

    # 副本的子目录就是原来那个目录（同一个 folder_id，不各拷一份）
    copy_subs = fs.list_folder(copy["folder_id"])["subfolders"]
    assert [s["folder_id"] for s in copy_subs] == [sub["folder_id"]]
    assert [x["doc_id"] for x in fs.list_folder(copy["folder_id"])["files"]] == [d]

    # 改原目录不影响副本
    d2 = mkdoc(db, f"cp2_{next(_seq)}")
    fs.add_member(src["folder_id"], "file", d2)
    assert [x["doc_id"] for x in fs.list_folder(copy["folder_id"])["files"]] == [d]

    # 从原目录把文件拿掉后，副本仍有它
    fs.remove_member(src["folder_id"], "file", d)
    assert [x["doc_id"] for x in fs.list_folder(copy["folder_id"])["files"]] == [d]

    # 副本再复制一份：自动换名，不撞
    copy2 = fs.copy_folder(src["folder_id"])
    assert copy2["name"] != copy["name"]


def test_copy_folder_into_own_subtree_rejected(db):
    a = fs.create_folder(nm("复制环A"))
    b = fs.create_folder(nm("复制环B"), a["folder_id"])
    expect_code("folder_cycle", fs.copy_member, "folder", a["folder_id"], b["folder_id"])


def test_copy_folder_rejects_its_own_subtree(db):
    """第 2 步补：``copy_folder`` 自己也要拒环。

    复制**不更新** ``parent_id`` ⇒ 原先挂在 ``move`` 上的那套环检测管不到它，
    但成员边已经成环（读路径有 ``seen`` 兜着不死，然而那是坏数据）。
    """
    a = fs.create_folder(nm("复制目录环A"))
    b = fs.create_folder(nm("复制目录环B"), a["folder_id"])
    expect_code("folder_cycle", fs.copy_folder, a["folder_id"], b["folder_id"])
    expect_code("folder_cycle", fs.copy_folder, a["folder_id"], a["folder_id"])
    # 复制到同一个父下的兄弟位置是合法的
    ok = fs.copy_folder(a["folder_id"], None)
    assert ok["folder_id"] != a["folder_id"]


# ─────────────── 排序：sort 优先、同级按拼音（第 2 步落地）───────────────

def test_top_level_order_is_sort_then_pinyin(db):
    """四个顶层（标准 10 / 法律法规 20 / 公司制度 30 / 待分类 90）必须按 **sort** 排。

    ⚠ 这条钉的是**实际顺序**，不是"``sort`` 的值写对没有"：修准前读取一律
    ``ORDER BY name`` ⇒ 顶层实际顺序是「公司制度 / 待分类 / 标准 / 法律法规」
    （Unicode 码位），四个顶层的 ``sort`` 白写。
    ⚠ 名字带上本用例独有的后缀，免得与其他用例新建的顶层目录撞（库是 session 级的）。
    """
    tags = nm("排序钉")
    names = [("标准", 10), ("法律法规", 20), ("公司制度", 30), ("待分类", 90)]
    made = {n: fs.create_folder(f"{n}·{tags}", None, sort=s)["folder_id"]
            for n, s in names}
    rows = fs.list_folder(None)["subfolders"]
    order = [r["folder_id"] for r in rows if r["folder_id"] in made.values()]
    assert order == [made[n] for n, _ in names]
    # 同级按拼音（不是码位）：A 综合(a) < 安全(an) < 行政(xing)
    p = fs.create_folder(nm("拼音父"))
    for name in ("行政", "A 综合", "安全"):
        fs.create_folder(name, p["folder_id"], sort=0)
    got = [s["name"] for s in fs.list_folder(p["folder_id"])["subfolders"]]
    assert got == ["A 综合", "安全", "行政"]
    # sort 压过拼音：sort=1 的排在所有 sort=0 的后面
    fs.create_folder("安 排", p["folder_id"], sort=1)
    assert [s["name"] for s in fs.list_folder(p["folder_id"])["subfolders"]] \
        == ["A 综合", "安全", "行政", "安 排"]


# ─────────────────────────── 挪目录：拒绝成环 ───────────────────────────

def test_move_folder_rejects_cycle(db):
    a = fs.create_folder(nm("环A"))
    b = fs.create_folder(nm("环B"), a["folder_id"])
    c = fs.create_folder(nm("环C"), b["folder_id"])
    expect_code("folder_cycle", fs.move_folder, a["folder_id"], a["folder_id"])
    expect_code("folder_cycle", fs.move_folder, a["folder_id"], b["folder_id"])
    expect_code("folder_cycle", fs.move_folder, a["folder_id"], c["folder_id"])
    expect_code("folder_cycle", fs.move_folder, b["folder_id"], c["folder_id"])
    # 报错之后层级一动没动
    assert fs._folder_row(fs.get_db_connection(), c["folder_id"])["parent_id"] \
        == b["folder_id"]
    # 反向合法：把 C 挪到顶层（挪完 C 不再是 a 的下级）
    assert fs.move_folder(c["folder_id"], None)["parent_id"] is None
    assert c["folder_id"] in [s["folder_id"] for s in fs.list_folder(None)["subfolders"]]
    # 挪出去以后 A 进 C 不再成环（这才是"挪动真的改了树"的证据）
    assert fs.move_folder(a["folder_id"], c["folder_id"])["parent_id"] == c["folder_id"]


# ─────────────── 挪：按"从哪一处 → 到哪一处"（2026-09-21 第 2 步修准）───────────────
#
# 修之前：`move_folder` 只收"挪到哪"，把 `folder.parent_id` 与成员边**一起**改
# ⇒ 一个"复制出来的、同时挂在两处"的目录，挪一处会把**另一处也带走**。
# 方案 §九把这条登记成待第 2 步修的缺陷。下面四条把这处语义钉住。

def _kids(fid):
    return [s["folder_id"] for s in fs.list_folder(fid)["subfolders"]]


def test_move_folder_by_from_to_updates_main_position_when_from_is_main(db):
    home = fs.create_folder(nm("主位"))
    other = fs.create_folder(nm("别处"))
    target = fs.create_folder(nm("目标"))
    sub = fs.create_folder(nm("被挪"), home["folder_id"])
    # 复制出一处：同一个目录同时挂在 other 下（成员边，不新建目录）
    assert fs.copy_member("folder", sub["folder_id"], other["folder_id"])["added"] is True

    got = fs.move_folder(sub["folder_id"], target["folder_id"],
                         from_parent_id=home["folder_id"])
    assert got["updated_main_position"] is True
    assert got["parent_id"] == target["folder_id"]
    assert _kids(target["folder_id"]) == [sub["folder_id"]]
    assert _kids(home["folder_id"]) == []
    # ⚠ **另一处不许被动**（修准前这里会变成 [sub] 被移走）
    assert _kids(other["folder_id"]) == [sub["folder_id"]]


def test_move_folder_defaults_to_the_main_position(db):
    """省略 ``from_parent_id`` = 挪"这个目录本身"（旧调用的行为一字不变）。"""
    a = fs.create_folder(nm("默认源"))
    b = fs.create_folder(nm("默认目标"))
    sub = fs.create_folder(nm("默认子"), a["folder_id"])
    got = fs.move_folder(sub["folder_id"], b["folder_id"])
    assert got["from_parent_id"] == a["folder_id"]
    assert got["updated_main_position"] is True
    assert got["parent_id"] == b["folder_id"]
    assert fs._folder_row(fs.get_db_connection(), sub["folder_id"])["parent_id"] \
        == b["folder_id"]


def test_move_folder_from_a_copy_takes_only_that_edge_away(db):
    """从**复制出来的那一处**挪走：只删那条边，目录本体（``parent_id``）不动。"""
    home = fs.create_folder(nm("本体"))
    other = fs.create_folder(nm("复制处"))
    sub = fs.create_folder(nm("本体的子"), home["folder_id"])
    fs.copy_member("folder", sub["folder_id"], other["folder_id"])

    got = fs.move_folder(sub["folder_id"], None, from_parent_id=other["folder_id"])
    assert got["updated_main_position"] is False
    assert got["parent_id"] == home["folder_id"]              # 本体没动
    assert _kids(other["folder_id"]) == []                # 那条边没了
    assert _kids(home["folder_id"]) == [sub["folder_id"]]  # 主位置还在


def test_move_folder_from_a_place_that_does_not_hold_it(db):
    a = fs.create_folder(nm("没有它"))
    sub = fs.create_folder(nm("不在那儿"))
    err = expect_code("folder_not_in_parent", fs.move_folder, sub["folder_id"], None,
                      from_parent_id=a["folder_id"])
    assert "不在" in str(err)
    # 什么都没动
    assert fs._folder_row(fs.get_db_connection(), sub["folder_id"])["parent_id"] is None


def test_move_folder_to_the_same_place_is_a_noop(db):
    a = fs.create_folder(nm("原地"))
    sub = fs.create_folder(nm("原地子"), a["folder_id"])
    got = fs.move_folder(sub["folder_id"], a["folder_id"])
    assert got["moved"] is False and got["updated_main_position"] is False
    assert _kids(a["folder_id"]) == [sub["folder_id"]]


def test_move_folder_name_conflict_at_target(db):
    target = fs.create_folder(nm("目标父"))
    fs.create_folder("撞名的", target["folder_id"])       # 目标层已有这个名字
    mover = fs.create_folder("撞名的")                    # 顶层另有一个同名目录
    expect_code("folder_name_conflict", fs.move_folder, mover["folder_id"],
                target["folder_id"])
    # 挪到顶层（同名在别的层）不算冲突
    child = fs.create_folder(nm("换层"), target["folder_id"])
    assert fs.move_folder(child["folder_id"], None)["parent_id"] is None


# ─────────────────────────── 删目录：三种情形 ───────────────────────────

def test_delete_empty_folder_ok(db):
    f = fs.create_folder(nm("空目录"))
    out = fs.delete_folder(f["folder_id"])
    assert out["mode"] == "empty" and out["removed"] is True
    expect_code("folder_not_found", fs._folder_row, fs.get_db_connection(), f["folder_id"])


def test_delete_nonempty_requires_mode(db):
    d = mkdoc(db, f"del_{next(_seq)}")
    f = fs.create_folder(nm("非空"))
    fs.add_member(f["folder_id"], "file", d)
    err = expect_code("folder_delete_mode_required", fs.delete_folder, f["folder_id"])
    # 报错要能给人话：两个模式都要点到名
    assert "reparent" in str(err) and "purge" in str(err)
    # 报错后什么都没动
    assert fs.list_folder(f["folder_id"])["files_total"] == 1
    expect_code("invalid_delete_mode", fs.delete_folder, f["folder_id"], "bogus")


def test_delete_reparent_moves_members_to_parent(db):
    d1 = mkdoc(db, f"rp1_{next(_seq)}")
    d2 = mkdoc(db, f"rp2_{next(_seq)}")
    parent = fs.create_folder(nm("上一层"))
    mid = fs.create_folder(nm("中间层"), parent["folder_id"])
    child = fs.create_folder(nm("下层目录"), mid["folder_id"])
    fs.add_member(mid["folder_id"], "file", d1)
    fs.add_member(mid["folder_id"], "file", d2)
    # d2 本来就已经在上一层里 ⇒ 只该去掉中间层那条，不该加重复行
    fs.add_member(parent["folder_id"], "file", d2)

    out = fs.delete_folder(mid["folder_id"], mode="reparent")
    assert out["mode"] == "reparent"
    assert out["reparented_subfolders"] == 1 and out["reparented_files"] == 2
    assert out["new_parent_id"] == parent["folder_id"]

    assert [x["doc_id"] for x in fs.list_folder(parent["folder_id"])["files"]] == [d1, d2]
    # 子目录改挂在上一层（parent_id 改掉，且不在中间层下了）
    assert fs._folder_row(fs.get_db_connection(), child["folder_id"])["parent_id"] \
        == parent["folder_id"]
    # 没有重复行（d2 在上一层只有一条）
    n = db.execute("SELECT COUNT(*) FROM folder_member WHERE folder_id=? AND item_kind='file'"
                   " AND item_id=?", (parent["folder_id"], d2)).fetchone()[0]
    assert n == 1
    # 被删的目录没了
    assert db.execute("SELECT COUNT(*) FROM folder WHERE folder_id=?",
                      (mid["folder_id"],)).fetchone()[0] == 0


def test_delete_reparent_rejects_top_level_folder(db):
    """业主点名的边界①：一级目录没有上一层 ⇒ reparent 必须报可读中文错，
    **不许**静默改成 purge、也不许静默不做事。"""
    d = mkdoc(db, f"top_{next(_seq)}")
    f = fs.create_folder(nm("一级目录"))
    fs.add_member(f["folder_id"], "file", d)

    err = expect_code("folder_top_level_no_parent", fs.delete_folder, f["folder_id"],
                      mode="reparent")
    assert "上一层" in str(err) and "一级目录" in str(err)
    # 目录与归属都还在（报错不能有副作用）
    assert db.execute("SELECT COUNT(*) FROM folder WHERE folder_id=?",
                      (f["folder_id"],)).fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id=?", (d,)).fetchone()[0] == 1
    # 一级目录仍然可以 purge（那是唯一选择）
    out = fs.delete_folder(f["folder_id"], mode="purge")
    assert out["mode"] == "purge" and out["deleted_docs"] == 1


def test_delete_purge_keeps_docs_present_elsewhere(db):
    """业主点名的边界②：purge 时**还挂在别的目录里**的文件只是丢归属，**不真删**。"""
    shared = mkdoc(db, f"pg_shared_{next(_seq)}")
    lonely = mkdoc(db, f"pg_lonely_{next(_seq)}")
    keep = fs.create_folder(nm("别处的目录"))
    doomed = fs.create_folder(nm("要删的目录"))
    sub = fs.create_folder(nm("要删的子目录"), doomed["folder_id"])
    fs.add_member(keep["folder_id"], "file", shared)      # 同时在别处
    fs.add_member(doomed["folder_id"], "file", shared)    # 在要删的这棵里
    fs.add_member(sub["folder_id"], "file", lonely)       # 只在这棵里

    out = fs.delete_folder(doomed["folder_id"], mode="purge")
    assert out["mode"] == "purge"
    assert out["purged_folders"] == 2                     # 自己 + 子目录
    assert out["unfiled_docs"] == 1                       # shared：只丢归属
    assert out["deleted_docs"] == 1                       # lonely：哪都不在了 ⇒ 真删

    # shared 还在库里，且仍挂在 keep 里
    assert db.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id=?",
                      (shared,)).fetchone()[0] == 1
    assert [x["doc_id"] for x in fs.list_folder(keep["folder_id"])["files"]] == [shared]
    # lonely 真没了
    assert db.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id=?",
                      (lonely,)).fetchone()[0] == 0
    # 被删的两个目录都没了，且没有悬空成员行
    assert db.execute("SELECT COUNT(*) FROM folder WHERE folder_id IN (?,?)",
                      (doomed["folder_id"], sub["folder_id"])).fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM folder_member WHERE folder_id IN (?,?)",
                      (doomed["folder_id"], sub["folder_id"])).fetchone()[0] == 0
    # 状态行也跟着真删的文件一起清掉
    assert db.execute("SELECT COUNT(*) FROM doc_filing_state WHERE doc_id=?",
                      (lonely,)).fetchone()[0] == 0


def test_purge_uses_given_db_path(db, tmp_path):
    """⚠ 安全用例：purge 的真删**必须**落在传进来的那个库上。

    `doc_delete.delete_documents` 原先只走默认连接 ⇒ 在真库副本上 purge 会删到**默认库**。
    这条用例用一个独立库文件证明现在删的是那一个：同名 doc 在默认库里必须毫发无损。
    """
    from src.core.storage.sqlite_db import init_schema
    other = tmp_path / "other.db"
    init_schema(other)
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection(other)
    for d in ("dup_doc", "other_doc"):
        conn.execute(
            "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
            " current_revision_id, domain_tags, file_path, file_hash)"
            " VALUES (?,?,?,?,'r1','[]','a.pdf',?)", (d, d, d, d, f"h-{d}"))
    conn.commit()

    mkdoc(db, "dup_doc")                                   # 默认库里的同名文档
    f = fs.create_folder(nm("独立库目录"), db_path=other)
    fs.add_member(f["folder_id"], "file", "dup_doc", db_path=other)
    fs.add_member(f["folder_id"], "file", "other_doc", db_path=other)

    out = fs.delete_folder(f["folder_id"], mode="purge", db_path=other)
    assert out["deleted_docs"] == 2
    assert conn.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id='dup_doc'"
                        ).fetchone()[0] == 0
    # 默认库（= 本会话的测试库，代表"真库那一侧"）里的 dup_doc 必须还在
    assert db.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id='dup_doc'"
                      ).fetchone()[0] == 1
    # 那个目录建在独立库里，也就该从独立库里消失（默认库里从来就没有它）
    assert conn.execute("SELECT COUNT(*) FROM folder WHERE folder_id=?",
                        (f["folder_id"],)).fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM folder WHERE folder_id=?",
                      (f["folder_id"],)).fetchone()[0] == 0


def test_describe_folder_delete_numbers(db):
    """「先问一句」要的数字：一级目录 reparent 不可用；purge 会真删几篇。"""
    shared = mkdoc(db, f"ds_{next(_seq)}")
    lonely = mkdoc(db, f"ds2_{next(_seq)}")
    big = fs.create_folder(nm("问句祖"))
    other = fs.create_folder(nm("问句别的"), big["folder_id"])   # 非一级 ⇒ 可用 reparent
    f = fs.create_folder(nm("问句一级"))
    fs.add_member(other["folder_id"], "file", shared)
    fs.add_member(f["folder_id"], "file", shared)
    fs.add_member(f["folder_id"], "file", lonely)

    d = fs.describe_folder_delete(f["folder_id"])
    assert d["is_empty"] is False
    assert d["direct_file_count"] == 2 and d["subtree_file_count"] == 2
    assert d["reparent_available"] is False              # 一级目录没有上一层
    assert d["files_kept_elsewhere"] == 1
    assert d["files_would_be_deleted"] == 1
    # 非一级目录的同一组数字：other 里只有 shared，而 shared 还在 f 里（子树之外）
    # ⇒ 一篇都不真删，只丢 other 这一处归属
    d2 = fs.describe_folder_delete(other["folder_id"])
    assert d2["reparent_available"] is True
    assert d2["files_kept_elsewhere"] == 1 and d2["files_would_be_deleted"] == 0

    empty = fs.create_folder(nm("问句空"))
    assert fs.describe_folder_delete(empty["folder_id"])["is_empty"] is True


# ─────────────────────────── 列某一级 + 分页 + 深层计数 ───────────────────────────

def test_list_folder_pagination_and_deep_counts(db):
    docs = [mkdoc(db, f"pg_{next(_seq)}") for _ in range(5)]
    a = fs.create_folder(nm("分页A"))
    b = fs.create_folder(nm("分页B"), a["folder_id"])
    c = fs.create_folder(nm("分页C"), b["folder_id"])
    for d in docs[:3]:
        fs.add_member(a["folder_id"], "file", d)
    fs.add_member(c["folder_id"], "file", docs[3])
    fs.add_member(c["folder_id"], "file", docs[4])

    first = fs.list_folder(a["folder_id"], file_offset=0, file_limit=2)
    assert first["files_total"] == 3 and len(first["files"]) == 2 and first["has_more"] is True
    second = fs.list_folder(a["folder_id"], file_offset=2, file_limit=2)
    assert len(second["files"]) == 1 and second["has_more"] is False
    assert [x["doc_id"] for x in first["files"] + second["files"]] == sorted(docs[:3])
    expect_code("invalid_pagination", fs.list_folder, a["folder_id"], 0, 0)

    # 含更深层的文件数：B 下面是 C（2 篇），A 直接 3 篇
    subs = {s["folder_id"]: s for s in fs.list_folder(a["folder_id"])["subfolders"]}
    assert subs[b["folder_id"]]["file_count_deep"] == 2
    assert subs[b["folder_id"]]["file_count_direct"] == 0
    # 面包屑：从顶层到本级
    assert [x["folder_id"] for x in fs.list_folder(c["folder_id"])["breadcrumb"]] == \
        [a["folder_id"], b["folder_id"], c["folder_id"]]


def test_list_root_shows_toplevel_folders_and_unfiled_docs(db):
    d = mkdoc(db, f"unf_{next(_seq)}")
    f = fs.create_folder(nm("顶层目录"))
    root = fs.list_folder(None)
    assert f["folder_id"] in [s["folder_id"] for s in root["subfolders"]]
    assert d in [x["doc_id"] for x in root["files"]]        # 还没进任何目录 ⇒ 顶层可见
    fs.add_member(f["folder_id"], "file", d)
    assert d not in [x["doc_id"] for x in fs.list_folder(None)["files"]]
    assert fs.list_folder(None, unfiled=False)["files"] == []


# ─────────────────────────── 范围集合 ───────────────────────────

def test_folder_scope_includes_deeper_levels_and_unions(db):
    d1 = mkdoc(db, f"sc_{next(_seq)}")
    d2 = mkdoc(db, f"sc2_{next(_seq)}")
    a = fs.create_folder(nm("范围A"))
    b = fs.create_folder(nm("范围B"), a["folder_id"])
    c = fs.create_folder(nm("范围C"), b["folder_id"])
    other = fs.create_folder(nm("范围另一棵"))
    d3 = mkdoc(db, f"sc3_{next(_seq)}")
    fs.add_member(a["folder_id"], "file", d1)
    fs.add_member(c["folder_id"], "file", d2)
    fs.add_member(other["folder_id"], "file", d3)

    s = fs.folder_scope(a["folder_id"])
    assert s["folder_ids"] == {a["folder_id"], b["folder_id"], c["folder_id"]}
    assert s["doc_ids"] == {d1, d2}                        # 含更深层
    # 多选取并集
    u = fs.folder_scope([c["folder_id"], other["folder_id"]])
    assert u["doc_ids"] == {d2, d3}
    assert u["roots"] == [c["folder_id"], other["folder_id"]]
    # 同一文件挂两处只算一次
    fs.add_member(a["folder_id"], "file", d2)
    assert fs.folder_scope(a["folder_id"])["doc_ids"] == {d1, d2}
    # 未知目录 ⇒ 当场报错，不静默给空范围
    expect_code("folder_not_found", fs.folder_scope, "no_such_folder")
    expect_code("invalid_scope", fs.folder_scope, [])


# ─────────────────────────── 批量入口 ───────────────────────────

def test_build_folder_tree_batch_atomic(db):
    d1 = mkdoc(db, f"bt_{next(_seq)}")
    d2 = mkdoc(db, f"bt2_{next(_seq)}")
    n1, n2 = nm("批量根"), nm("批量子")
    res = fs.build_folder_tree(
        [{"key": "k1", "name": n1, "parent_key": None},
         {"key": "k2", "name": n2, "parent_key": "k1"}],
        [{"folder_key": "k1", "item_kind": "file", "item_id": d1},
         {"folder_key": "k2", "item_kind": "file", "item_id": d2}],
        [{"doc_id": d1, "stage": "filed", "placed_folder_key": "k1", "placed_by": "t"},
         {"doc_id": d2, "stage": "queued"}])
    assert res["folders_created"] == 2 and res["members_added"] == 2
    assert fs.get_filing_state(d1)["stage"] == "filed"
    assert fs.get_filing_state(d1)["placed_folder_id"] == res["key_to_id"]["k1"]
    assert fs.get_filing_state(d2)["stage"] == "queued"

    # 父先子后 / key 存在性 / 引用完整性：任一不满足 ⇒ 整批回滚（不是留半截）
    before = db.execute("SELECT COUNT(*) FROM folder").fetchone()[0]
    expect_code("invalid_folder_key", fs.build_folder_tree,
                [{"key": "x", "name": nm("子先到"), "parent_key": "not_yet"}])
    expect_code("invalid_folder_key", fs.build_folder_tree,
                [{"key": "y", "name": nm("重复key")},
                 {"key": "y", "name": nm("重复key2")}])
    expect_code("invalid_folder_key", fs.build_folder_tree,
                [], [{"folder_key": "ghost", "item_kind": "file", "item_id": d1}])
    expect_code("invalid_stage", fs.build_folder_tree,
                [], [], [{"doc_id": d1, "stage": "bogus"}])
    expect_code("doc_not_found", fs.build_folder_tree,
                [], [], [{"doc_id": "no_such_doc", "stage": "queued"}])
    assert db.execute("SELECT COUNT(*) FROM folder").fetchone()[0] == before
    # 整批失败后 d2 的状态也没被改成半个样子
    assert fs.get_filing_state(d2)["stage"] == "queued"


def test_build_folder_tree_reuse_existing_is_idempotent(db):
    """``reuse_existing=True`` ⇒ 同一批 nodes 重复跑**不建重复目录**（一次性归位脚本要的幂等）。

    2026-09-21 加：真库归位脚本要能"重跑一次不出第二棵树"，而默认口径（严格新建）
    第二次会当场 ``folder_name_conflict``。
    """
    d1 = mkdoc(db, f"re_{next(_seq)}")
    n1, n2 = nm("复用根"), nm("复用子")
    nodes = [{"key": "k1", "name": n1, "parent_key": None, "sort": 10},
             {"key": "k2", "name": n2, "parent_key": "k1"}]
    first = fs.build_folder_tree(nodes, [{"folder_key": "k2", "item_kind": "file",
                                          "item_id": d1}],
                                 [{"doc_id": d1, "stage": "queued"}],
                                 reuse_existing=True)
    assert first["folders_created"] == 2 and first["folders_reused"] == 0
    second = fs.build_folder_tree(nodes, [{"folder_key": "k2", "item_kind": "file",
                                           "item_id": d1}],
                                  [{"doc_id": d1, "stage": "filed", "placed_folder_key": "k2"}],
                                  reuse_existing=True)
    assert second["folders_created"] == 0 and second["folders_reused"] == 2
    assert second["key_to_id"] == first["key_to_id"]        # 复用到的就是原来那两个
    assert second["members_added"] == 0 and second["members_skipped"] == 1
    assert db.execute("SELECT COUNT(*) FROM folder WHERE name=?", (n1,)).fetchone()[0] == 1
    # 默认口径仍然是**严格新建**（同名同层当场报错，绝不悄悄复用）
    expect_code("folder_name_conflict", fs.build_folder_tree, nodes)


# ─────────────────────────── 处理状态 ───────────────────────────

def test_filing_state_lifecycle_and_lists(db):
    d = mkdoc(db, f"st_{next(_seq)}")
    f = fs.create_folder(nm("状态目录"))

    # 从未处理过：默认按 queued 算，出现在「待分类」
    assert fs.get_filing_state(d) is None
    pending_ids = {x["doc_id"] for x in fs.list_pending_filing(limit=2000)["items"]}
    assert d in pending_ids

    fs.set_filing_state(d, "recognizing", confidence=0.42, failure_kind="table")
    st = fs.get_filing_state(d)
    assert st["stage"] == "recognizing" and st["confidence"] == 0.42
    assert d in {x["doc_id"] for x in fs.list_pending_filing(limit=2000)["items"]}

    fs.mark_filed(d, f["folder_id"], placed_by="tester", confidence=0.9)
    st = fs.get_filing_state(d)
    assert st["stage"] == "filed" and st["placed_folder_id"] == f["folder_id"]
    assert st["placed_by"] == "tester" and st["placed_at"]
    assert d not in {x["doc_id"] for x in fs.list_pending_filing(limit=2000)["items"]}

    # 「所有文件」的状态列表里也有它
    all_states = fs.list_document_states(limit=5000)["items"]
    me = next(x for x in all_states if x["doc_id"] == d)
    assert me["stage"] == "filed" and me["confidence"] == 0.9

    # 只改传进来的字段（没传的保持原值）
    fs.set_filing_state(d, "failed", last_error="表格识别失败")
    st = fs.get_filing_state(d)
    assert st["stage"] == "failed" and st["confidence"] == 0.9
    assert st["last_error"] == "表格识别失败"

    expect_code("invalid_stage", fs.set_filing_state, d, "bogus")
    expect_code("invalid_state_field", fs.set_filing_state, d, None, bogus=1)
    expect_code("doc_not_found", fs.set_filing_state, "no_such_doc", "queued")
    expect_code("invalid_pagination", fs.list_pending_filing, 0, 0)
