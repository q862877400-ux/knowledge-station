"""六路混合检索 + RRF 融合（T04，依据主计划 v4.3 第 8.3 节）。"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from typing import Any, Dict, List, Optional, Sequence

from src.core.domain.models import ClauseRevisionModel, MODALITY_STRENGTH, SEARCH_CHANNELS
from src.core.retrieval import embedder
from src.core.storage.clause_repo import fetch_full_clause
from src.core.storage.sqlite_db import get_db_connection, load_vec_extension

logger = logging.getLogger(__name__)

RRF_K = 60
CHANNEL_WEIGHTS: Dict[str, float] = {
    "exact": 2.0, "fts": 1.0, "vec": 1.0,
    "modality": 0.8, "legal_element": 0.8, "behavior_scope": 1.2,
}

#: **每条通道最多取多少行**（2026-09-25，P0.4）。
#:
#: 为什么必须有：通道 A（精确条款号）/ D（模态）/ E（法理要素）原先**完全没有上限**，
#: 实测一句带"应"的话会把**全库 27%（140,555 条）**一次拉进内存，`clause_number='1'`
#: 会拉 **6,379 条**（B/F 本来就有 `LIMIT 20`，C 按 k 取）。
#:
#: 为什么是 500（而不是更小）：RRF 的名次权重是 `W/(RRF_K+rank+1)`。取 W 最大的一路（exact，2.0）：
#:   第 1 名 2.0/61 = 0.0328；**第 500 名 2.0/561 = 0.0036**（只有第 1 名的 11%）。
#: 六条路满配也顶不住这个量级，所以第 500 名之后的条目**进不了最终 top-k**；
#: 而 cap ≥ top_k 时，"某一条路单独命中"的返回结果**逐条不变**（取的就是它最前那几行）。
#: 500 相比 140,555 已经是 **280 倍**的内存削减，同时给"极端情况下靠后名次翻盘"留了很大余量。
CHANNEL_ROW_CAP = 500


# 2026-09-13 附录细分配套修复：附录字母章号前置——"E.5.2" 先被截出 "5.2" 返回
# **错标准**的正文条款（GB 30871 5.2 等，看起来对实则错——比查不到更危险）。
# 字母章号形态（A-Z 单字母 + 点分段）优先尝试；命不中再回落数字/法条旧正则。
# 边界（?!\\b——Python \\b 不认中文，"表E.4" 的 E 与中文之间无 \\b）：前侧
# 只需排除字母数字（防 "TABLE.4" 之类英文词内误截），后侧数字点结尾天然截断。
_CLAUSE_NO_RE = re.compile(r"(\d+\.[\d\.]+|第[一二三四五六七八九十百千]+条)")
_CLAUSE_NO_APPENDIX_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Z]\.\d+(?:\.\d+)*)(?![A-Za-z0-9])")
_MODALTITY_RE = re.compile("严禁|禁止|不得|不应|不能|应当|必须|宜|可以|有权|鼓励|提倡|支持")

#: 从**用户提问**里认出标准号（2026-09-24）。形态：字母前缀（可带 `/T` 之类分册）+ 号 + 连字符 + 年。
#: 例：`AQ 3028-2008`、`GB/T 10029-2010`、`GB 55037—2022`。
#:
#: ⚠ **刻意不列前缀族**：仓里已有两份前缀表（`text_utils._WM_STD_CORE` 与
#: `doc_catalog._STD_NO_PREFIX`）且两份并不一致，再加第三份正是要避免的事。
#: 这里只认**形态**，认出来之后再拿库里的 `standard_no` 去比（同一个 `standard_key` 口径）。
#: ⚠ 与 `_WM_STD_CORE` **不是一回事**：那个是页眉水印清洗判据，必须防"数字+大写字母"
#: 误吃条款标题（`5.2.3 试验方法`）；本处输入是**提问**，且要求"号-年"形态，不存在那个风险。
_STD_IN_QUERY_RE = re.compile(
    r"[A-Z]{1,6}(?:\s*/\s*[A-Z]{1,3})?\s*\d{1,5}(?:\.\d+)?\s*[\u2014\-\u2013]\s*\d{2,4}",
    re.I)


# 评测/门禁用：临时覆盖库路径（eval benchmark 对快照库跑，可复现、不依赖本机 %APPDATA%）
_DB_OVERRIDE: Any | None = None


def set_db_override(path: Any | None) -> None:
    """设置/清除检索库路径覆盖（None=恢复默认）。仅 eval/测试使用。"""
    global _DB_OVERRIDE
    _DB_OVERRIDE = path


def _conn():
    return get_db_connection(_DB_OVERRIDE)


def _fts_query(text: str) -> str:
    """构建 FTS5 MATCH 表达式：对每个分词加引号，避免点号/连字符等触发语法错误。

    实现已**迁到** `text_utils.fts_match_expr`（2026-09-17，与材料侧共用一份口径），
    本函数只做委托。**行为逐字不变**（迁移时用 12 个输入钉住过）——
    这么改的理由：材料侧一度自己写了一份**更差**的实现（裸词 + 隐式 AND），
    于是"同一句话在法条里搜得到、在材料里搜不到"。
    """
    from src.core.text_utils import fts_match_expr
    return fts_match_expr(text)


def perform_hybrid_search(
    query: str,
    top_k: int = 5,
    include_superseded: bool = False,
    channels: Optional[List[str]] = None,
    modality_filter: Optional[str] = None,
    subject_filter: Optional[str] = None,
    behavior_scope_filter: Optional[str] = None,
    boost_bookmarks: bool = True,
    rerank: bool = True,
    rerank_n: int = 24,
    rerank_k: Optional[int] = None,
    doc_ids: Optional[Sequence[str]] = None,
) -> List[ClauseRevisionModel]:
    """六路召回 + RRF(k=60) 融合 + 时效过滤。向量引擎离线时自动降级（R30）。

    `doc_ids`（2026-09-21 第 6 步：**按目录范围提问**）—— **在检索层**把候选限定在这批文档里：
      * `None`（缺省）= 不限定（历史行为，逐字不变）；
      * **空序列 `[]` = "范围里一篇都没有"** ⇒ 直接返回 `[]`，**绝不退化成全库**
        （空范围若被当成"没给范围"，"范围内提问"就会悄悄变成全库提问 —— 那是最坏的一种谎）；
      * 非空 ⇒ **六条召回通道每一条**都在 SQL 里带上范围约束（不是取回 top_k 之后再筛：
        那样 top_k 会被范围外的命中吃掉，出现"范围内明明有却答不出"）。
      ⚠ 范围用 `json_each(?)` 一次传进 SQL（本机 SQLite 3.53.1 带 JSON1；避免 IN 列表的变量数上限）。
      ⚠ 向量通道（通道 C）的实测口径（`var/tmp/probe-vec-scope.py`，sqlite-vec v0.1.9 /
        SQLite 3.53.1）—— **两句分开写**（2026-09-21 复核 INFO-2 指出上一版把两种形态混成一句
        "先 KNN 再筛"，会让人推出错误的容量结论）：
          ① **子查询**形式 `clause_revision_id IN (SELECT … json_each(?))` 是**带约束的 KNN**
             （全局最近的两条都在范围外时，它仍返回范围内最近的那条）；
          ② **双元素字面量列表** `IN ('a','b')` 比"先 KNN 再筛"**更糟**：它**连全局 top-k 里
             本来有的那条也返回 0 行**（复核在"只有一行"的表上也是 0 行）；
             真正"先 KNN 再筛"的是**单字面量/等值**（`clause_revision_id = ?`）。
        ⇒ 结论不变（**只许用子查询形式**），但别再照"先 KNN 再筛"推理容量。
    """
    conn = _conn()
    if channels is None:
        channels = list(SEARCH_CHANNELS)
    scores: Dict[str, float] = {}
    degraded = {"vector_engine": "offline"}

    # ── 文档范围（第 6 步）：空范围 ⇒ 不检索（**不许**退化成全库） ─────────────────
    scope_active = doc_ids is not None
    scope_json = ""
    if scope_active:
        wanted = sorted({str(d) for d in (doc_ids or ()) if str(d).strip() != ""})
        if not wanted:
            logger.info("范围提问：范围为空（0 篇）⇒ 不做任何检索，直接返回空")
            return []
        scope_json = json.dumps(wanted, ensure_ascii=False)
        logger.info("范围提问：候选限定在 %d 篇文档内（检索层过滤，六通道）", len(wanted))

    def _scope_doc(param: str = "cr.doc_id") -> str:
        """范围 SQL 片段（**只在真的限定范围时**拼进查询）。"""
        return f" AND {param} IN (SELECT value FROM json_each(?))"

    def _scope_clause(param: str = "clause_revision_id") -> str:
        """FTS/向量表没有 doc_id 列 ⇒ 回 `clause_revision.doc_id` 判（同为检索层过滤）。"""
        return (f" AND {param} IN (SELECT clause_revision_id FROM clause_revision"
                f" WHERE doc_id IN (SELECT value FROM json_each(?)))")

    # 通道 A: 条款号/法条号精确匹配
    if "exact" in channels:
        # 2026-09-13：附录字母章号（E.5.2）优先——先用字母形态取整号；命不中
        # 再走旧数字/法条正则。取到字母号后不再让数字正则截短号（防双路错配）。
        m_ann = _CLAUSE_NO_APPENDIX_RE.search(query)
        m = _CLAUSE_NO_RE.search(query)
        exact_no = None
        if m_ann:
            exact_no = m_ann.group(1)
        elif m:
            exact_no = m.group(1)
        if exact_no:
            # 2026-09-24：**提问里认得出标准号时，把本通道限定到那本标准。**
            # 为什么必须做：实测库里 `clause_number='5.2'` 有 **4,910 条**，只有 1 条属 GB 30871-2022。
            # 不限定的话，用户问「查 AQ 3028-2008 第 3.1 条」会把**全库所有叫 3.1 的条款**
            # 一起拉出来（本通道权重 2.0，六路最高）⇒ 正确的那条被别家的 3.1 挤掉。
            # 实测代价：金标 90 条检索题里，**47 条**是靠"匹配到别的标准的同名条款"被判成命中的。
            # 认不出标准号时（`want_keys` 为空）**行为一字不改** —— 历史语义完整保留。
            from src.core.text_utils import standard_key
            want_keys = {standard_key(s) for s in _STD_IN_QUERY_RE.findall(query)}
            rows = conn.execute(
                "SELECT cr.clause_revision_id, dm.standard_no FROM clause_revision cr"
                " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
                " WHERE cr.clause_number = ?"
                + ("" if include_superseded
                   # ⚠ **NULL 必须放进来**（2026-09-17 独立复核 b8 的 LOW）：
                   # `NOT IN (…)` 对 NULL 求值是 NULL（不是 true）⇒ 未核验的条款
                   # （采集件，`legal_status IS NULL`）会被**静默排除**在精确命中与
                   # 模态召回之外——而"未核验"**不是**"已废止"，不该这样筛掉。
                   # `fetch_full_clause` 那层已按 §10.44 如实带出 NULL，这里是
                   # **另一条 SQL 通道**，两处判据要一致。
                   else " AND (dm.legal_status IS NULL OR dm.legal_status"
                        " NOT IN ('withdrawn','superseded'))")
                + (_scope_doc() if scope_active else "")
                # ⚠ 排序必须**显式把"未核验"放最后**（2026-09-18 复核 b9 的 LOW-3）：
                # SQLite 的 `ORDER BY x` 把 **NULL 排在最前**，而 `rank` 直接决定
                # `CHANNEL_WEIGHTS / (RRF_K + rank + 1)` ⇒ 上面那两处刚把 NULL **放进来**，
                # 它们就会**排第一**、拿到通道内最好的名次——方向与 §10.44 建立的
                # "未核验不得承重"**相反**。`(dm.legal_status IS NULL)` 对 NULL 求值为 1、
                # 其余为 0 ⇒ 未核验沉到最后，已知状态的按名排（effective 在前）。
                # ⚠ **口径取舍补记**（2026-09-18 复核 b12 的 LOW-4）："已知状态按名排"= **字符串序**
                # `effective < superseded < withdrawn < NULL` ⇒ **已废止/已替代排在"未核验"之前**。
                # 这不是某一步引入的（§10.58 之前 A 就是这样），D/E 只是**对齐**它；
                # 也不与"未核验不得承重"冲突——那是"谁排前面"，这是"能不能承重"（承重判据在
                # `authority`/`evidence` 那一侧，不在排序里）。若要"已废止也沉到未核验之后"，
                # 那是**新口径**，需业主拍板（不是"顺手改一下"）。
                # ⚠ 另一处不对称：**A 这条原先没有 id 兜底** ⇒ 同状态多行时次序不保证（非全序）。
                # **2026-09-25（P0.4）补上 `cr.clause_revision_id` 兜底**——这是加 `LIMIT` 的**前提**：
                # 非全序 + LIMIT 会让"取到哪 500 条"变成**不确定的**（比不加上限更糟，
                # 因为不加上限时至少"集合"是确定的）。补齐后 A 与 D/E 口径一致（全序）。
                + " ORDER BY (dm.legal_status IS NULL), dm.legal_status, cr.clause_revision_id"
                # 上限：见 CHANNEL_ROW_CAP 的注释（为什么是 500）
                + f" LIMIT {CHANNEL_ROW_CAP}",
                ((exact_no, scope_json) if scope_active else (exact_no,))).fetchall()
            if want_keys:
                rows = [r for r in rows if standard_key(r[1] or "") in want_keys]
            for rank, row in enumerate(rows):
                scores[row[0]] = scores.get(row[0], 0.0) + CHANNEL_WEIGHTS["exact"] / (RRF_K + rank + 1)

    # 通道 B: FTS5 全文检索
    if "fts" in channels:
        fq = _fts_query(query)
        if fq:
            try:
                rows = conn.execute(
                    "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ?"
                    + (_scope_clause() if scope_active else "")
                    + " ORDER BY rank LIMIT 20",
                    ((fq, scope_json) if scope_active else (fq,))).fetchall()
                for rank, row in enumerate(rows):
                    scores[row[0]] = scores.get(row[0], 0.0) + CHANNEL_WEIGHTS["fts"] / (RRF_K + rank + 1)
            except sqlite3.OperationalError as e:
                logger.warning("FTS 查询失败: %s", e)

    # 通道 C: sqlite-vec 向量检索
    if "vec" in channels and embedder.is_available():
        try:
            load_vec_extension(conn)
            q_emb = embedder.embed_query(query)
            rows = conn.execute(
                "SELECT clause_revision_id, distance FROM clause_vec"
                " WHERE embedding MATCH ? AND k = 20"
                + (_scope_clause("clause_revision_id") if scope_active else "")
                + " ORDER BY distance",
                ((json.dumps(q_emb), scope_json) if scope_active
                 else (json.dumps(q_emb),))).fetchall()
            for rank, row in enumerate(rows):
                scores[row[0]] = scores.get(row[0], 0.0) + CHANNEL_WEIGHTS["vec"] / (RRF_K + rank + 1)
            degraded["vector_engine"] = "ok"
        except Exception as e:  # noqa: BLE001
            logger.warning("向量检索降级: %s", e)

    # 通道 D: 模态召回
    if "modality" in channels and modality_filter:
        rows = conn.execute(
            "SELECT cr.clause_revision_id FROM clause_revision cr"
            " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
            " WHERE cr.modality = ?"
            + ("" if include_superseded
               # 同上（通道 A 那条注释）：NULL 是"未核验"，不是"已废止"。
               else " AND (dm.legal_status IS NULL OR dm.legal_status"
                    " NOT IN ('withdrawn','superseded'))")
            + (_scope_doc() if scope_active else "")
            # ⚠ 这一条**原先完全没有 ORDER BY**（复核 b9 的 LOW-3 顺带指出、本步修，
            # 方案未决第 12 条的 INFO-6）：`rank` 直接决定
            # `CHANNEL_WEIGHTS / (RRF_K + rank + 1)`，而**没有 ORDER BY 的 SELECT 返回次序
            # 是未定义的**（实际由访问路径/rowid 决定，改规划器、加索引、VACUUM 都可能变）
            # ⇒ 同一个查询的权重分配**不可复现**，而且**无法断言**。
            # 排序口径与通道 A 一致：未核验（NULL）沉底，已知状态按名排，最后用 id 兜底
            # 保证**全序**（同状态多行时也确定）。取舍（已废止排在未核验之前）与 A 相同，
            # 见通道 A 那条注释——**口径的唯一所有者在 A**，这里只负责"更全"（多了 id 兜底）。
            + " ORDER BY (dm.legal_status IS NULL), dm.legal_status, cr.clause_revision_id"
            # 上限：见 CHANNEL_ROW_CAP（原先这条**完全没有上限**，模态='应' 一次拉 14 万条）
            + f" LIMIT {CHANNEL_ROW_CAP}",
            ((modality_filter, scope_json) if scope_active else (modality_filter,))).fetchall()
        for rank, row in enumerate(rows):
            scores[row[0]] = scores.get(row[0], 0.0) + CHANNEL_WEIGHTS["modality"] / (RRF_K + rank + 1)

    # 通道 E: 法理要素召回 (义务主体)
    if "legal_element" in channels and subject_filter:
        rows = conn.execute(
            "SELECT cr.clause_revision_id FROM clause_revision cr"
            # ⚠ **LEFT JOIN，不是 JOIN**（2026-09-18 补齐通道 E 的状态偏好）：
            # `LEFT` 保证"`doc_meta` 缺行"**不会把条款静默丢掉**——本项目已经栽过两次
            # "未核验被静默排除"（§10.44/§10.49），那次是 `NOT IN` 对 NULL 求值，
            # 这次若用内连接，缺行会在**更前面**被丢掉，症状一模一样（少了行、没人报错）。
            # 缺行时 `dm.legal_status` 为 NULL ⇒ 正好落进"未核验"那一档（沉底），语义也对。
            " LEFT JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
            " WHERE cr.subject = ? AND cr.knowledge_type = 'legal'"
            + (_scope_doc() if scope_active else "")
            # ⚠ 这条原先**没有 ORDER BY**（复核 b9 的 LOW-3 顺带指出、§10.58 先补了"确定性"）：
            # `rank` 直接决定 `CHANNEL_WEIGHTS / (RRF_K + rank + 1)`，没有 ORDER BY 的返回次序
            # 是未定义的 ⇒ 同一查询的权重分配不可复现。
            # 本步把**口径与通道 A/D 对齐**：未核验（NULL）沉底、已知状态按名排、id 兜底成全序。
            # 取舍（已废止排在未核验之前）见通道 A 注释（唯一所有者）；本处与 A 的差别是
            # **多了 id 兜底** ⇒ 这条是**全序**，A 不是（复核 b12 的 INFO）。
            + " ORDER BY (dm.legal_status IS NULL), dm.legal_status, cr.clause_revision_id"
            # 上限：见 CHANNEL_ROW_CAP（这条原先也没有上限）
            + f" LIMIT {CHANNEL_ROW_CAP}",
            ((subject_filter, scope_json) if scope_active else (subject_filter,))).fetchall()
        for rank, row in enumerate(rows):
            scores[row[0]] = scores.get(row[0], 0.0) + CHANNEL_WEIGHTS["legal_element"] / (RRF_K + rank + 1)

    # 通道 F: 行为客体召回 (合规审查专用)
    if "behavior_scope" in channels and behavior_scope_filter:
        fq = _fts_query(behavior_scope_filter)
        if fq:
            try:
                rows = conn.execute(
                    "SELECT clause_revision_id FROM clause_fts"
                    " WHERE behavior_scope_segmented MATCH ?"
                    + (_scope_clause() if scope_active else "")
                    + " ORDER BY rank LIMIT 20",
                    ((fq, scope_json) if scope_active else (fq,))).fetchall()
                for rank, row in enumerate(rows):
                    scores[row[0]] = scores.get(row[0], 0.0) + CHANNEL_WEIGHTS["behavior_scope"] / (RRF_K + rank + 1)
            except sqlite3.OperationalError as e:
                logger.warning("行为客体 FTS 查询失败: %s", e)

    # R25: 已收藏条款获得轻量排名加分 (+0.15)
    if boost_bookmarks and scores:
        try:
            from src.core.storage.user_data import bookmarked_clause_keys
            bm_keys = bookmarked_clause_keys()
        except Exception:
            bm_keys = set()
        if bm_keys:
            ids = list(scores.keys())
            for i in range(0, len(ids), 900):  # SQLite 变量上限分块（旧版 999）
                chunk = ids[i:i + 900]
                ph = ",".join("?" * len(chunk))
                for cid, key in conn.execute(
                        f"SELECT clause_revision_id, clause_key FROM clause_revision"
                        f" WHERE clause_revision_id IN ({ph})", chunk).fetchall():
                    if key in bm_keys:
                        scores[cid] = scores.get(cid, 0.0) + 0.15

    # RRF 排序与时效过滤（rerank 开启时先取 rerank_n 候选，再裁到 top_k）
    cap = rerank_n if (rerank and rerank_n > top_k) else top_k
    sorted_cids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    results: List[ClauseRevisionModel] = []
    for cid in sorted_cids:
        if len(results) >= cap:
            break
        clause = fetch_full_clause(conn, cid)
        if clause is None:
            continue
        if not include_superseded and clause.legal_status in ("superseded", "withdrawn"):
            continue
        results.append(clause)
    if rerank and rerank_n > top_k:
        results, rerank_debug = _rerank_results(query, results, rerank_k or top_k)
        _last_rerank_debug.update(rerank_debug)
    return results


# 最近一次 rerank 的调试信息（search_with_details 合并进 R31 debug）
_last_rerank_debug: dict[str, Any] = {}


def _protect_exception_clauses(kept: List[ClauseRevisionModel],
                               results: List[ClauseRevisionModel],
                               top_k: int) -> List[ClauseRevisionModel]:
    """例外条款保护（P1）：含但书/除外的条款被 rerank 挤出时强制保留。

    例外信息（但书/除外/另有规定）不可被 rerank 淘汰——漏例外=误导用户。
    """
    kept_ids = {c.clause_revision_id for c in kept}
    for r in results:
        if len(kept) >= top_k + 2:
            break
        if (r.exception or "") and r.clause_revision_id not in kept_ids:
            kept.append(r)
            kept_ids.add(r.clause_revision_id)
    return kept[:top_k]


def _rerank_results(query: str, results: List[ClauseRevisionModel],
                    top_k: int) -> tuple[List[ClauseRevisionModel], dict]:
    """Task 10.2 rerank 标准阶段：RRF 融合后 top-N → reranker → top-K。

    例外条款保护：含"但书/除外/另有规定"的条款若在候选中，强制保留进 top-K
    （例外信息不可被 reranker 挤掉，P1 准确性）。
    返回 (重排结果, 调试信息)。模型不可用/异常 → 原序 + rerank_offline=true。
    """
    debug: dict[str, Any] = {"rerank_offline": False, "rerank_score": {}}
    if len(results) <= 1:
        return results, debug
    try:
        from src.core.retrieval import reranker
        if not reranker.is_available():
            debug["rerank_offline"] = True
            debug["rerank_reason"] = reranker.offline_reason()
            return results[:top_k], debug
        texts = [(r.content_text or "")[:512] for r in results]
        scores = reranker.rerank(query, texts)  # 已按得分降序
        ordered = sorted(range(len(results)), key=lambda i: scores[i], reverse=True)
        debug["rerank_score"] = {results[i].clause_revision_id: round(scores[i], 4)
                                 for i in ordered}
        kept: List[ClauseRevisionModel] = [results[i] for i in ordered[:top_k]]
        # 例外条款保护：任何含但书的候选强制保留（若已被挤出）
        return _protect_exception_clauses(kept, results, top_k), debug
    except Exception as e:  # noqa: BLE001
        debug["rerank_offline"] = True
        debug["rerank_reason"] = str(e)
        return results[:top_k], debug


def extract_modality_from_query(query: str) -> Optional[str]:
    """从用户查询中提取模态词，用于通道 D 过滤。

    陷阱: "应该""可能会"等口语复合词会误命中单字模态词(应/可)，
    命中后检查相邻字符排除常见复合词。
    """
    _compound_next = {"应": "该", "可": "能", "宜": "于"}
    for word in sorted(MODALITY_STRENGTH.keys(), key=len, reverse=True):
        idx = query.find(word)
        while idx != -1:
            nxt = query[idx + len(word):idx + len(word) + 1]
            if word in _compound_next and nxt == _compound_next[word]:
                idx = query.find(word, idx + 1)
                continue
            return word
    return None


# R9 条件追问：指代词/过短问题判定（追问增强用）
_FOLLOWUP_MARKERS = ("那", "这", "它", "其", "上述", "该条款", "该条", "上面", "之前", "刚刚", "你")


def expand_query_with_history(query: str, history: list[dict] | None) -> str:
    """R9 条件追问检索增强：当前问过短、含指代词，或是在补充上一轮提问的回答时
    （以"是/对/在/属于/设备/车间/有"等开头），把原始问题并入检索词，避免脱靶。

    纯规则实现（零 LLM 消耗）：first_user + ' ' + current。
    """
    if not history:
        return query
    q = query.strip()
    short = len(q) < 4
    has_marker = any(m in query for m in _FOLLOWUP_MARKERS)
    starts_with_answer = q.startswith(("是", "对", "好", "在", "属于", "位于", "有",
                                       "不知道", "不清楚", "设备", "车间", "厂房",
                                       "生产", "装置区", "密度", "大概", "差不多",
                                       "就", "应该", "可能"))
    if not (short or has_marker or starts_with_answer):
        return query
    first_user = ""
    for turn in history:
        if turn.get("role") == "user":
            first_user = (turn.get("content") or "").strip()
            break
    if not first_user:
        return query
    if first_user == q:
        return q
    return f"{first_user} {q}"


def expand_evidence_chain(conn: sqlite3.Connection,
                          seed_ids: list[str],
                          max_hops: int = 1,
                          limit: int = 3) -> list[dict]:
    """R5a 证据链扩展：沿 evidence_edge 扩 1~2 跳，防例外/但书/引用遗漏。

    返回 [{clause(模型), expanded_from, edge_type}]，仅沿 active 边。
    """
    expanded: list[dict] = []
    seen = set(seed_ids)
    frontier = list(seed_ids)
    for _hop in range(max_hops):
        if not frontier or len(expanded) >= limit:
            break
        placeholders = ",".join("?" * len(frontier))
        rows = conn.execute(
            f"SELECT edge_type, source_clause_id, target_clause_id FROM evidence_edge"
            f" WHERE status='active' AND source_clause_id IN ({placeholders})",
            frontier).fetchall()
        next_frontier = []
        for r in rows:
            for cid in (r["target_clause_id"],):
                if cid in seen:
                    continue
                seen.add(cid)
                clause = fetch_full_clause(conn, cid)
                if clause is None:
                    continue
                expanded.append({"clause": clause,
                                 "expanded_from": r["source_clause_id"],
                                 "edge_type": r["edge_type"]})
                next_frontier.append(cid)
                if len(expanded) >= limit:
                    break
        frontier = next_frontier
    return expanded


def search_with_details(query: str, **kwargs: Any) -> Dict[str, Any]:
    """R31 检索可解释性：返回结果 + 调试元数据。"""
    modality_filter = kwargs.pop("modality_filter", None)
    if modality_filter is None:
        modality_filter = extract_modality_from_query(query)
    expand_chain = kwargs.pop("expand_chain", True)
    # ⚠ 第 6 步（范围提问）：**证据链扩展也必须留在范围内** —— 扩展是沿着 evidence_edge
    #   从命中条款往外走一跳，目标条款**可能落在范围外**；不筛的话，"范围内提问"的答案里
    #   会混进范围外的条款（`ks_answer` 会把 expanded 合进证据列表）。这里按 doc_id 再筛一道。
    scope_kw = kwargs.get("doc_ids")
    allowed_docs = None if scope_kw is None else {str(d) for d in scope_kw}
    results = perform_hybrid_search(query, modality_filter=modality_filter, **kwargs)
    expanded: list[dict] = []
    if expand_chain and results:
        expanded = expand_evidence_chain(
            conn := _conn(),
            [r.clause_revision_id for r in results], max_hops=1)
        if allowed_docs is not None:
            expanded = [e for e in expanded
                        if str(getattr(e["clause"], "doc_id", "") or "") in allowed_docs]
    return {
        "results": results,
        "expanded": expanded,
        "debug": {
            "modality_filter": modality_filter,
            # 范围提问的可审计元数据（第 6 步）：**这一次到底限定在哪批文档里**。
            "doc_scope": (None if scope_kw is None else {
                "active": True, "doc_count": len(allowed_docs or ()),
                "empty": len(allowed_docs or ()) == 0,
            }),
            # ⚠ **同名不同义**（复核 b13 的 INFO-2）：这里的 `vector_engine` 是**三态**
            # （`ok`/`offline`/`unknown`，`embedder.health()` 的结论）；而同一个 dict 之外的
            # `degraded["vector_engine"]`（本函数上面）是**二态** `ok`/`offline`，且含义不同
            # ——那是"**这次检索真的用过向量通道**"的结论（用过才知道）。两者**都不加载模型**，
            # 但"没试过"在 `degraded` 里不会出现。改名要动消费方（`ks_answer` 读 `debug`），
            # 所以先在这里写明差异，别当成同一个东西用。
            "vector_engine": embedder.health(),
            "channels": kwargs.get("channels") or list(SEARCH_CHANNELS),
            "result_count": len(results),
            "expanded_count": len(expanded),
            "rerank": dict(_last_rerank_debug),
        },
    }
