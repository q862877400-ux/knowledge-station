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

#: ⚠ **不设行数上限——这是算过之后刻意不做的**（2026-09-25，第二轮独立复核 P0 打回）。
#:
#: 起因：通道 A（精确条款号）/ D（模态）/ E（法理要素）原先没有上限，实测模态 `'应'` 一次拉
#: **140,555 条**（全库 26.9%）、`clause_number='1'` 拉 **6,379 条** ⇒ 想做 `LIMIT 500` 收口。
#:
#: **为什么不能简单加 `LIMIT`**：加闸的论证是"RRF 名次权重 `W/(60+rank+1)`，第 500 名只有
#: 第 1 名的 11%，翻不了盘"——**那个论证预设了"名次 = 相关性名次"，而它不是**。
#: 通道 A/D/E 的 `ORDER BY` 头两个键是 `(dm.legal_status IS NULL), dm.legal_status`，
#: 而真库里它们**几乎不分档**（clause 级实测 effective **521,984** / withdrawn 21 /
#: reference 16 / superseded **0** / NULL **0**）⇒ **通道 A 的候选行（= 去掉 withdrawn/superseded
#: 之后的 522,000 行，见下）里 99.997% 落在同一档**
#: ⇒ **通道内名次实质上等于灌库顺序（`clause_revision_id` 序），与相关性无关**。
#: ⚠ **分母要写明**（第四轮复核 INFO）：522,000 = 521,984 + 16（`include_superseded=False`
#: 排掉 withdrawn/superseded 后的候选行）；**全库是 522,021 行**。拿 522,021 当分母只会算出
#: 99.993%，看着像矛盾。`99.997% = 521,984 / 522,000`。
#: ⚠ **措辞更正（第三轮复核的"低"）**：初版这里写"**恒为常数**"并只列了
#: effective/withdrawn/superseded/NULL —— 那**不准确**：`reference` 有 16 条，
#: 第二个键并非严格常数，且列数漏了 reference。**结论不受影响**（同档比例仍是 99.997%），
#: 但这是论证的地基，措辞必须准。
#: 于是 `LIMIT` 会**任意**丢掉候选，而不是丢掉"最不相关的"。
#:
#: **复核实测的代价**（真库 + 默认六通道 + 普通提问）：
#:   * **6/6** 提问里，用户**点名的那条条款**被挤出前 10（在基准树上是第 0 名）；
#:   * 通道 A 候选 522,000 行里，名次 >500 被砍掉 **177,829 行 = 34.1%**；
#:   * **384 / 6,793 篇文档的全部条款都被砍光**（通道 A 对它们完全失效）。
#:   * 而`金标四项一字未动`是**空证据**：快照库只有 19 篇、最大条款分组 **13** 条，
#:     闸在快照上**结构上不可能生效**，所以它证明不了闸安全。
#:
#: ⇒ **结论：在把通道 A/D/E 的排序改成"与相关性有关"之前，不许给它们加行数上限。**
#: 内存问题（14 万行）**仍然存在**，已登记为独立缺陷（长周期计划 P0），不在这里偷偷解决。
#: 谁要重新加闸，先回答：**这条通道的名次凭什么算相关性名次？**


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
#: ⚠ **2026-09-25 复核打回后的两处收紧**（原版会把不是标准号的记号当标准号，把通道清空）：
#:   ① 数字位下限 **1 → 3**（`\d{3,5}`）：原版把 `A1-2020`、`GB 5-2022` 也认成标准号；
#:   ② 抽出候选后**必须先在 `doc_meta` 里验证它真的存在**（见通道 A 里的 `want_keys`）——
#:      这条是关键：`FY2021-2022`、`ABC123-4567`、`T/CCSAS 001-2022` 这类就算形态像，
#:      只要库里没有对应文档，就**不筛**（退回历史行为），而不是把权重最高的通道整条清空。
_STD_IN_QUERY_RE = re.compile(
    r"[A-Z]{1,6}(?:\s*/\s*[A-Z]{1,3})?\s*\d{3,5}(?:\.\d+)?\s*[\u2014\-\u2013]\s*\d{2,4}",
    re.I)


def _std_key_hits_doc(key: str, doc_standard_no: str | None) -> bool:
    """提问里的标准号键 `key` 是否命中这部文档的 `standard_no`。

    ⚠ 判据是**词边界包含**（`(?<!\\d)…(?!\\d)`），**不是裸包含**。两个反例各自定住了它：

    * 裸「相等」不够 —— 真库有 **4 篇** `standard_no` 尾部带中文
      （`GB 5009.12-2023食品安全国家标准`、`GB/T 27668-2023显微镜光学显微术术语(1)`…），
      `standard_key` 对这种串会退化成整串 ⇒ 与提问算出的键不等
      ⇒ **权重最高（2.0）的通道 A 对这 4 篇整条失效**（复核实测 base 通道 A n=0 / 修后 n≥1）。
      所以必须允许"键是标准号的**前缀部分**"。
    * 裸「包含」**过头** —— `standard_key("GB/T 2033-2008")` = `2033-2008`，而
      `canon_standard_no("GB/T 12033-2008")` = `GBT12033-2008` **包含** `2033-2008`
      ⇒ 提问点名 `GB/T 2033-2008`，第 1 名返回 **`GB/T 12033-2008`**（第二轮复核实测端到端复现）。
      加数字左边界后 `…12033-2008` 里的 `2033` 前面是数字 ⇒ 不命中。

    真库实测的 5 组后缀碰撞：`7718-2011`↔`GB/T 27718-2011`、`144-2024`↔`GB/T 30144-2024`、
    `151-2014`↔`GB/T 31151-2014`、`2033-2008`↔`GB/T 12033-2008`、`247-2008`↔`GB/T 10247-2008`。
    """
    if not key:
        return False
    from src.core.text_utils import canon_standard_no
    return re.search(rf"(?<!\d){re.escape(key)}(?!\d)",
                     canon_standard_no(doc_standard_no)) is not None


def _rows_matching_standard_keys(rows, want_keys) -> list:
    """把候选行按「提问点名的标准」过滤（判据是 `_std_key_hits_doc` 的词边界包含）。

    为什么单独抽成函数（2026-09-25，第四轮复核的"残余 1"）：复核实测——
    把**调用点**的判据换成**裸包含**时，**全部测试仍然全绿**。原因是
    **快照库里一对后缀碰撞都没有**（真库有 5 对），所以那把尺子**结构上看不见**这个变异。
    抽成纯函数后，可以用真库那 5 对在单测里直接钉死（见 `tests/test_golden_criterion.py`）。

    `want_keys` 为空 ⇒ **原样返回**（认不出标准号 ⇒ 历史行为一字不改）。
    """
    if not want_keys:
        return list(rows)
    return [r for r in rows if any(_std_key_hits_doc(k, r[1]) for k in want_keys)]


def _known_standard_keys(want_keys, doc_standard_nos) -> set[str]:
    """从提问里抽出的候选键中，**挑出库里真的有对应文档的那些**。

    为什么必须有这道闸（第二轮复核 P0）：形态像标准号、库里却没有对应文档的记号
    （`FY2021-2022` / `ABC123-4567` / `T/CCSAS 001-2022`…）若照筛，会把**权重最高（2.0）的
    通道 A 整条清空**并把首位结果换掉——复核实测 22 条提问里 6 条如此。
    库里没有 ⇒ 不筛（退回历史行为）。耗时实测约 **16 ms/次**（真库 6,797 行）。
    """
    return {k for k in want_keys if any(_std_key_hits_doc(k, s) for s in doc_standard_nos)}



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


def _catalog_visible_fragment(conn: sqlite3.Connection, param: str = "dm.doc_id") -> str:
    """`catalog_hidden` 可见性片段（spec 013）——**唯一所有者**。

    ## 为什么检索路径也要它（2026-10-14 实测缺陷）

    `catalog_hidden=1` 以前**只在浏览类接口**被过滤
    （`/api/v1/documents*`、`/documents/categories`、`report/effect`），
    检索路径**完全不认它**（`git grep catalog_hidden -- src/core/retrieval/` 当时为空）。

    ⇒ 实测后果：拿真问题「个人信息处理者处理个人信息应当取得同意吗」跑真实检索
    （`top_k=20`），那篇**测试假样本** `个人信息保护法(测试)` 的条款排在
    **第 3 名与第 16 名** —— 而库里有**真的**《个人信息保护法》（74 条）
    ⇒ 它不只是噪声，是**用一个拼接的假法条去竞争真法条的位置**。

    ## 为什么这样写

    * **只对 `doc_meta` 有效**：片段引用 `dm.doc_id`，因此只能拼进
      **JOIN 了 `doc_meta`** 的通道（A/D/E）。通道 B/C/F 走 `_catalog_visible_by_clause()`。
    * **列可能不存在**（`catalog_hidden` 是 `clause_repo.ensure_catalog_hidden_column()`
      加的**增量列**，**不在 `schema.sql`**）⇒ 列不在时**返回空串**（不加条件），
      而不是拼一个会 `no such column` 报错的片段。这与
      `folder_store` / `apply-folder-filing` 的"读取时自适应"同口径。
    * **列在 ⇒ 一律过滤**，不提供"不过滤"的开关：`catalog_hidden=1` 的语义就是
      "不该被用户看见"，浏览与检索**必须一致**（两套可见性迟早漂移）。
    """
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(doc_meta)")}
    except sqlite3.Error:
        return ""
    if "catalog_hidden" not in cols:
        return ""
    return f" AND COALESCE({param} NOT IN (SELECT doc_id FROM doc_meta WHERE catalog_hidden = 1), 1)"


def _catalog_visible_by_clause(conn: sqlite3.Connection, param: str = "clause_revision_id") -> str:
    """同上，但给**没 JOIN `doc_meta`** 的通道用（B/C/F 走 `clause_revision` 中转）。

    ⚠ 与 `_catalog_visible_fragment` **同一个判据**（`catalog_hidden = 1` 排除），
    只是写法不同（多一跳 `clause_revision`）—— 两处**必须同时改**，
    `tests/test_catalog_hidden_retrieval.py` 有一条结构判据钉住这一点。
    """
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(doc_meta)")}
    except sqlite3.Error:
        return ""
    if "catalog_hidden" not in cols:
        return ""
    return (f" AND {param} NOT IN (SELECT clause_revision_id FROM clause_revision"
            f" WHERE doc_id IN (SELECT doc_id FROM doc_meta WHERE catalog_hidden = 1))")


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

      ⚠⚠ **2026-10-09 就地更正（spec 003）—— 上面那段对向量通道【作废】，下面这句也已更正过一次。**
        **初版更正（作废）**：曾写"`IN (子查询)` 只在**子查询恰好返回 1 个 id** 时成立、**≥2 个 id 恒返回 `[]`**"
        —— 那是**错的**（依据的探针喂的是文档 id 不是条款 id）。
        **真正的失效条件**（判决性实验 `specs/003-vec-scope-pushdown/probes/probe-mechanism.py`，
        且经独立复核用更细的档位确认）：**范围子查询返回的 id 里，只要有一个在向量表里【没有对应行】，
        整体就返回 `[]`**（返回的 id 全都有向量 ⇒ 正常；少一条 ⇒ 空）。
        **与 id 个数无关、与表大小无关**（近邻 25 → 100,000 条行为一样）。
        根因：`clause_revision_id` 是 vec0 的 **TEXT PRIMARY KEY**，sqlite-vec **不把它用于 KNN 前置过滤**。
        ⇒ 修法（已实测 + 已迁移）：给 `clause_vec` 加**元数据列** `doc_id`，改用 `_scope_vec()`。
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

    # ── 目录可见性（spec 013）：`catalog_hidden=1` 的文档**不进检索** ──────────────
    # 判据的唯一所有者是上面两个函数；这里只取一次片段，六条通道共用。
    # ⚠ 为什么不提供开关：`catalog_hidden=1` 的语义就是"不该被用户看见"，
    #   浏览与检索**必须一致** —— 两套可见性迟早漂移（这正是本缺陷的成因）。
    vis_doc = _catalog_visible_fragment(conn)
    vis_clause = _catalog_visible_by_clause(conn)
    #: 隐藏文档的 doc_id 集合（通道 C 在 Python 里筛要用）。
    hidden_doc_ids: set[str] = set()
    #: `clause_revision_id -> doc_id` 的小缓存（通道 C 逐条查会 N+1）。
    _doc_of_clause: Dict[str, Any] = {}
    if vis_doc:
        try:
            hidden_doc_ids = {r[0] for r in conn.execute(
                "SELECT doc_id FROM doc_meta WHERE catalog_hidden = 1")}
        except sqlite3.Error:
            hidden_doc_ids = set()
        if hidden_doc_ids:
            logger.info("目录卫生：%d 篇 catalog_hidden=1 的文档不进检索", len(hidden_doc_ids))

    def _scope_doc(param: str = "cr.doc_id") -> str:
        """范围 SQL 片段（**只在真的限定范围时**拼进查询）。"""
        return f" AND {param} IN (SELECT value FROM json_each(?))"

    def _scope_clause(param: str = "clause_revision_id") -> str:
        """FTS 表没有 doc_id 列 ⇒ 回 `clause_revision.doc_id` 判（同为检索层过滤）。

        ⚠ 2026-10-09（spec 003）就地更正：这句原来写的是"FTS/**向量表**没有 doc_id 列"，
        且**向量通道也在调本函数**。**两处都不成立了** —— `clause_vec` 已加 `doc_id` 元数据列，
        向量通道改走 `_scope_vec()`。原因见本函数上方那段 ⚠⚠ 与
        `specs/003-vec-scope-pushdown/research.md` R2。
        """
        return (f" AND {param} IN (SELECT clause_revision_id FROM clause_revision"
                f" WHERE doc_id IN (SELECT value FROM json_each(?)))")

    def _scope_vec() -> str:
        """向量通道的范围片段：**必须**打在 `clause_vec.doc_id`（元数据列）上才下推。

        ⚠ **只许这一种写法**。实测（sqlite-vec 0.1.9 / SQLite 3.53.1，
        `specs/003-vec-scope-pushdown/probes/probe-vec-scope-fix.py`）：
          · `doc_id IN (?, ?)` 字面量列表  ⇒ **返回范围外的行**（Q2b）
          · `doc_id = ? OR doc_id = ?`     ⇒ 同上（Q2d）
          · `rowid IN (…)`                 ⇒ `no such column: rowid`（Q3）
        那两种"看着像"的写法**比不修更糟**：现状是"假报没有"，它们是"假报有"。
        范围大小不设上限（Q5：100 篇仍下推）；不加范围时**不拼这一段**（Q6 零回归）。
        """
        return " AND doc_id IN (SELECT value FROM json_each(?))"

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
            # 实测代价（**快照库，与门禁同口径**）：金标 90 条检索题里，旧判据比诚实判据
            # "多算"**14 / 4 / 0** 条（按前 1 / 前 5 / 前 10）。⚠ 作者原写"47 条"是**错的**——
            # 47 是**真库**上的数（67−20），被误填进了快照的表里，第二轮复核已打回并留痕。
            # 认不出标准号时（`want_keys` 为空）**行为一字不改** —— 历史语义完整保留。
            from src.core.text_utils import standard_key
            want_keys = {standard_key(s) for s in _STD_IN_QUERY_RE.findall(query)}
            # ⚠ **必须在库里验证这一步**（第二轮复核 P0）：库里没有对应文档的记号不许筛。
            # 判据与耗时见 `_known_standard_keys` 的 docstring（词边界包含 + 约 16 ms/次）。
            if want_keys:
                want_keys = _known_standard_keys(
                    want_keys, [s for (s,) in conn.execute("SELECT standard_no FROM doc_meta")])
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
                # ⚠ 目录可见性（spec 013）：`catalog_hidden=1` 的文档不进检索。
                # 判据的唯一所有者见 `_catalog_visible_fragment`。
                + vis_doc
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
                # **2026-09-25（P0.4）补上 `cr.clause_revision_id` 兜底**：原先是**非全序**，
                # 同状态多行时次序不保证。补齐后 A 与 D/E 口径一致（全序）。
                # ⚠ **本通道刻意不加行数上限**——理由见文件上方那段长注释（第二轮复核 P0：
                #   通道内名次不是相关性名次，`LIMIT` 会任意丢候选，实测 6/6 挤出正确条款）。
                + " ORDER BY (dm.legal_status IS NULL), dm.legal_status, cr.clause_revision_id",
                ((exact_no, scope_json) if scope_active else (exact_no,))).fetchall()
            if want_keys:
                # 判据是 `_std_key_hits_doc`（**词边界包含**），不是裸包含——
                # 裸包含会把 `GB/T 2033-2008` 的键命中到 `GB/T 12033-2008`（数字后缀），
                # 正是上一批要关掉的那类假命中（第二轮复核实测端到端复现）。
                # ⚠ 抽成函数是为了可单测（第四轮复核的"残余 1"）：快照库里**一对后缀碰撞都没有**，
                #   所以把判据换成裸包含时全仓测试**全绿** —— 那把尺子结构上看不见。
                rows = _rows_matching_standard_keys(rows, want_keys)
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
                    # 目录可见性（spec 013）：FTS 表没有 doc_id，走 clause_revision 中转。
                    + vis_clause
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
                + (_scope_vec() if scope_active else "")
                + " ORDER BY distance",
                ((json.dumps(q_emb), scope_json) if scope_active
                 else (json.dumps(q_emb),))).fetchall()
            # ⚠ 目录可见性（spec 013）：**这一路在 Python 里筛**，不拼 SQL。
            # 为什么与其余五路不同：`clause_vec` 是 vec0 虚表，
            # 实测**只验证过** `doc_id IN (子查询)` 这一种下推写法
            # （`specs/003-vec-scope-pushdown`），**`NOT IN` 没验证过** ——
            # 而这个仓库已经栽过一次"看着像的写法比不修更糟"（见 `_scope_vec` 的注释：
            # 字面量列表会**返回范围外的行**）。⇒ 在没验证之前，宁可**取回再筛**
            # （代价：k=20 里可能少几条；隐藏文档实测 7 篇 / 8,983 = 0.08%，
            #  影响可忽略，而写错一个 vec0 约束会让整路返回空）。
            if hidden_doc_ids:
                keep = []
                for r in rows:
                    owner = _doc_of_clause.get(r[0])
                    if owner is None:
                        owner = conn.execute(
                            "SELECT doc_id FROM clause_vec WHERE clause_revision_id = ?",
                            (r[0],)).fetchone()
                        owner = owner[0] if owner else None
                        _doc_of_clause[r[0]] = owner
                    if owner not in hidden_doc_ids:
                        keep.append(r)
                rows = keep
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
            # 目录可见性（spec 013）。
            + vis_doc
            # ⚠ 这一条**原先完全没有 ORDER BY**（复核 b9 的 LOW-3 顺带指出、本步修，
            # 方案未决第 12 条的 INFO-6）：`rank` 直接决定
            # `CHANNEL_WEIGHTS / (RRF_K + rank + 1)`，而**没有 ORDER BY 的 SELECT 返回次序
            # 是未定义的**（实际由访问路径/rowid 决定，改规划器、加索引、VACUUM 都可能变）
            # ⇒ 同一个查询的权重分配**不可复现**，而且**无法断言**。
            # 排序口径与通道 A 一致：未核验（NULL）沉底，已知状态按名排，最后用 id 兜底
            # 保证**全序**（同状态多行时也确定）。取舍（已废止排在未核验之前）与 A 相同，
            # 见通道 A 那条注释——**口径的唯一所有者在 A**，这里只负责"更全"（多了 id 兜底）。
            # ⚠ **本通道刻意不加行数上限**（第二轮复核 P0）：见文件上方长注释。
            # （原先这条**完全没有上限**，模态='应' 一次拉 14 万条 ⇒ 内存问题仍在，已登记为独立缺陷。）
            + " ORDER BY (dm.legal_status IS NULL), dm.legal_status, cr.clause_revision_id",
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
            # 目录可见性（spec 013）。
            + vis_doc
            # ⚠ 这条原先**没有 ORDER BY**（复核 b9 的 LOW-3 顺带指出、§10.58 先补了"确定性"）：
            # `rank` 直接决定 `CHANNEL_WEIGHTS / (RRF_K + rank + 1)`，没有 ORDER BY 的返回次序
            # 是未定义的 ⇒ 同一查询的权重分配不可复现。
            # 本步把**口径与通道 A/D 对齐**：未核验（NULL）沉底、已知状态按名排、id 兜底成全序。
            # 取舍（已废止排在未核验之前）见通道 A 注释（唯一所有者）；本处与 A 的差别是
            # **多了 id 兜底** ⇒ 这条是**全序**，A 不是（复核 b12 的 INFO）。
            # ⚠ **本通道刻意不加行数上限**（第二轮复核 P0）：见文件上方长注释。
            + " ORDER BY (dm.legal_status IS NULL), dm.legal_status, cr.clause_revision_id",
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
                    # 目录可见性（spec 013）。
                    + vis_clause
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

    ⚠ **已知缺陷（2026-10-09 实测，已登记，本批未修）**：本函数在**真实调用形态**下恒不生效 ——
    `_rerank_results` 传进来的 `kept` 长度**已经等于 `top_k`**，于是"append 例外条款"
    紧接着被最后那句 `return kept[:top_k]` **原样切掉**。
    实测（`var/tmp/probe-exception-protect.py`）：`kept` 长度 == `top_k` ⇒ 例外**不保留**；
    只有 `kept` 一开始就短于 `top_k`（`tests/test_reranker.py::test_rerank_exception_clause_kept`
    用的就是这种形态）才保留 ⇒ 那条判据测的是一个**真实路径上不会出现的形态**。
    ⚠ 影响面：修好 `reranker.rerank` 的返回形状（总纲 0.7）之后，重排才**真的会发生**
    ⇒ 本缺陷从"无害的摆设"变成"**例外条款会被重排挤掉**"的真风险。
    ⇒ **把 rerank 接进生产之前必须先修它**（见 `docs/RETRIEVAL-LONG-RANGE-PLAN.md` P0·0.7 段）。
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
        scores = reranker.rerank(query, texts)  # 与 texts 一一对应（未排序）
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
