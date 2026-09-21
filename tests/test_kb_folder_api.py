"""``/api/v1/kb/*`` 接口用例（KB-FOLDER-PLAN 第 2 步）。

全部在 conftest 的**临时库**上跑（绝不碰真库）。每个接口至少一条"正常 + 一条边界"：

- 列目录：空目录 / 顶层顺序（**标准 → 法律法规 → 公司制度 → 待分类**）/ 不存在的 id ⇒ 404 /
  分页边界 / 目录按 (sort, 拼音, 名) 排；
- 列文件：空目录 ⇒ 空数组（**不是 404**）/ 分页 / 不存在的 id ⇒ 404；
- 建目录：正常 / 顶层重名 ⇒ 409 / 顶层乱建 ⇒ 422 / 不存在的上级 ⇒ 404 / 空名 ⇒ 422；
- 改名：正常 / 同层重名 ⇒ 409 / 不存在 ⇒ 404；
- 挪：正常 / **同时挂在两处的目录只挪一处**（第 2 步修准的语义）/ 成环 ⇒ 422 /
  `from_parent_id` 那条边不存在 ⇒ 409；
- 复制：正常（**共享成员**）/ 复制进自己的下级 ⇒ 422；
- 删：空目录直接删 / 非空缺 mode ⇒ 409 / 一级目录 reparent ⇒ 409 /
  purge 时"同时在别处"的文件不真删 / 不存在 ⇒ 404 / 非法 mode ⇒ 422；
- 成员：批量加（**重复加幂等**）/ 拿掉 / 挪 / 复制；
- 待分类：列表（带 stage/confidence）/ **只在现有目录里给建议**（认不出 ⇒ null）/
  确认归位三条路（accept / existing / new）+ **自动挪出「待分类」**；
- 范围：含更深层 / 多选取并集 / 未知目录 ⇒ 404（**绝不静默给空范围**）。
"""
from __future__ import annotations

import itertools

from _kb_folder_api_fixtures import api, data_of, error_code, mkdoc_full, tops, uniq

_seq = itertools.count()


def _new(c, token, name: str | None = None, parent: str | None = None) -> dict:
    body: dict = {"name": name or uniq("目录")}
    if parent is not None:
        body["parent_id"] = parent
    return data_of(api(c, token, "post", "/api/v1/kb/folders", json=body))


# ─────────────────────────── 列某一级 ───────────────────────────

def test_list_top_level_order_is_the_hand_set_order(client, tops):
    """**顶层实际顺序**必须是 标准 → 法律法规 → 公司制度 → 待分类（不只比 sort 值）。"""
    c, token = client
    data = data_of(api(c, token, "get", "/api/v1/kb/folders"))
    assert data["folder"] is None and data["breadcrumb"] == []
    order = [s["name"] for s in data["subfolders"]]
    want = ["标准", "法律法规", "公司制度", "待分类"]
    assert [n for n in order if n in want] == want


def test_list_empty_folder_gives_empty_array_not_error(client):
    c, token = client
    f = _new(c, token)
    data = data_of(api(c, token, "get", "/api/v1/kb/folders",
                       params={"parent_id": f["folder_id"]}))
    assert data["subfolders"] == [] and data["total"] == 0
    assert [b["folder_id"] for b in data["breadcrumb"]] == [f["folder_id"]]


def test_list_unknown_folder_is_404(client):
    c, token = client
    st, code = error_code(api(c, token, "get", "/api/v1/kb/folders",
                              params={"parent_id": "fld_nope"}))
    assert (st, code) == (404, "folder_not_found")


def test_list_subfolders_sorted_by_sort_then_pinyin(client):
    """同级排序 = (sort, 拼音, 名)：``A 综合`` 按拼音是 a…，必须排在 ``安全`` 前。"""
    c, token = client
    parent = _new(c, token)
    for name in ("行政", "安全", "A 综合"):
        api(c, token, "post", "/api/v1/kb/folders",
            json={"parent_id": parent["folder_id"], "name": name, "sort": 0})
    # sort 优先：另一个 sort=1 的必须排在所有 sort=0 的后面
    api(c, token, "post", "/api/v1/kb/folders",
        json={"parent_id": parent["folder_id"], "name": "安 排", "sort": 1})
    rows = data_of(api(c, token, "get", "/api/v1/kb/folders",
                       params={"parent_id": parent["folder_id"]}))["subfolders"]
    assert [s["name"] for s in rows] == ["A 综合", "安全", "行政", "安 排"]
    assert [s["sort"] for s in rows] == [0, 0, 0, 1]


def test_list_pagination_boundary(client):
    c, token = client
    parent = _new(c, token)
    for i in range(3):
        _new(c, token, uniq(f"分页{i}"), parent["folder_id"])
    page1 = data_of(api(c, token, "get", "/api/v1/kb/folders",
                        params={"parent_id": parent["folder_id"], "limit": 2, "offset": 0}))
    assert len(page1["subfolders"]) == 2 and page1["total"] == 3 and page1["has_more"]
    page2 = data_of(api(c, token, "get", "/api/v1/kb/folders",
                        params={"parent_id": parent["folder_id"], "limit": 2, "offset": 2}))
    assert len(page2["subfolders"]) == 1 and not page2["has_more"]
    ids = [s["folder_id"] for s in page1["subfolders"] + page2["subfolders"]]
    assert len(set(ids)) == 3                                   # 不重不漏
    st, code = error_code(api(c, token, "get", "/api/v1/kb/folders",
                              params={"parent_id": parent["folder_id"], "limit": 0}))
    assert (st, code) == (422, "invalid_pagination")
    st, code = error_code(api(c, token, "get", "/api/v1/kb/folders",
                              params={"parent_id": parent["folder_id"], "limit": 999}))
    assert (st, code) == (422, "invalid_pagination")


def test_subfolder_deep_file_count(client, db, tops):
    c, token = client
    parent = _new(c, token)
    child = _new(c, token, uniq("深"), parent["folder_id"])
    d = mkdoc_full(db, f"deep_{next(_seq)}")
    assert api(c, token, "post", "/api/v1/kb/members",
               json={"folder_id": child["folder_id"], "items": [{"kind": "file", "id": d}]}
               ).status_code == 200
    subs = {s["folder_id"]: s for s in data_of(
        api(c, token, "get", "/api/v1/kb/folders",
            params={"parent_id": parent["folder_id"]}))["subfolders"]}
    assert subs[child["folder_id"]]["file_count_direct"] == 1
    assert subs[child["folder_id"]]["file_count_deep"] == 1


# ─────────────────────────── 列某一级的文件 ───────────────────────────

def test_items_empty_and_pagination(client, db):
    c, token = client
    f = _new(c, token)
    empty = data_of(api(c, token, "get", f"/api/v1/kb/folders/{f['folder_id']}/items"))
    assert empty["items"] == [] and empty["total"] == 0 and empty["folder"]["folder_id"] \
        == f["folder_id"]
    docs = [mkdoc_full(db, f"it_{next(_seq)}") for _ in range(5)]
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": f["folder_id"],
              "items": [{"kind": "file", "id": d} for d in docs]})
    p1 = data_of(api(c, token, "get", f"/api/v1/kb/folders/{f['folder_id']}/items",
                     params={"limit": 2, "offset": 0}))
    assert p1["total"] == 5 and len(p1["items"]) == 2 and p1["has_more"]
    p3 = data_of(api(c, token, "get", f"/api/v1/kb/folders/{f['folder_id']}/items",
                     params={"limit": 2, "offset": 4}))
    assert len(p3["items"]) == 1 and not p3["has_more"]


def test_items_unknown_folder_is_404(client):
    c, token = client
    st, code = error_code(api(c, token, "get", "/api/v1/kb/folders/fld_nope/items"))
    assert (st, code) == (404, "folder_not_found")


# ─────────────────────────── 建 / 改名 ───────────────────────────

def test_create_folder_under_parent_and_errors(client, tops):
    c, token = client
    parent = _new(c, token)
    kid = _new(c, token, uniq("子"), parent["folder_id"])
    assert kid["parent_id"] == parent["folder_id"]
    # 同层重名
    st, code = error_code(api(c, token, "post", "/api/v1/kb/folders",
                              json={"parent_id": parent["folder_id"], "name": kid["name"]}))
    assert (st, code) == (409, "folder_name_conflict")
    # 顶层重名（四个预建之一）
    st, code = error_code(api(c, token, "post", "/api/v1/kb/folders", json={"name": "标准"}))
    assert (st, code) == (409, "folder_name_conflict")
    # 顶层可以加新目录（顶层名字**不**限定）
    extra = _new(c, token, uniq("新顶层"))
    assert extra["parent_id"] is None
    # 不存在的上级 / 空名
    st, code = error_code(api(c, token, "post", "/api/v1/kb/folders",
                              json={"parent_id": "fld_nope", "name": uniq("x")}))
    assert (st, code) == (404, "folder_not_found")
    st, code = error_code(api(c, token, "post", "/api/v1/kb/folders",
                              json={"parent_id": parent["folder_id"], "name": "   "}))
    assert (st, code) == (422, "invalid_folder_name")


def test_rename_and_conflict(client):
    c, token = client
    parent = _new(c, token)
    a = _new(c, token, uniq("甲"), parent["folder_id"])
    b = _new(c, token, uniq("乙"), parent["folder_id"])
    got = data_of(api(c, token, "put", f"/api/v1/kb/folders/{a['folder_id']}",
                      json={"name": "甲改"}))
    assert got["name"] == "甲改"
    st, code = error_code(api(c, token, "put", f"/api/v1/kb/folders/{a['folder_id']}",
                              json={"name": b["name"]}))
    assert (st, code) == (409, "folder_name_conflict")
    st, code = error_code(api(c, token, "put", "/api/v1/kb/folders/fld_nope",
                              json={"name": "x"}))
    assert (st, code) == (404, "folder_not_found")


# ─────────────────────────── 挪（第 2 步修准的语义）───────────────────────────

def test_move_folder_from_to(client):
    c, token = client
    a = _new(c, token)
    b = _new(c, token)
    got = data_of(api(c, token, "post", f"/api/v1/kb/folders/{a['folder_id']}/move",
                      json={"to_parent_id": b["folder_id"]}))
    assert got["parent_id"] == b["folder_id"]
    assert got["updated_main_position"] is True
    assert a["folder_id"] in [s["folder_id"] for s in data_of(
        api(c, token, "get", "/api/v1/kb/folders",
            params={"parent_id": b["folder_id"]}))["subfolders"]]


def test_move_a_two_places_folder_leaves_the_other_place_alone(client):
    """**第 2 步修准的那处语义**：同时挂在两处的目录，挪一处**不再**把另一处带走。

    构造（这正是方案 §九登记的那个缺陷形状）：
    目录 ``sub`` 的主位置 = ``home``，**另一条边** ``(other, sub)`` 是复制出来的那一处
    （用底层 ``copy_member`` 造，因为"复制目录"是新建一个目录、不是给原目录加一条边）。
    旧实现挪 ``home → target`` 时会把 ``(other, sub)`` 一起改掉；
    修准后：只动 ``(home, sub)``，``parent_id`` 跟着更新，``(other, sub)`` 原样保留。
    """
    from src.core.knowledge import folder_store as fs
    c, token = client
    home = _new(c, token)
    other = _new(c, token)
    target = _new(c, token)
    sub = _new(c, token, uniq("两处"), home["folder_id"])
    assert fs.copy_member("folder", sub["folder_id"], other["folder_id"])["added"] is True

    got = data_of(api(c, token, "post", f"/api/v1/kb/folders/{sub['folder_id']}/move",
                      json={"from_parent_id": home["folder_id"],
                            "to_parent_id": target["folder_id"]}))
    assert got["updated_main_position"] is True
    assert got["parent_id"] == target["folder_id"]

    def kids(folder: dict):
        return [s["folder_id"] for s in data_of(
            api(c, token, "get", "/api/v1/kb/folders",
                params={"parent_id": folder["folder_id"]}))["subfolders"]]

    assert kids(target) == [sub["folder_id"]]
    assert kids(home) == []
    # ⚠ "复制出来的那一处"**不动**（旧实现会把它一起改掉）
    assert kids(other) == [sub["folder_id"]]


def test_move_from_a_place_that_does_not_hold_it_is_409(client):
    c, token = client
    a = _new(c, token)
    b = _new(c, token)
    st, code = error_code(api(c, token, "post", f"/api/v1/kb/folders/{a['folder_id']}/move",
                              json={"from_parent_id": b["folder_id"], "to_parent_id": None}))
    assert (st, code) == (409, "folder_not_in_parent")


def test_move_rejects_own_subtree(client):
    c, token = client
    a = _new(c, token)
    b = _new(c, token, uniq("环子"), a["folder_id"])
    c2 = _new(c, token, uniq("环孙"), b["folder_id"])
    for target in (a["folder_id"], b["folder_id"], c2["folder_id"]):
        st, code = error_code(api(c, token, "post", f"/api/v1/kb/folders/{a['folder_id']}/move",
                                  json={"to_parent_id": target}))
        assert (st, code) == (422, "folder_cycle"), target
    # 报错后层级一动没动
    assert [s["folder_id"] for s in data_of(
        api(c, token, "get", "/api/v1/kb/folders",
            params={"parent_id": a["folder_id"]}))["subfolders"]] == [b["folder_id"]]


# ─────────────────────────── 复制 ───────────────────────────

def test_copy_folder_shares_members(client, db):
    c, token = client
    src = _new(c, token)
    d = mkdoc_full(db, f"cp_{next(_seq)}")
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": src["folder_id"], "items": [{"kind": "file", "id": d}]})
    copy = data_of(api(c, token, "post", f"/api/v1/kb/folders/{src['folder_id']}/copy",
                       json={}))
    assert copy["folder_id"] != src["folder_id"]
    items = data_of(api(c, token, "get", f"/api/v1/kb/folders/{copy['folder_id']}/items"))
    assert [x["doc_id"] for x in items["items"]] == [d]
    # 从原目录拿掉后副本仍有它（**共享同一份**，不是拷了一份）
    api(c, token, "post", "/api/v1/kb/members/remove",
        json={"folder_id": src["folder_id"], "items": [{"kind": "file", "id": d}]})
    items2 = data_of(api(c, token, "get", f"/api/v1/kb/folders/{copy['folder_id']}/items"))
    assert [x["doc_id"] for x in items2["items"]] == [d]


def test_copy_into_own_subtree_is_422(client):
    c, token = client
    a = _new(c, token)
    b = _new(c, token, uniq("复制环"), a["folder_id"])
    st, code = error_code(api(c, token, "post", f"/api/v1/kb/folders/{a['folder_id']}/copy",
                              json={"to_parent_id": b["folder_id"]}))
    assert (st, code) == (422, "folder_cycle")


# ─────────────────────────── 删 ───────────────────────────

def test_delete_empty_folder_directly(client):
    c, token = client
    f = _new(c, token)
    got = data_of(api(c, token, "delete", f"/api/v1/kb/folders/{f['folder_id']}"))
    assert got["mode"] == "empty" and got["removed"] is True
    st, _ = error_code(api(c, token, "get", "/api/v1/kb/folders",
                           params={"parent_id": f["folder_id"]}))
    assert st == 404


def test_delete_nonempty_without_mode_is_409(client, db):
    c, token = client
    f = _new(c, token)
    d = mkdoc_full(db, f"del_{next(_seq)}")
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": f["folder_id"], "items": [{"kind": "file", "id": d}]})
    resp = api(c, token, "delete", f"/api/v1/kb/folders/{f['folder_id']}")
    st, code = error_code(resp)
    assert (st, code) == (409, "folder_delete_mode_required")
    # 报错要能给人话：两个模式都点到名
    msg = resp.json()["message"]
    assert "reparent" in msg and "purge" in msg
    st, code = error_code(api(c, token, "delete", f"/api/v1/kb/folders/{f['folder_id']}",
                              params={"mode": "bogus"}))
    assert (st, code) == (422, "invalid_delete_mode")
    # 报错后什么都没动
    assert data_of(api(c, token, "get",
                       f"/api/v1/kb/folders/{f['folder_id']}/items"))["total"] == 1


def test_delete_top_level_reparent_rejected_when_nonempty(client, db):
    c, token = client
    f = _new(c, token, uniq("顶层非空"))
    api(c, token, "post", f"/api/v1/kb/folders/{f['folder_id']}/move",
        json={"to_parent_id": None})
    d = mkdoc_full(db, f"topdel_{next(_seq)}")
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": f["folder_id"], "items": [{"kind": "file", "id": d}]})
    resp = api(c, token, "delete", f"/api/v1/kb/folders/{f['folder_id']}",
               params={"mode": "reparent"})
    st, code = error_code(resp)
    assert (st, code) == (409, "folder_top_level_no_parent")
    assert "上一层" in resp.json()["message"]
    # 目录与文件都还在（报错不能有副作用）
    assert data_of(api(c, token, "get",
                       f"/api/v1/kb/folders/{f['folder_id']}/items"))["total"] == 1


def test_delete_purge_keeps_files_present_elsewhere(client, db):
    c, token = client
    keep = _new(c, token)
    doomed = _new(c, token)
    sub = _new(c, token, uniq("要删的子"), doomed["folder_id"])
    shared = mkdoc_full(db, f"pg_shared_{next(_seq)}")
    lonely = mkdoc_full(db, f"pg_lonely_{next(_seq)}")
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": keep["folder_id"], "items": [{"kind": "file", "id": shared}]})
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": doomed["folder_id"], "items": [{"kind": "file", "id": shared}]})
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": sub["folder_id"], "items": [{"kind": "file", "id": lonely}]})
    got = data_of(api(c, token, "delete", f"/api/v1/kb/folders/{doomed['folder_id']}",
                      params={"mode": "purge"}))
    assert got["mode"] == "purge" and got["purged_folders"] == 2
    assert got["unfiled_docs"] == 1 and got["deleted_docs"] == 1
    assert db.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id=?", (shared,)).fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id=?", (lonely,)).fetchone()[0] == 0
    assert [x["doc_id"] for x in data_of(
        api(c, token, "get", f"/api/v1/kb/folders/{keep['folder_id']}/items"))["items"]] \
        == [shared]


def test_delete_preview_numbers(client, db):
    c, token = client
    shared = mkdoc_full(db, f"prev_{next(_seq)}")
    lonely = mkdoc_full(db, f"prev2_{next(_seq)}")
    nest = _new(c, token)                     # 非一级目录（挂在顶层下）
    other = _new(c, token, uniq("问句别的"), nest["folder_id"])
    f = _new(c, token, uniq("问句一级"))
    api(c, token, "post", f"/api/v1/kb/folders/{f['folder_id']}/move",
        json={"to_parent_id": None})
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": other["folder_id"], "items": [{"kind": "file", "id": shared}]})
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": f["folder_id"],
              "items": [{"kind": "file", "id": shared}, {"kind": "file", "id": lonely}]})
    got = data_of(api(c, token, "get", f"/api/v1/kb/folders/{f['folder_id']}/delete-preview"))
    assert got["is_empty"] is False
    assert got["reparent_available"] is False          # 一级目录没有上一层
    assert got["files_kept_elsewhere"] == 1
    assert got["files_would_be_deleted"] == 1
    # 非一级目录：同一组数字（shared 还在 f 里 = 子树**之外**）⇒ 一篇都不真删
    got2 = data_of(api(c, token, "get",
                       f"/api/v1/kb/folders/{other['folder_id']}/delete-preview"))
    assert got2["reparent_available"] is True
    assert got2["files_kept_elsewhere"] == 1 and got2["files_would_be_deleted"] == 0
    # 空目录
    empty = _new(c, token)
    assert data_of(api(c, token, "get",
                       f"/api/v1/kb/folders/{empty['folder_id']}/delete-preview"))["is_empty"] \
        is True


def test_delete_unknown_folder_is_404(client):
    c, token = client
    st, code = error_code(api(c, token, "delete", "/api/v1/kb/folders/fld_nope"))
    assert (st, code) == (404, "folder_not_found")


# ─────────────────────────── 成员批量 ───────────────────────────

def test_members_add_is_idempotent(client, db):
    c, token = client
    f = _new(c, token)
    d = mkdoc_full(db, f"mb_{next(_seq)}")
    payload = {"folder_id": f["folder_id"], "items": [{"kind": "file", "id": d}]}
    first = data_of(api(c, token, "post", "/api/v1/kb/members", json=payload))
    assert (first["added"], first["skipped"]) == (1, 0)
    second = data_of(api(c, token, "post", "/api/v1/kb/members", json=payload))
    assert (second["added"], second["skipped"]) == (0, 1)
    assert db.execute("SELECT COUNT(*) FROM folder_member WHERE folder_id=? AND item_id=?",
                      (f["folder_id"], d)).fetchone()[0] == 1


def test_members_add_errors(client, db):
    c, token = client
    f = _new(c, token)
    st, code = error_code(api(c, token, "post", "/api/v1/kb/members",
                              json={"folder_id": f["folder_id"], "items": []}))
    assert (st, code) == (422, "invalid_decision")
    st, code = error_code(api(c, token, "post", "/api/v1/kb/members",
                              json={"folder_id": f["folder_id"],
                                    "items": [{"kind": "bogus", "id": "x"}]}))
    assert (st, code) == (422, "invalid_decision")
    st, code = error_code(api(c, token, "post", "/api/v1/kb/members",
                              json={"folder_id": "fld_nope",
                                    "items": [{"kind": "file", "id": "x"}]}))
    assert (st, code) == (404, "folder_not_found")
    st, code = error_code(api(c, token, "post", "/api/v1/kb/members",
                              json={"folder_id": f["folder_id"],
                                    "items": [{"kind": "file", "id": "no_such_doc"}]}))
    assert (st, code) == (404, "doc_not_found")


def test_members_remove_move_copy(client, db):
    c, token = client
    a = _new(c, token)
    b = _new(c, token)
    d1 = mkdoc_full(db, f"mm1_{next(_seq)}")
    d2 = mkdoc_full(db, f"mm2_{next(_seq)}")
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": a["folder_id"],
              "items": [{"kind": "file", "id": d1}, {"kind": "file", "id": d2}]})
    # 复制到 b：**多一处位置**（原件不动）
    cp = data_of(api(c, token, "post", "/api/v1/kb/members/copy",
                     json={"to_folder_id": b["folder_id"],
                           "items": [{"kind": "file", "id": d1}]}))
    assert cp["added"] == 1
    assert data_of(api(c, token, "get", f"/api/v1/kb/folders/{a['folder_id']}/items"))["total"] == 2
    # 从 a 挪 d2 到 b
    mv = data_of(api(c, token, "post", "/api/v1/kb/members/move",
                     json={"from_folder_id": a["folder_id"], "to_folder_id": b["folder_id"],
                           "items": [{"kind": "file", "id": d2}]}))
    assert mv["moved"] == 1
    assert data_of(api(c, token, "get",
                       f"/api/v1/kb/folders/{a['folder_id']}/items"))["total"] == 1
    # 从 a 拿掉 d1：**不删文件**
    rm = data_of(api(c, token, "post", "/api/v1/kb/members/remove",
                     json={"folder_id": a["folder_id"],
                           "items": [{"kind": "file", "id": d1}]}))
    assert rm["removed"] == 1
    assert db.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id=?", (d1,)).fetchone()[0] == 1
    assert data_of(api(c, token, "get", f"/api/v1/kb/folders/{a['folder_id']}/items"))["total"] == 0


# ─────────────────────────── 待分类 ───────────────────────────

def test_inbox_lists_unfiled_with_suggestion_only_from_existing(client, db, tops):
    """**只匹配现有目录，绝不自行新建**：路径命中了就给，没命中就 null。"""
    c, token = client
    d_known = mkdoc_full(db, f"in_{next(_seq)}", standard_no=f"GB/T 91{next(_seq):03d}-2020",
                         tags=["CCS:P16 工程防火"])
    d_unknown = mkdoc_full(db, f"in_{next(_seq)}", standard_no=f"GB/T 92{next(_seq):03d}-2020",
                           tags=[])
    page = data_of(api(c, token, "get", "/api/v1/kb/inbox", params={"limit": 200}))
    rows = {r["doc_id"]: r for r in page["items"]}
    assert d_unknown in rows and rows[d_unknown]["stage"] == "queued"
    assert rows[d_unknown]["suggested_folder_id"] is None      # 认不出 ⇒ 不猜、不建
    assert "suggest_new_path" in rows[d_unknown]
    # 已知分类这篇：只有在「标准」下面**真的存在**那层目录时才会给建议
    if rows[d_known]["suggested_folder_id"]:
        assert rows[d_known]["suggested_path"]


def test_inbox_confirm_accept_existing_new(client, db, tops):
    c, token = client
    incoming = _new(c, token, uniq("收件"))
    # 三个顶层「待分类」的子目录：把三篇都先挂进「待分类」这一处
    pend = tops["待分类"]
    docs = [mkdoc_full(db, f"cf_{i}_{next(_seq)}") for i in range(3)]
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": pend, "items": [{"kind": "file", "id": d} for d in docs]})
    # 给第一篇一个**真实存在**的建议目录（走 existing 那篇由调用方指定）
    from src.core.knowledge import folder_store as fs
    fs.set_filing_state(docs[0], "queued", suggested_folder_id=incoming["folder_id"])

    got = data_of(api(c, token, "post", "/api/v1/kb/inbox/confirm", json={"decisions": [
        {"doc_id": docs[0], "action": "accept"},
        {"doc_id": docs[1], "action": "existing", "target_folder_id": incoming["folder_id"]},
        {"doc_id": docs[2], "action": "new", "new_parent_id": incoming["folder_id"],
         "new_name": uniq("新建的子")},
    ]}))
    assert got["confirmed"] == 3
    assert got["removed_from_pending"] == 3          # 自动挪出「待分类」
    assert len(got["created"]) == 1
    # 三篇都 filed，且都不在「待分类」那一处了
    for d in docs:
        assert fs.get_filing_state(d)["stage"] == "filed"
        n = db.execute("SELECT COUNT(*) FROM folder_member WHERE folder_id=? AND item_id=?",
                       (pend, d)).fetchone()[0]
        assert n == 0, d
    # 「待分类」列表里也看不到了
    listed = {r["doc_id"] for r in data_of(
        api(c, token, "get", "/api/v1/kb/inbox", params={"limit": 200}))["items"]}
    assert not (set(docs) & listed)


def test_inbox_confirm_errors_are_atomic(client, db, tops):
    """整批全成或全败：中间一条非法 ⇒ 前面的也不许落。"""
    c, token = client
    from src.core.knowledge import folder_store as fs
    d_ok = mkdoc_full(db, f"atom_{next(_seq)}")
    d_bad = mkdoc_full(db, f"atom2_{next(_seq)}")
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": tops["待分类"], "items": [{"kind": "file", "id": d_ok}]})
    fs.set_filing_state(d_ok, "queued", suggested_folder_id=tops["标准"])
    st, code = error_code(api(c, token, "post", "/api/v1/kb/inbox/confirm",
                              json={"decisions": [
                                  {"doc_id": d_ok, "action": "accept"},
                                  {"doc_id": d_bad, "action": "bogus"},
                              ]}))
    assert (st, code) == (422, "invalid_decision")
    assert fs.get_filing_state(d_ok) is None or \
        fs.get_filing_state(d_ok)["stage"] == "queued"          # 第一条没落
    # 边界：没有建议却 accept / 缺 target / 缺 new_name
    st, code = error_code(api(c, token, "post", "/api/v1/kb/inbox/confirm",
                              json={"decisions": [{"doc_id": d_bad, "action": "accept"}]}))
    assert (st, code) == (422, "no_suggestion")
    st, code = error_code(api(c, token, "post", "/api/v1/kb/inbox/confirm",
                              json={"decisions": [{"doc_id": d_bad, "action": "existing"}]}))
    assert (st, code) == (422, "invalid_decision")
    st, code = error_code(api(c, token, "post", "/api/v1/kb/inbox/confirm",
                              json={"decisions": [{"doc_id": d_bad, "action": "new"}]}))
    assert (st, code) == (422, "invalid_decision")
    st, code = error_code(api(c, token, "post", "/api/v1/kb/inbox/confirm",
                              json={"decisions": []}))
    assert (st, code) == (422, "invalid_decision")


# ─────────────────────────── 范围 ───────────────────────────

def test_scope_resolve_union_and_deeper(client, db):
    c, token = client
    a = _new(c, token)
    b = _new(c, token, uniq("范围子"), a["folder_id"])
    other = _new(c, token)
    d1 = mkdoc_full(db, f"sc_{next(_seq)}")
    d2 = mkdoc_full(db, f"sc2_{next(_seq)}")
    d3 = mkdoc_full(db, f"sc3_{next(_seq)}")
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": a["folder_id"], "items": [{"kind": "file", "id": d1}]})
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": b["folder_id"], "items": [{"kind": "file", "id": d2}]})
    api(c, token, "post", "/api/v1/kb/members",
        json={"folder_id": other["folder_id"], "items": [{"kind": "file", "id": d3}]})
    got = data_of(api(c, token, "post", "/api/v1/kb/scope/resolve",
                      json={"folder_ids": [a["folder_id"], other["folder_id"]]}))
    assert set(got["folder_ids"]) == {a["folder_id"], b["folder_id"], other["folder_id"]}
    assert set(got["doc_ids"]) == {d1, d2, d3}              # 含更深层 + 并集
    assert got["folder_count"] == 3 and got["doc_count"] == 3
    assert got["folder_ids"] == sorted(got["folder_ids"])    # 已排序、可重现


def test_scope_resolve_unknown_is_404_not_empty(client):
    """⚠ 绝不静默返回空范围（空范围会让"在此范围内提问"悄悄变成全库提问）。"""
    c, token = client
    st, code = error_code(api(c, token, "post", "/api/v1/kb/scope/resolve",
                              json={"folder_ids": ["fld_nope"]}))
    assert (st, code) == (404, "folder_not_found")
    st, code = error_code(api(c, token, "post", "/api/v1/kb/scope/resolve",
                              json={"folder_ids": []}))
    assert (st, code) == (422, "invalid_scope")


def test_all_kb_endpoints_require_token(client):
    c, _ = client
    for method, path in (("get", "/api/v1/kb/folders"),
                         ("get", "/api/v1/kb/inbox"),
                         ("get", "/api/v1/kb/folders/fld_x/items"),
                         ("delete", "/api/v1/kb/folders/fld_x")):
        assert getattr(c, method)(path).status_code == 401
