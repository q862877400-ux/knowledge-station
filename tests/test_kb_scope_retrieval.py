# -*- coding: utf-8 -*-
"""第 6 步「按目录范围提问」：**检索层**的范围过滤（六条通道）+ 答案层的范围契约。

## 这组用例在守什么（每条都有反向）

1. **范围内答得出 / 范围外答不出**（两个方向都要）——范围是真的在**检索层**生效，
   不是"取回 top_k 之后再筛"：那条老路会让范围外的命中**吃掉候选名额**，症状是
   "范围内明明有、却答不出"。两条用例专门钉它，且**都带前提断言**
   （`test_scope_filter_is_in_retrieval_not_post_filter` 与
   `test_answer_still_answers_when_out_of_scope_hits_saturate_topk`：
   先断言"不留范围时第一名在范围外"，前提不成立 ⇒ **判据自己红**）。
   ⚠ 复核 HIGH-1 打回前，这两条靠"碰巧的语料统计"才红（单独跑是绿的）—— 详见各条 docstring。
2. **六条召回通道**（exact / fts / vec / modality / legal_element / behavior_scope）
   **每一条**都被范围约束（不许只堵一条）。
3. **空范围绝不许退化成全库**（照 `folder_scope` / `scope/resolve` 的既有立论）：
   `doc_ids=[]` ⇒ 一条都不返回；答案层 `kb_doc_ids=[]` ⇒ **不做任何检索**、如实说"范围内没有"。
4. **两种"夹"不混**：`folder_id`（收藏夹）仍旧只对**证据**做后置过滤、**不动检索**；
   `kb_folder_ids`（知识库目录）才是检索层范围；两者同时给 ⇒ 证据是**交集**。
5. **目录不存在 ⇒ 报错（不是空范围、更不是全库）**：`KbScopeNotFound`（端点 404）。

⚠ 本文件**自己隔离**（私有临时数据目录，照 `tests/test_ks_answer.py` 的先例）：用例真的建库、
真的插条款，不隔离就会写进会话级共享库、污染别的模块（第 5 步被复核抓过一次）。
⚠ 向量通道那条**不依赖 BGE**：直接往 `clause_vec` 塞假向量（512 维）⇒ 模型离线也能验"向量通道被堵住"。
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.core.domain.models import ClauseRevisionModel
from src.core.storage import clause_repo


@pytest.fixture(scope="module", autouse=True)
def _own_data_dir():
    """本模块私有的临时数据目录（跑完即弃；其他模块零影响，见文件头）。

    ⚠⚠ **2026-09-22（父代理点名的缺陷：每跑一次漏一个 ~2.6 MB 的 `ks_scope_*`）**：
    以前这里写的是 `tempfile.TemporaryDirectory(prefix="ks_scope_", ignore_cleanup_errors=True)`。
    根因**不是**"忘了关连接"，而是本模块最后两条用例走 `client` fixture ——
    FastAPI 的**同步**路由跑在 **AnyIO 线程池的 worker 线程**里，那些线程自己 `get_db_connection()`
    建了一份、且**比用例活得长**；`close_thread_connection()` 只关**当前**线程那一份 ⇒
    Windows 上 `knowledge.db` 一直被占着（`WinError 32`），而 `ignore_cleanup_errors=True`
    把这条失败**静默吞掉**（实测取证见 `var/tmp/probe_conn_holder.py`：
    sessionfinish 时那条 worker 线程的连接仍 `QUERYABLE`）。
    ⇒ 现在：① `close_all_connections()` 真把**所有线程**那份关掉（并摘掉那个线程 `_local` 里的键，
    不摘的话那个被复用的线程下次会拿到已关闭的连接）；② 清理**自己做**
    （`mkdtemp` + `shutil.rmtree` + 退避重试），仍失败就**抛出去**（teardown 报 error），**不许静默**。

    ⚠⚠ **2026-09-22 我自己踩的第二个坑（全量跑才现形，单跑恒绿）**：重写时把原来 setup 里的
    `close_thread_connection()` 漏掉了 ⇒ 全量跑时**主线程**手里还攥着**上一个模块**（会话库）的连接，
    于是 `init_schema()` 把种子数据写进了**会话库**，而最后两条走 `client` 的用例在 **worker 线程**里
    按**新** `KS_DATA_DIR` 打开的是我这个空目录 ⇒ 那两条红（`404/422` 对不上）。
    ⇒ setup 里也要关：**只关当前线程是不够的**（worker 线程那份同样会指向上一个库），
    所以 setup/teardown 两处都调 `close_all_connections()` —— 关掉之后每一条线程下次
    `get_db_connection()` 会按**当时的** `KS_DATA_DIR` 重新建连接。
    """
    import gc
    import shutil
    import time

    from src.core.storage.sqlite_db import close_all_connections, close_thread_connection

    td = Path(tempfile.mkdtemp(prefix="ks_scope_"))
    old = os.environ.get("KS_DATA_DIR")
    os.environ["KS_DATA_DIR"] = str(td)
    from src.core import config
    config.reset_settings()
    # ⚠ 必须在 init_schema **之前**：把上个模块留在**任何线程**里的连接关掉（含主线程），
    #   否则种子数据会写进上一个库（见上面那段留痕）。
    close_thread_connection()
    close_all_connections()
    from src.core.storage.sqlite_db import init_schema
    init_schema()
    try:
        yield td
    finally:
        config.reset_settings()
        close_thread_connection()
        close_all_connections()
        gc.collect()
        if old is None:
            os.environ.pop("KS_DATA_DIR", None)
        else:
            os.environ["KS_DATA_DIR"] = old
        last: OSError | None = None
        for delay in (0.0, 0.2, 0.5, 1.0):
            if delay:
                time.sleep(delay)
            try:
                shutil.rmtree(td)
                last = None
                break
            except OSError as e:  # noqa: PERF203 - 退避重试，故意逐个接
                last = e
        if last is not None:
            raise AssertionError(
                "本模块的临时数据目录没清掉（清理失败**不许静默**）："
                f"{td} —— {type(last).__name__}: {last}")


@pytest.fixture(autouse=True)
def _offline_embedder(monkeypatch):
    """向量引擎强制离线（与 `test_ks_answer` 同一手法）：不加载模型、不去下模型。"""
    from src.core.retrieval import embedder as _emb
    monkeypatch.setattr(_emb, "is_available", lambda: False)
    yield


def _clause(cid: str, no: str, text: str, doc: str, standard: str = "GB 50016-2022",
            modality: str | None = None, subject: str | None = None,
            behavior_scope: str | None = None, ktype: str = "rule") -> ClauseRevisionModel:
    return ClauseRevisionModel(
        clause_revision_id=cid, doc_id=doc, clause_key=f"key_{cid}",
        standard_no=standard, clause_number=no, title=None, content_text=text,
        knowledge_type=ktype, modality=modality,
        modality_strength={"严禁": 5, "不应": 4, "应": 3}.get(modality),
        subject=subject, behavior_scope=behavior_scope,
        legal_status="effective", page_start=1, page_end=1)


@pytest.fixture(scope="module")
def scope_db(_own_data_dir):
    """两篇文档：`in_doc`（**范围内**）与 `out_doc`（**范围外**），各带六条通道要用的条款。"""
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    docs = [
        dict(doc_id="in_doc", standard_no="GB 90001-2026", standard_name="范围内那份标准",
             short_code="GB90001", current_revision_id="r_in",
             domain_tags=["测试"], file_path="in.pdf", file_hash="h_in"),
        dict(doc_id="out_doc", standard_no="GB 90002-2026", standard_name="范围外那份标准",
             short_code="GB90002", current_revision_id="r_out",
             domain_tags=["测试"], file_path="out.pdf", file_hash="h_out"),
    ]
    for d in docs:
        clause_repo.insert_document(conn, d)
    # ⚠⚠ **2026-09-21（复核 HIGH-1 打回后重做）**：这段 fixture 的**排序前提**以前是错的 ——
    #   旧注释写着"范围外 3 条**强命中**……正是会被 top_k 吃掉的那批"，而复核实测
    #   全局 FTS 第一名其实是**范围内**那条（`['in_exact','out_hot2','out_hot1',…]`）：
    #   BM25 的**长度归一**让短正文的 `in_exact` 压过了关键词重复更多的 `out_hot1`。
    #   后果：把范围挪到"取回之后"（合法变异）时，**那两条用例单独跑都是绿的**
    #   （只有先跑的向量用例塞了 25 行、改了语料统计之后才偶然翻成红）。
    # ⇒ 现在把三条正文改成**长度/词频都拉开**，并让用例先断言"不留范围时第一名确实在范围外"
    #   （前提不成立 ⇒ **判据自己红**，不许"碰巧红"）。测出来的序见下面两条用例的断言消息。
    clause_repo.insert_clauses([
        # 范围内：一条**很长**的弱命中（只提到一次防火间距）——长正文 ⇒ BM25 分数低
        _clause("in_weak", "1.0.1",
                "范围内的普通条款（只提到一次防火间距）。"
                + "本条其余文字与查询无关，纯粹用来把正文拉长、压低它在 BM25 里的得分："
                + "甲乙丙丁戊己庚辛壬癸甲乙丙丁戊己庚辛壬癸甲乙丙丁戊己庚辛壬癸甲乙丙丁戊己庚辛壬癸。",
                "in_doc"),
        # 范围内：精确号那条（命中全部查询词，但正文也不短 ⇒ 全局排名**不是**第一）
        _clause("in_exact", "5.2.3",
                "范围内的精确号条款：防火间距不应小于13m。"
                + "本条其余文字同样与查询无关，用来保证「全局第一名在范围外」这个前提成立："
                + "子丑寅卯辰巳午未申酉戌亥子丑寅卯辰巳午未申酉戌亥子丑寅卯辰巳午未申酉戌亥。",
                "in_doc"),
        _clause("in_mod", "1.0.2", "范围内模态条款", "in_doc", modality="严禁"),
        _clause("in_sub", "1.0.3", "范围内义务主体条款", "in_doc", ktype="legal",
                subject="建设单位"),
        _clause("in_beh", "1.0.4", "范围内行为客体条款", "in_doc",
                behavior_scope="动火作业 审批"),
        # 范围外：**真的**强命中 —— 正文短 + 查询词重复三次 ⇒ 全局第一名（用例里有前提断言钉它）
        _clause("out_hot1", "5.2.3",
                "防火间距不应小于13m防火间距不应小于13m防火间距不应小于13m", "out_doc",
                standard="GB 90002-2026"),
        _clause("out_hot2", "5.2.3",
                "范围外强命中：防火间距 不应小于13m（这一条正文比上面那条长，用来当第二名对照）",
                "out_doc", standard="GB 90002-2026"),
        _clause("out_hot3", "1.0.9", "范围外强命中：防火间距与防火分区", "out_doc",
                standard="GB 90002-2026", modality="严禁", ktype="legal", subject="建设单位",
                behavior_scope="动火作业 审批"),
    ])
    return conn


IN_SCOPE = ["in_doc"]
OUT_SCOPE = ["out_doc"]


def _ids(rows) -> list[str]:
    return [r.clause_revision_id for r in rows]


# ═════════════ 1. 两个方向：范围内答得出 / 范围外答不出 ═════════════

def test_answer_is_findable_only_inside_the_scope(scope_db):
    """范围 = 范围内那篇 ⇒ 命中；范围 = 范围外那篇 ⇒ **同一条条款查不到**（两个方向都判）。"""
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    hit = perform_hybrid_search("5.2.3", top_k=5, channels=["exact"], doc_ids=IN_SCOPE)
    assert "in_exact" in _ids(hit), f"范围内应当查得到那条：{_ids(hit)}"
    miss = perform_hybrid_search("5.2.3", top_k=5, channels=["exact"], doc_ids=OUT_SCOPE)
    assert "in_exact" not in _ids(miss), f"范围外**不许**返回范围内的条款：{_ids(miss)}"
    assert "out_hot1" in _ids(miss), "范围外那篇自己的条款应当查得到（否则是过度过滤）"


def test_unrestricted_search_still_sees_both(scope_db):
    """反向哨兵：不给范围（`doc_ids=None`）时**两篇都能查到** —— 证明上一条不是"检索坏了"。"""
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    both = _ids(perform_hybrid_search("5.2.3", top_k=10, channels=["exact"]))
    assert "in_exact" in both and "out_hot1" in both, both


def test_scope_filter_is_in_retrieval_not_post_filter(scope_db):
    """**核心判据**：范围过滤必须发生在**检索层**。

    场景：`top_k=1`、`channels=["fts"]`、查询 = 两条正文都命中的那句。
      · 若过滤发生在"取回 top_k 之后"⇒ 候选按**全库**排序，前 1 名是**范围外**那条 ⇒ 筛完**空**、
        "范围内明明有却答不出"（这正是任务书点名要避免的那种实现）；
      · 在检索层过滤 ⇒ 候选里只有范围内那条 ⇒ **必须返回它**。

    ⚠⚠ **2026-09-21（复核 HIGH-1 打回后补的前提断言）**：这条用例以前**抓不住**那个形态 ——
    它默认"全库第 1 名在范围外"，而实测当时全库第 1 名是**范围内**的 `in_exact`
    （BM25 长度归一）⇒ 把范围挪到取回之后它**单独跑照样绿**。现在先断言前提：
    **不留范围时 `top_k=1` 必须是 `out_hot1`（范围外那条）**；前提不成立 ⇒ **这条自己红**，
    而不是悄悄退化成恒真（棘轮看不见"把断言换成恒真"，这条前提断言正是补它的）。
    """
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    q = "防火间距 不应小于13m"
    # ① 前提（不许省）：不留范围时第一名**确实**在范围外
    unrestricted = _ids(perform_hybrid_search(q, top_k=1, channels=["fts"], rerank=False))
    assert unrestricted == ["out_hot1"], (
        "**前提不成立**：不留范围时 FTS 第一名应当是范围外的 out_hot1，实测 "
        f"{unrestricted} —— 这样这条用例根本无法区分「检索层过滤」与「取回后再筛」"
        "（两者都会返回范围内那条）。要么调 fixture 让范围外那条真的排第一，"
        "要么换一个前提成立的查询；**不许**就这样放过（那会让本判据变成恒真）")
    # ② 判据本体：范围内 top_k=1 ⇒ 必须是范围内那条（取回后筛的写法会返回空）
    res = perform_hybrid_search(q, top_k=1, channels=["fts"], rerank=False, doc_ids=IN_SCOPE)
    assert _ids(res) == ["in_exact"], (
        "范围内那条没被返回 ⇒ 过滤很可能发生在取回之后（top_k 被范围外的命中吃掉了）："
        f"{_ids(res)}")


# ═════════════ 2. 六条通道都被堵住 ═════════════

def test_every_channel_is_restricted(scope_db):
    """六条召回通道**逐条**验证：范围外的那篇在任何一条通道上都进不来。"""
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    cases = [
        ("exact", dict(query="5.2.3", channels=["exact"]), "in_exact"),
        ("fts", dict(query="防火间距", channels=["fts"]), "in_weak"),
        ("modality", dict(query="严禁使用", channels=["modality"],
                          modality_filter="严禁"), "in_mod"),
        ("legal_element", dict(query="建设单位", channels=["legal_element"],
                               subject_filter="建设单位"), "in_sub"),
        ("behavior_scope", dict(query="动火作业", channels=["behavior_scope"],
                                behavior_scope_filter="动火作业"), "in_beh"),
    ]
    for name, kwargs, expected_in in cases:
        rows = perform_hybrid_search(top_k=10, rerank=False, doc_ids=IN_SCOPE, **kwargs)
        ids = _ids(rows)
        assert expected_in in ids, f"通道 {name} 在范围内应当有命中：{ids}"
        assert not any(i.startswith("out_") for i in ids), \
            f"通道 {name} **没被范围堵住**：{ids}"
    # 向量通道单独判（不依赖模型，见下面那条）


def test_vec_channel_is_restricted_without_the_model(scope_db, monkeypatch):
    """**向量通道**也要被堵住 —— 直接塞假向量，模型离线也能验。

    ⚠ 实测口径（`var/tmp/probe-vec-scope.py`，sqlite-vec v0.1.9 / SQLite 3.53.1）——
    **两句分开写**（复核 INFO-2 指出上一版把两种形态混成一句"先 KNN 再筛"，会让人推出错误的容量结论）：
      1. **子查询**形式（`clause_revision_id IN (SELECT … json_each(?))`）是**带约束的 KNN**：
         25 条更近的范围外行也压不掉范围内那条（本用例判的就是它）；
      2. **双元素字面量列表**（`IN ('a','b')`）比"先 KNN 再筛"**更糟**：它**连全局 top-k 里
         本来有的那条也返回 0 行**（复核在"只有一行"的表上也是 0 行）；
         真正"先 KNN 再筛"的是**单字面量/等值**写法（`clause_revision_id = ?`）。
    ⇒ 结论不变（**只许用子查询**），但别再照"先 KNN 再筛"推理容量。

    ⚠⚠ **2026-10-09 就地更正（第 17 轮，自动续接链）—— 上面那句"子查询 = 带约束的 KNN"【只在
    范围恰好落到 1 个条款 id 时成立】。这条用例现在**红得有道理**，它抓到的是真缺陷。**

    **最小复现**（`sqlite-vec 0.1.9` / `SQLite 3.53.1`，与本文件钉的版本完全一致；表 = `vec0(…,
    embedding FLOAT[512])`，查询向量与 25 条**范围外**近邻完全相同 ⇒ 全局 top-20 全是它们）：

    | 范围内**有向量的**条款 | 范围内 `clause_revision` 的**行数** | `IN (SELECT …)` 的结果 |
    |---|---|---|
    | 1 | 1 | **`['in_weak']`**（下推成功） |
    | 1 | 2 | **`[]`**（**没下推**） |
    | 1 | 3 / 5 / 10 | **`[]`** |

    ⇒ 判据是**范围子查询返回几个 id**，不是"有没有用子查询"：**≥2 个就退化成"先 KNN 再筛"**。
    三种写法都试过（`IN (SELECT value FROM json_each(?))` 直接把 id 列表喂进去 / 两级子查询 /
    单等值），**≥2 个 id 时全都返回 `[]`**（单等值本来就被本条文档认定为"先 KNN 再筛"）。

    **本用例为什么因此红**：fixture 给的 `in_doc` 有 **5 条**条款（`in_weak` / `in_exact` /
    `in_mod` / `in_sub` / `in_beh`）⇒ 范围子查询返回 **5 个 id** ⇒ 下推不发生 ⇒ 返回 `[]`。
    （fixture 在 2026-09-21 因复核 HIGH-1 重做过、条款集变过；重做后这条用例的前提就不再成立，
    而**它当时没有进任何会跑到它的门禁** —— `-Full` 那时跑不完 —— 所以一直没人发现。）

    ⇒ **结论：`hybrid_engine` 的向量通道【没能真的】把范围约束下推进 KNN**（对"一个目录下通常有
    几十上百条条款"的真实用法尤其如此）⇒ 「按目录范围提问」在向量这一路上会**假报"范围内没有"**。
    **这是待修的真缺陷，不是判据要放宽**（本用例保持红）。修法要动 schema 侧
    （给 `vec0` 加 `doc_id` 辅助列做元数据过滤，或分区）⇒ 属**必验类别**，需单独立项。

    ---
    ✅ **2026-10-09 已修（`specs/003-vec-scope-pushdown/`）**：给 `clause_vec` 加 `doc_id`
    **元数据列**，向量通道的范围过滤改走 `doc_id IN (SELECT value FROM json_each(?))` ——
    实测**只有这一种写法能下推**（字面量列表 / `OR` 会返回范围外，见该 spec 的 research.md R2）。
    **本用例断言一个字未改**：转绿即证明修复成立（夹具补了 `doc_id`，属前提而非判据）。
    """
    from src.core.retrieval import embedder as emb
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage.sqlite_db import get_db_connection, load_vec_extension
    conn = get_db_connection()
    load_vec_extension(conn)
    # 方向：in_weak 与查询向量最**远**、out_hot1/2 最近 ⇒ 若"先 KNN 再筛"，范围内一条都不剩
    vecs = {
        "in_weak": [0.0] * 511 + [1.0],
        "out_hot1": [1.0] + [0.0] * 511,
        "out_hot2": [0.9, 0.1] + [0.0] * 510,
    }
    # ⚠ 再灌 25 条**范围外**、与查询向量完全一致的近邻：全局 top-20 全是它们 ⇒
    #   "先 KNN 再筛"的写法会返回**空**（假报"范围内没有"）；带约束地找 k 个才会返回范围内那条。
    clause_repo.insert_clauses([
        _clause(f"out_bulk{i}", f"9.9.{i}", "范围外批量近邻", "out_doc",
                standard="GB 90002-2026") for i in range(25)
    ])
    try:
        # ⚠ 必须带 `doc_id`（spec 003）：范围提问靠 `clause_vec.doc_id` 下推进 KNN；
        #   本用例判的正是"向量通道有没有被范围堵住"，夹具不带就等于没造出前提。
        doc_of = {"in_weak": "in_doc", "out_hot1": "out_doc", "out_hot2": "out_doc"}
        for cid, v in vecs.items():
            conn.execute("DELETE FROM clause_vec WHERE clause_revision_id=?", (cid,))
            conn.execute("INSERT INTO clause_vec(clause_revision_id, doc_id, embedding)"
                         " VALUES (?,?,?)", (cid, doc_of[cid], json.dumps(v)))
        for i in range(25):
            conn.execute("DELETE FROM clause_vec WHERE clause_revision_id=?", (f"out_bulk{i}",))
            conn.execute("INSERT INTO clause_vec(clause_revision_id, doc_id, embedding)"
                         " VALUES (?,?,?)",
                         (f"out_bulk{i}", "out_doc", json.dumps([1.0] + [0.0] * 511)))
        conn.commit()
        monkeypatch.setattr(emb, "is_available", lambda: True)
        monkeypatch.setattr(emb, "embed_query", lambda q: [1.0] + [0.0] * 511)
        rows = perform_hybrid_search("随便问点什么", top_k=5, channels=["vec"], rerank=False,
                                     doc_ids=IN_SCOPE)
        ids = _ids(rows)
        assert ids, ("向量通道在范围内**一条都没返回** ⇒ 范围约束写成了「先 KNN 再筛」"
                     "（范围外的近邻把 k=20 的名额吃光了）")
        assert not any(i.startswith("out_") for i in ids), f"向量通道没被范围堵住：{ids}"
    finally:
        # ⚠⚠ **2026-09-21（复核 HIGH-1 的根因之一）**：这 25 行以前**留在库里**，
        # 改变了 FTS5 的 BM25 统计量 ⇒ 把**后面**用例的全库排名"翻"了过来，
        # 于是那两条"取回后筛"的用例只有全量跑才红（顺序相关的偶然）。
        # 现在**跑完就清**：本用例只该证明"向量通道被堵住"，不许顺手改别人的语料。
        for i in range(25):
            for sql in ("DELETE FROM clause_vec WHERE clause_revision_id=?",
                        "DELETE FROM clause_fts WHERE clause_revision_id=?",
                        "DELETE FROM clause_revision WHERE clause_revision_id=?"):
                try:
                    conn.execute(sql, (f"out_bulk{i}",))
                except Exception:  # noqa: BLE001 - 表不存在就跳过（列名随 schema 变）
                    pass
        conn.commit()


def test_vec_scope_holds_with_more_than_one_document(scope_db, monkeypatch):
    """**范围里有 ≥2 篇文档**时，向量通道也必须整体下推（spec 003 · FR-003）。

    为什么要单独一条：上面那条的范围内**只有 1 篇**，所以
    `doc_id = (SELECT value FROM json_each(?))` 这种"标量子查询只取第一行"的写法**照样能过** ——
    而它正是本项要关掉的那类"看着像"的写法（实测：≥2 个 id 时行为不同，
    字面量列表 / `OR` 更会**返回范围外的行**，见 `specs/003-vec-scope-pushdown/research.md` R2）。

    本条把答案放在**第二篇**范围内文档里 ⇒ 只有"范围真的整体下推"才拿得到它。
    判据：两篇的向量条款**都要回来**，且不许混进 `out_`。
    """
    from src.core.retrieval import embedder as emb
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage.sqlite_db import get_db_connection, load_vec_extension
    conn = get_db_connection()
    load_vec_extension(conn)
    far = [0.0] * 511 + [1.0]
    near = [1.0] + [0.0] * 511
    clause_repo.insert_document(conn, dict(
        doc_id="in_doc2", standard_no="GB 90003-2026", standard_name="范围内第二份标准",
        short_code="GB90003", current_revision_id="r_in2",
        domain_tags=["测试"], file_path="in2.pdf", file_hash="h_in2"))
    clause_repo.insert_clauses([
        _clause("in2_weak", "1.0.1", "范围内第二篇的普通条款", "in_doc2",
                standard="GB 90003-2026"),
    ])
    try:
        for cid, doc in (("in_weak", "in_doc"), ("in2_weak", "in_doc2")):
            conn.execute("DELETE FROM clause_vec WHERE clause_revision_id=?", (cid,))
            conn.execute("INSERT INTO clause_vec(clause_revision_id, doc_id, embedding)"
                         " VALUES (?,?,?)", (cid, doc, json.dumps(far)))
        for i in range(25):   # 范围外、与查询向量完全一致的近邻（全局 top-k 全是它们）
            conn.execute("DELETE FROM clause_vec WHERE clause_revision_id=?", (f"out_bulk{i}",))
            conn.execute("INSERT INTO clause_vec(clause_revision_id, doc_id, embedding)"
                         " VALUES (?,?,?)", (f"out_bulk{i}", "out_doc", json.dumps(near)))
        conn.commit()
        monkeypatch.setattr(emb, "is_available", lambda: True)
        monkeypatch.setattr(emb, "embed_query", lambda q: near)
        rows = perform_hybrid_search("随便问点什么", top_k=5, channels=["vec"], rerank=False,
                                     doc_ids=["in_doc", "in_doc2"])
        ids = set(_ids(rows))
        assert not any(i.startswith("out_") for i in ids), f"向量通道没被范围堵住：{sorted(ids)}"
        assert {"in_weak", "in2_weak"} <= ids, (
            f"范围有 2 篇文档时只有整体下推才拿得到两篇的条款；实得 {sorted(ids)}"
            "（标量子查询/只取第一行的写法会漏掉第二篇）")
    finally:
        for i in range(25):
            for sql in ("DELETE FROM clause_vec WHERE clause_revision_id=?",
                        "DELETE FROM clause_fts WHERE clause_revision_id=?",
                        "DELETE FROM clause_revision WHERE clause_revision_id=?"):
                try:
                    conn.execute(sql, (f"out_bulk{i}",))
                except Exception:  # noqa: BLE001
                    pass
        for sql in ("DELETE FROM clause_vec WHERE clause_revision_id='in2_weak'",
                    "DELETE FROM clause_fts WHERE clause_revision_id='in2_weak'",
                    "DELETE FROM clause_revision WHERE clause_revision_id='in2_weak'",
                    "DELETE FROM doc_meta WHERE doc_id='in_doc2'"):
            try:
                conn.execute(sql)
            except Exception:  # noqa: BLE001
                pass
        conn.commit()


# ═════════════ 3. 空范围绝不退化成全库 ═════════════

def test_empty_scope_returns_nothing_never_the_whole_kb(scope_db):
    """`doc_ids=[]` = "范围内一篇都没有" ⇒ **一条都不返回**（绝不退化成全库）。"""
    from src.core.retrieval.hybrid_engine import perform_hybrid_search, search_with_details
    res = perform_hybrid_search("5.2.3", top_k=10, doc_ids=[])
    assert res == [], f"空范围竟然返回了 {_ids(res)}（= 退化成全库了）"
    out = search_with_details("5.2.3", top_k=10, doc_ids=[])
    assert out["results"] == [] and out["expanded"] == []
    assert out["debug"]["doc_scope"] == {"active": True, "doc_count": 0, "empty": True}


# ═════════════ 4. 答案层：范围回显 / 未知目录 / 两种"夹"不混 ═════════════

@pytest.fixture(scope="module")
def kb_folders(scope_db):
    """知识库目录：顶层「甲」挂着 in_doc，顶层「乙」挂着 out_doc（返回两个 id）。"""
    from src.core.knowledge import folder_store as fs
    a = fs.create_folder("甲", None)
    b = fs.create_folder("乙", None)
    fs.add_member(a["folder_id"], "file", "in_doc")
    fs.add_member(b["folder_id"], "file", "out_doc")
    return {"in": a["folder_id"], "out": b["folder_id"]}


def test_answer_scope_is_echoed_and_restricts_retrieval(scope_db, kb_folders, monkeypatch):
    """`ks_answer.answer(kb_folder_ids=[甲])`：检索被限定（范围外那篇的证据进不来）+ 范围如实回显。

    ⚠ 这条**不 mock 检索**（第 5 步踩过"自己验自己"的坑）：判的是**可观察的结果** ——
    范围外那份标准里堆了三处强命中，`top_k=2` 时若过滤发生在"取回之后"，
    候选名额会被它们占满 ⇒ 证据里**看不到范围内那条**。
    """
    from src.core.llm import ks_answer
    monkeypatch.setattr(ks_answer, "_stream_llm",
                        lambda messages: iter(["【推导区】\n推导\n【结论区】\n结论"]))
    data = ks_answer.answer("5.2.3 防火间距", params={
        "kb_folder_ids": [kb_folders["in"]], "top_k": 2, "channels": ["exact", "fts"]})
    assert data["scope"]["doc_count"] == 1 and data["scope"]["empty"] is False
    assert data["scope"]["folder_count"] == 1
    docs = {ev["doc_id"] for ev in data["evidence"]}
    assert docs == {"in_doc"}, f"范围外的条款混进了证据（或范围内那条没进来）：{docs}"
    assert any("知识库目录范围" in n for n in data["notes"]), data["notes"]
    assert data["_meta"]["kb_scope"]["doc_count"] == 1


def test_answer_still_answers_when_out_of_scope_hits_saturate_topk(scope_db, kb_folders, monkeypatch):
    """**"在取回后筛"必红的那一条**（`top_k` 被范围外命中吃光的情形）。

    场景：范围外那条同一条关键词堆了三遍（FTS 打分明显更高），`top_k=1`。
      · 在**检索层**过滤 ⇒ 候选里只有范围内那条 ⇒ 证据非空、是 `in_doc`；
      · 在**取回之后**筛 ⇒ 全库第 1 名是范围外那条 ⇒ 筛完**一篇证据都不剩** ⇒
        "范围内明明有却答不出"。
    ⚠ 为什么必须单开一条：`test_answer_scope_is_echoed_and_restricts_retrieval` 只断言
      "范围外的不许进来" —— 那条判据**取回后筛也满足**（筛掉就是了），抓不到这个症状。

    ⚠⚠ **2026-09-21（复核 HIGH-1 打回后）**：这条以前**依赖前序用例**（向量那条往 out_doc 塞了
    25 行、改了 BM25 统计）才偶然变红 —— 单独跑是绿的。现在：① fixture 让范围外那条**本来就**排第一；
    ② 先断言前提（不留范围时 `top_k=1` = `out_hot1`），前提不成立就红；③ 向量用例跑完**自己清理**
    那 25 行（不再污染后面的语料）。⇒ 单跑、全量跑、换顺序都必须红/绿一致。
    """
    from src.core.llm import ks_answer
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    # ① 前提（不许省）：`answer()` 走的就是这次检索；不留范围时第一名必须在范围外。
    q = "防火间距 不应小于13m"
    unrestricted = _ids(perform_hybrid_search(q, top_k=1, channels=["fts"], rerank=False))
    assert unrestricted == ["out_hot1"], (
        "**前提不成立**：不留范围时 FTS 第一名应当是范围外的 out_hot1，实测 "
        f"{unrestricted} ⇒ 这条用例抓不住「取回后再筛」，不许放过")
    monkeypatch.setattr(ks_answer, "_stream_llm",
                        lambda messages: iter(["【推导区】\n推导\n【结论区】\n结论"]))
    data = ks_answer.answer(q, params={
        "kb_folder_ids": [kb_folders["in"]], "top_k": 1, "channels": ["fts"]})
    docs = {ev["doc_id"] for ev in data["evidence"]}
    assert docs == {"in_doc"}, (
        "范围内那条**没被答出来**（top_k=1 被范围外的强命中吃掉了）—— "
        f"范围过滤很可能发生在取回之后：{sorted(docs)}")


def test_answer_rejects_unknown_folder_instead_of_falling_back(scope_db):
    """目录不存在 ⇒ **报错**（`KbScopeNotFound`），绝不静默当成"没给范围"全库检索。"""
    from src.core.llm import ks_answer
    with pytest.raises(ks_answer.KbScopeNotFound):
        ks_answer.answer("5.2.3", params={"kb_folder_ids": ["fld_does_not_exist"]})
    with pytest.raises(ValueError):
        ks_answer.answer("5.2.3", params={"kb_folder_ids": []})
    with pytest.raises(ValueError):
        ks_answer.answer("5.2.3", params={"kb_doc_ids": []})


def test_answer_with_empty_doc_scope_does_not_search(scope_db, monkeypatch):
    """空范围（目录存在但里面一篇没有）⇒ **不检索**、如实说"范围内没有"，且**不调 LLM 拿全库编答案**。"""
    from src.core.knowledge import folder_store as fs
    from src.core.llm import ks_answer
    empty = fs.create_folder("空目录", None)["folder_id"]
    called: list = []

    def _boom(*a, **kw):
        called.append(1)
        raise AssertionError("空范围不该发生检索")

    monkeypatch.setattr("src.core.retrieval.hybrid_engine.perform_hybrid_search", _boom)
    monkeypatch.setattr(ks_answer, "_stream_llm",
                        lambda messages: iter(["【推导区】\n推导\n【结论区】\n结论"]))
    data = ks_answer.answer("5.2.3", params={"kb_folder_ids": [empty]})
    assert called == [], "空范围竟然走了检索（= 可能退化成全库）"
    assert data["evidence"] == []
    assert data["scope"]["empty"] is True and data["scope"]["doc_count"] == 0
    assert any("没有做任何检索" in n for n in data["notes"]), data["notes"]


def test_bookmark_folder_and_kb_scope_are_two_different_things(scope_db, kb_folders, monkeypatch):
    """两种"夹"不混：`folder_id`（收藏夹）**不动检索**（只后置过滤证据），`kb_folder_ids` 才限定检索。

    同时给时证据是**交集**：知识库范围先限定检索，收藏夹再过滤证据。
    ⚠ 判据全部是**可观察结果**（不 spy 内部调用）：
      · 只给收藏夹（收藏的是**范围外**那篇的条款）⇒ 证据**非空且全在范围外**
        —— 若收藏夹把检索也限定了（或把它当成知识库范围），这里会是空；
      · 同时给"知识库范围=甲（in_doc）"+ 同一个收藏夹 ⇒ 证据**空**（交集），而 scope 回显 doc_count=1。
    """
    from src.core.llm import ks_answer
    from src.core.storage import user_data
    monkeypatch.setattr(ks_answer, "_stream_llm",
                        lambda messages: iter(["【推导区】\n推导\n【结论区】\n结论"]))
    folder = user_data.create_folder("范围测试收藏夹")
    user_data.add_bookmark("key_out_hot1", folder_id=folder["folder_id"])
    only_bm = ks_answer.answer("5.2.3 防火间距", params={
        "folder_id": folder["folder_id"], "channels": ["exact", "fts"]})
    bm_docs = {ev["doc_id"] for ev in only_bm["evidence"]}
    assert bm_docs == {"out_doc"}, (
        f"收藏夹那一路只该**后置过滤**证据（不该去动检索层）：{bm_docs}")
    assert only_bm["scope"] is None, "没给知识库范围时 scope 必须是 None（不是空对象）"
    both = ks_answer.answer("5.2.3 防火间距", params={
        "kb_folder_ids": [kb_folders["in"]], "folder_id": folder["folder_id"],
        "channels": ["exact", "fts"]})
    assert both["scope"]["doc_count"] == 1, both["scope"]
    assert both["evidence"] == [], (
        "两者同时给时应当是**交集**（知识库范围限定检索 + 收藏夹过滤证据）⇒ 这里应为空："
        f"{[ev['doc_id'] for ev in both['evidence']]}")


def test_api_returns_404_for_unknown_kb_folder(client, kb_folders):
    """端点级：`POST /api/v1/ks/answer` 带不存在的目录 ⇒ **404**（不是 200 + 空答案）。"""
    from _kb_folder_api_fixtures import api, error_code
    c, token = client
    st, code = error_code(api(c, token, "post", "/api/v1/ks/answer", json={
        "query": "5.2.3", "params": {"kb_folder_ids": ["fld_nope_scope"]}}))
    assert (st, code) == (404, "kb_scope_not_found"), (st, code)
    st2, code2 = error_code(api(c, token, "post", "/api/v1/ks/answer", json={
        "query": "5.2.3", "params": {"kb_folder_ids": []}}))
    assert (st2, code2) == (422, "bad_request"), (st2, code2)


def test_two_endpoints_agree_on_too_many_folders(client, kb_folders):
    """**同一条件两个端点必须给同一个状态码**（复核 LOW-3 打回）。

    `folder_scope` 对"超过 200 个根"抛的是 `invalid_scope`，而它**不是"没找到"**：
      · `/api/v1/kb/scope/resolve` 对它回 **422 `invalid_scope`**（既有行为，未改）；
      · `/api/v1/ks/answer` 以前把**所有** KnowledgeStationError 都包成 `KbScopeNotFound` ⇒ **404**
        （复核实测 201 个目录时一边 422、一边 404）。
    ⇒ 现在按错误码分流：只有 `folder_not_found` 才是 404，其余（含 invalid_scope）走 ValueError ⇒ 422。
    """
    from _kb_folder_api_fixtures import api, error_code
    c, token = client
    many = [f"fld_x{i}" for i in range(201)]
    st_resolve, code_resolve = error_code(api(c, token, "post", "/api/v1/kb/scope/resolve", json={
        "folder_ids": many}))
    st_answer, code_answer = error_code(api(c, token, "post", "/api/v1/ks/answer", json={
        "query": "5.2.3", "params": {"kb_folder_ids": many}}))
    assert (st_resolve, code_resolve) == (422, "invalid_scope"), (st_resolve, code_resolve)
    assert (st_answer, code_answer) == (422, "bad_request"), (
        "「目录太多」不是「没找到」⇒ 端点必须 422（与 /kb/scope/resolve 同一档），"
        f"实测 {(st_answer, code_answer)}")
    # 反向：不存在的目录仍然是 404（别把这一条修成"全都 422"）
    st_unknown, code_unknown = error_code(api(c, token, "post", "/api/v1/ks/answer", json={
        "query": "5.2.3", "params": {"kb_folder_ids": ["fld_nope_scope"]}}))
    assert (st_unknown, code_unknown) == (404, "kb_scope_not_found"), (st_unknown, code_unknown)
