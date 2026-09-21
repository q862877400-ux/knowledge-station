"""``/api/v1/kb/*`` 用例的公共夹具（真库不碰：库是 conftest 的临时库）。

⚠ 为什么单独一个 fixtures 文件：目录名要**复用**
（``folder`` 表有"同名同层拒绝"的两条部分唯一索引），而 pytest 的用例函数拿不到
彼此的局部名字；做成 session 级夹具后，"四个顶层只建一次"就是**结构上**保证的，
不靠每个用例自己记得。
"""
from __future__ import annotations

import itertools

import pytest

from src.core.knowledge import folder_store as fs

_seq = itertools.count()


def uniq(base: str) -> str:
    """本会话内唯一的目录名（session 级库 ⇒ 名字不能撞）。"""
    return f"{base}-kb{next(_seq)}"


def mkdoc(db, doc_id: str) -> str:
    """插一篇最小可用的文档（目录归属只认 doc_meta 里有这一行）。"""
    return mkdoc_full(db, doc_id)


def mkdoc_full(db, doc_id: str, *, standard_no: str | None = None,
               standard_name: str | None = None, tags: list[str] | None = None,
               doc_type: str = "standard", hierarchy: str | None = None) -> str:
    """插一篇文档（可带分类信息 ⇒ 让"建议去向"能算出路径）。

    ⚠ ``standard_no`` **必须全局唯一**（``doc_meta`` 上有唯一约束），而这个库是
    **session 级**的（整个测试会话共用一个临时库）⇒ 默认值带 ``doc_id``
    （调用方已经用序号保证它唯一），**绝不**写死 ``GB 50016-2014`` 这种
    别的用例文件也在用的号 —— 一撞就是 ``UNIQUE constraint failed``，
    而且报错的是**别人**的用例。
    """
    import json
    db.execute(
        "INSERT OR IGNORE INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash, legal_hierarchy,"
        " doc_type) VALUES (?,?,?,?,'r1',?,?,?,?,?)",
        (doc_id, standard_no or doc_id, standard_name or f"名-{doc_id}", doc_id,
         json.dumps(tags or []), "a.pdf", f"h-{doc_id}", hierarchy, doc_type))
    db.commit()
    return doc_id


@pytest.fixture()
def tops(db):
    """四个顶层目录（业主手定 sort 10/20/30/90）——**按名字复用**，用例间共用。

    ⚠ 依赖 ``db``（它才跑 ``init_schema`` + 两个 ``ensure_additive_columns``）。
    做成 ``session`` 级会让它先于 ``db`` 跑 ⇒ ``no such table: folder``。
    """
    names = (("标准", 10), ("法律法规", 20), ("公司制度", 30), ("待分类", 90))
    out: dict[str, str] = {}
    for name, sort in names:
        found = fs._find_child_by_name(fs.get_db_connection(), None, name)
        out[name] = found if found else fs.create_folder(name, None, sort=sort)["folder_id"]
    return out


#: **真形状**的标准树路径（顶层「标准」→ CCS 大类 → 区间 → 具体类目）。
#: 口径来源 = ``classify_document(CCS:P16 工程防火)``；⚠ **故意没有**「国家标准·行业标准·
#: 团体标准」那一段 —— 真树跳过了它（唯一所有者 `folder_filing_plan.tree_path_of`）。
#: 用这条路径才能证明"建议去向"与真树对齐（复核 2026-09-21：拿分类口径原名匹配 ⇒ 0 命中）。
STD_TREE_P16: tuple[str, ...] = (
    "标准", "P 土木、建筑", "P15/19 工程抗震、工程防火、人防工程", "P16 工程防火")


def ensure_folder_path(parts: tuple[str, ...]) -> dict[str, str]:
    """按名字路径**复用或新建**一串目录，返回 ``{名字: folder_id}``（幂等）。"""
    out: dict[str, str] = {}
    parent: str | None = None
    for name in parts:
        found = fs._find_child_by_name(fs.get_db_connection(), parent, name)
        parent = found if found else fs.create_folder(name, parent)["folder_id"]
        out[name] = parent
    return out


@pytest.fixture()
def std_tree(db, tops):
    """真形状的标准树（CCS P16 那一支）——共用，用例间幂等复用。"""
    return ensure_folder_path(STD_TREE_P16)


def api(c, token, method: str, path: str, **kw):
    """带 token 的请求（``json`` / ``params`` 透传）。"""
    fn = getattr(c, method)
    return fn(path, headers={"Authorization": f"Bearer {token}"}, **kw)


def data_of(resp) -> dict:
    assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert body.get("status") == "success", body
    return body["data"]


def error_code(resp) -> tuple[int, str]:
    body = resp.json()
    return resp.status_code, str(body.get("error") or "")
