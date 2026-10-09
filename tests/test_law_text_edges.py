"""`ingest_law_text` 的证据边**归属**契约（2026-10-09 真缺陷的回归判据）。

## 缺陷（真库只读实测确认）

`src/core/ingestion/law_text.py` 建边那一步原本写的是：

    edges = [(t, number_to_id[m.clause_number], number_to_id[ref])
             for t, src, ref in raw_edges
             if src in number_to_id and ref in number_to_id]

`m` 是**上一个 `for m in models:` 循环结束后残留的变量**（Python 的 for 不产生新作用域，
循环跑完 `m` 停在 `models` 的**最后一个模型**）⇒ **每条边的 source 都被解析成
「最后一条条款」的 id**。后果**两个方向都错**：
① 最后一条凭空多出整份文档的引用边；② 其余条款的引用边**从来没进图**。

真库读数（2026-10-09）：
* 出度最高的那条 =《民事诉讼法解释(OCR采集)》**第五百五十二条**（正文 106 字、
  自身 `cross_refs` 为 `[]`）却挂 **204 条出边** —— **恰好等于该文档全部 cross_refs 条目数**，
  去重后目标数（106）也逐项相等；
* 全库 **845 条**条款呈同一形状，**99.9% 是各文档的最后一条**、
  **99.6% 属于 `lawrefbook://` 文档**（该来源共 1,430 份）。

## 本测试抓什么

一份 3 条的小法：**第一条**与**第二条**都引用**第三条**（被引用方是最后一条）。
* 正确 ⇒ 两条边，source 分别是第一 / 第二条；
* 带缺陷 ⇒ 两条边的 source **都变成第三条**（自环）⇒ 下面的断言必红。

⚠ 三条判据**各自**都有牙：① 只看 source 归属；② 只看"最后一条有没有出边"；
③ 只看边数。任一处被改回残留变量写法，至少一条会红。

⚠ `ingest_law_text` 按**内容哈希**去重（同文本第二次入返回 `duplicate`）⇒ 三条判据
共用**一次**入库（模块级夹具）。`_isolate_data_dir` 是**会话级**夹具，模块级安全。
"""
import pytest

from src.core.ingestion.law_text import ingest_law_text
from src.core.storage.sqlite_db import get_db_connection

LAW_TWO_REFER = """# 示例引用法

第一条 办理本事项，依照第三条的规定执行。

第二条 办理本事项，依照第三条的规定执行。

第三条 本条是被引用的依据条款，它自己不引用任何条款。
"""


@pytest.fixture(scope="module")
def two_refer_doc() -> str:
    r = ingest_law_text(LAW_TWO_REFER, "示例引用法·测试", "示例引用法·测试")
    assert r["status"] == "ok", r
    return r["doc_id"]


def _edges_of(doc_id: str) -> set[tuple[str, str]]:
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT src.clause_number, dst.clause_number
        FROM evidence_edge e
        JOIN clause_revision src ON src.clause_revision_id = e.source_clause_id
        JOIN clause_revision dst ON dst.clause_revision_id = e.target_clause_id
        WHERE e.edge_type = 'reference_relation' AND src.doc_id = ?
        """, (doc_id,)).fetchall()
    return {(s, d) for s, d in rows}


def test_edge_source_is_the_referring_clause(two_refer_doc):
    """边的 source 必须是**引用别人的那一条**，不是"文档的最后一条"。"""
    got = _edges_of(two_refer_doc)
    assert got == {("第一条", "第三条"), ("第二条", "第三条")}, (
        f"边的 source 挂错了（期望第一/第二条引用第三条）：{sorted(got)}")


def test_last_clause_has_no_outgoing_edges(two_refer_doc):
    """反向：被引用的**最后一条**不该凭空多出任何出边（缺陷的签名就是它）。"""
    got = _edges_of(two_refer_doc)
    assert not any(s == "第三条" for s, _ in got), (
        f"最后一条凭空多了出边：{sorted(got)}")


def test_edge_count_matches_reference_sites(two_refer_doc):
    """边的**条数**也要对：该文档共 2 处引用 ⇒ 恰好 2 条边（不多不少）。"""
    assert len(_edges_of(two_refer_doc)) == 2, "边数不等于实际引用处数"
