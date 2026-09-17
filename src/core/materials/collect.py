# -*- coding: utf-8 -*-
"""材料平面：**自采入口**（Phase C，2026-09-17）。

## 这个模块解决什么
业主要求"**能自己搜集材料**"，同时（J4/§6）"**采集材料必须经用户判断或系统评审**"。
两者合起来意味着：自采**不能**是一条绕开评审的旁路——收集到的每一条都必须落到
**同一扇门**后面（`material.review_status='pending'`），由用户批准后才可能进入作答。

本模块就是那个**唯一入口**：抓取侧（模型、脚本或未来的采集器）把"我找到了什么"
交给它，它负责登记 + 判重 + 标注，**并且结构上无法批准**。

## 四条结构性约束（不是靠调用方自觉）
1. **永远 pending**：本模块**没有**任何能设置 `review_status` 的参数；
   `mr.add_material` 的默认就是 pending，这里连"传下去"的通道都不开。
2. **默认一次性**：`lifecycle='ephemeral'`（业主裁定："其它资料默认当前任务一次性，
   用户可提名长期参考"）。升为长期是**用户**的动作（`set_lifecycle`），不在采集路径上。
3. **来源必须交代**：`url` / `domain` / `title` 至少要有出处标识，否则记为
   "身份未知"——而 `authority` 那层已经写明：**身份未知者不能参与互证**。
   ⇒ 采来的东西默认只是"线索"，不是"依据"。
4. **判重**：同项目内 `content_hash` 相同 → 不新建，直接返回既有材料并标 `duplicate=True`；
   内容**近似**（`dedup`）→ 仍登记，但记下 `near_duplicate_of`，评审人看得到"疑似同稿"。

## 与 Track L 的关系
"采到库内没有的法规标准"要在**评审通过后**自动入库（走既有 ingest 管线进 `doc_meta`，
再由 `material.doc_id` 回指——**法条链一个字段都不改**）。本模块只负责**认出**它可能是
标准（复用 `knowledge.auto_tag` 的既有判据，不新写第二份正则），并把该意图记在
`tier_evidence['track_l']` 里；**真正的入库是评审通过之后的事**（下一步）。

## 诚实边界
- 本模块**不抓网**：抓取（含 SSRF/外发纪律）在调用方；这里只做"登记与判据"。
- `content_hash` 对**文本**候选是文本的哈希（不是"源文件字节"）——网页没有"源文件"；
  这点的后果是：同一网页两次抓取若正文有个别变动，会被当成两份（判重只在完全相同或
  近似时才合并）。
- 近似判重是**启发式**（`dedup` 的阈值 0.8，判"文字是否几乎一样"），标注给**人**看，
  不做任何自动决定。
"""
from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse

from src.core.ingestion import material_ingest as mi
from src.core.ingestion.law_text import split_law_text
from src.core.materials import dedup
from src.core.storage import material_repo as mr
from src.core.text_utils import looks_like_binary

#: 一次采集最多拿多少条做近似比对（避免在大项目上 O(k²) 失控）。
NEAR_DUP_WINDOW = 200

#: 近重复判定的阈值（与 `dedup` 默认一致；写成常量以便一处调）。
NEAR_DUP_THRESHOLD = dedup.DEFAULT_THRESHOLD

#: 认法规的**条数门槛**（两个信号各一个门槛，见 `looks_like_law`）。
LAW_MIN_CLAUSES = 3        # 有法规形态标题时：≥3 条就算
LAW_STRONG_CLAUSES = 10    # 没有可用标题时：≥10 条才算（宁可不认）

#: 采集通道的**解析器指纹**（引用锚点稳定性，方案 §12 未决第 5 条）。
#: 网页材料没有留存原始字节 ⇒ 指纹不匹配时**无法**重解析复算（`locator` 会如实回
#: `unavailable`）。改这里就等于声明"采集侧派生文本的算法变了"。
COLLECT_PARSER_FINGERPRINT = "web:collect-v1"

#: 法规名常见结尾（**窄**：只用于"标题像不像法规"，不用于判层级）。
#: ⚠ `法典` 必须单列：`中华人民共和国民法典` **不以"法"结尾**，而它是中国最重要的一部法律
#: （第一版漏了它，被自己的用例抓出来）。
#: ⚠ **不含 `通知`**（2026-09-17 复核后收紧）：`《…通知》` 绝大多数是公告/新闻标题，
#: 把它算成法规名会让"某部门通知"这类标题直接变成法规候选（实测被用例抓出）。
#: 真·规范性文件若确实是法规正文，仍能走"标题不可用 + ≥10 条 + 立法句式"那一支。
LAW_NAME_SUFFIXES = ("法", "法典", "条例", "规定", "办法", "细则", "规则", "决定", "解释")

#: **明确不是法规**的结尾（复核实测：合同/判决书/方案会被误认成法规，进而污染法条库）。
LAW_NAME_EXCLUDE = ("合同", "协议", "订单", "标书", "招标文件", "判决书", "裁定书",
                    "起诉书", "答辩状", "说明书", "方案", "台账", "纪要", "函")

#: 立法句式：法规正文几乎一定会自称（"本法"/"本条例"/"本规定"…）。这是**必要证据之一**，
#: 用来把"引用了法条的新闻/合同/判决书"挡在外面。
_RE_LEGISLATIVE = re.compile(r"本(?:法|条例|规定|办法|规则|细则|决定)")
_RE_LAW_TITLE = re.compile(r"《[^》]{2,60}》")


def domain_of(url: str | None) -> str | None:
    """从 URL 取域名（与 `authority._domain_of` 同口径的**轻量版**：只取 host）。

    ⚠ 这里**不重复实现**归一化逻辑的那个细节（去 www/端口/大小写）——那在
    `authority._domain_of` 里，且 `authority._source_identity` 判"独立来源"时会再走一遍。
    本函数只负责把 host 填进 `material.domain`（存**原样的 host**），
    归一化交给判据那一层，免得两处口径分叉。
    """
    if not url:
        return None
    try:
        host = urlparse(url).hostname
    except ValueError:
        return None
    return host or None


def text_hash(text: str) -> str:
    """文本候选的 `content_hash`（sha256 十六进制，与 `file_hash` 同形以便共用列）。"""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def looks_like_standard(title: str, text: str) -> dict[str, Any]:
    """认出"这可能是一部法规/标准的正文"（Track L 的**判据入口**）。

    复用 `knowledge.auto_tag` 的既有正则（**不新写第二份**：标准号写法五花八门，
    两份正则必然分叉——本战役已经因为"同一机制两份实现"栽过好几次）。
    只返回元数据，**不做任何入库动作**。
    """
    from src.core.knowledge.auto_tag import auto_tag
    tags = auto_tag(f"{title}\n{text[:4000]}", filename=title)
    if not tags.standard_no:
        return {"is_standard": False}
    return {"is_standard": True, "standard_no": tags.standard_no, "year": tags.year}


def _near_duplicates(project_id: str, text: str) -> list[str]:
    """在同项目**已登记**材料里找内容近似的（返回 material_id 列表，最多几个）。

    只比对已登记材料的**切片文本**（`material_chunks` 里有全文），逐条用
    `dedup.similarity` 判——数量以 `NEAR_DUP_WINDOW` 为上限（超出的不参与，稳妥不贪）。
    """
    out: list[str] = []
    rows = mr.list_materials(project_id)[:NEAR_DUP_WINDOW]
    for r in rows:
        chunks = mr.material_chunks(r["material_id"])
        joined = "\n".join(str(c.get("text") or "") for c in chunks)
        if not joined:
            continue
        if dedup.similarity(joined, text, n=dedup.DEFAULT_NGRAM) >= NEAR_DUP_THRESHOLD:
            out.append(str(r["material_id"]))
    return out


def _law_name_of(title: str, text: str) -> str | None:
    """从**标题**取法规名（取不到返回 None）。

    ## ⚠ 为什么**只看标题**（2026-09-17 复核 step-31~34 的 MEDIUM-HIGH，实测数据污染）
    第一版还会扫"正文首行 120 字里的任意 `《…》`"。复核实测后果很重：
    一篇**新闻**（首行引了三条法条）被认成 `law_name='中华人民共和国安全生产法'`，
    批准后**真的往 `doc_meta` 插了一行**（`standard_no=中华人民共和国安全生产法`、
    `standard_name=新闻标题`）；此后采到**真**《安全生产法》全文再批准时，
    `find_existing_law` 命中那行新闻 ⇒ `link` 而不是 `import` ⇒ **真法规永远进不了库**。
    合同（《设备采购合同》）、判决书（正文引《合同法》）同理。
    ⇒ 正文里的书名号**一律不算**：法规名必须来自**标题**，且标题本身要像标题。

    ## 判据（宁可不认）
    1. 标题 ≤ 40 字、**不含句读**（`，。！？；：、`——那是新闻标题的典型特征）；
    2. 标题里若出现 `《…》`，取里面的名字作为候选；否则标题自身就是候选；
    3. 候选（去掉**非版本**括注后）必须以法规后缀结尾，或以「法」「条例」结尾；
    4. 候选**不得**是合同/协议/判决书/方案这类（`LAW_NAME_EXCLUDE`）。
    版本括注（`（2021年修正）`）**保留**——它是身份的一部分（见 `law_name_key`）。
    """
    t = (title or "").strip()
    if not t or len(t) > 40:
        return None
    if any(ch in t for ch in "，。！？；：、"):
        return None                      # 像新闻标题，不像法规名
    m = _RE_LAW_TITLE.search(t)
    cand = (m.group(0)[1:-1] if m else t).strip()
    if not cand or len(cand) > 40:
        return None
    # 去掉**非版本**括注（`（节选）`/`(摘录)`），但保留 `（2021年修正）` 这类版本标记
    # ——版本标记是**身份的一部分**（见 `law_name_key`），而"节选"不是。
    ver = re.search(r"[（(]([^）)]*)[）)]\s*$", cand)
    keeps_version = bool(ver and re.search(r"修正|修订|修改|决定|解释", ver.group(1)))
    base_cand = cand if (ver is None or keeps_version) else cand[:ver.start()].strip()
    if not base_cand:
        return None
    if base_cand.endswith(LAW_NAME_EXCLUDE):
        return None
    if base_cand.endswith(LAW_NAME_SUFFIXES) or "条例" in base_cand or "法" in base_cand:
        return cand if keeps_version else base_cand
    return None


def looks_like_law(title: str, text: str) -> dict[str, Any]:
    """认出"这可能是一部**法规**的正文"（Track L 的**法规入口**，Phase C 第八步）。

    ## 为什么需要它（这是 C-3 留下的一句"走不通"）
    `looks_like_standard` 复用 `auto_tag` 的**标准号正则** ⇒ **法规没有标准号**，
    永远认不出（`track_l.import_to_library` 自己的 docstring 就写着"当前实际只会走
    标准那一支"）。于是"采集到的法规正文自动入库"这句承诺在法规这一侧是**空的**。

    ## 判据（**四条证据齐了才算**；宁可不认，也不要把新闻当法规）
    1. **标题是法规名**（`_law_name_of`：只认标题、不含句读、不是合同/协议/判决书类）；
    2. **条文从「第一条」开始**（`starts_at_first`）——新闻/判决书里的引用通常引第三条、第四条；
    3. **正文有立法句式**（`本(法|条例|规定|办法|规则|细则|决定)`）**且**条数 ≥
       `LAW_MIN_CLAUSES`(3)；
    4. **没有可用标题时**：条数 ≥ `LAW_STRONG_CLAUSES`(10) **且**同样满足 2、3。

    ⚠ 这四条是**复核 step-31~34 的 MEDIUM-HIGH 逼出来的**：只有"标题形态 + 条数"时，
    实测有一篇新闻（正文引了三条法条）被认成《安全生产法》，批准后**真的进了法条库**，
    还把此后采到的**真**《安全生产法》挤成 `link`（脏数据拦住了真数据）。
    第一版 docstring 写着"宁可不认，也不要把新闻当法规"——**那句话当时是空话**，现在是判据。

    条数由 `ingestion.law_text.split_law_text` 数（**第X条切分的唯一所有者**，
    本函数**不新写**第二份正则——标准号那次教训就是"同一机制两份实现必然分叉"）。

    ⚠ **优先级在调用方**：若同时认成标准（有标准号），走**标准**那一支
    （标准号的判据更精确；有标准号的文本不该被当法规入库）。
    """
    articles = split_law_text(str(text or ""))
    count = len(articles)
    name = _law_name_of(title, text)
    first_no = str(articles[0][0]) if articles else ""
    starts_at_first = first_no.replace(" ", "") == "第一条"
    legislative = bool(_RE_LEGISLATIVE.search(str(text or "")[:4000]))
    core = count >= LAW_MIN_CLAUSES and starts_at_first and legislative
    if name is not None and core:
        return {"is_law": True, "law_name": name, "clause_count": count,
                "starts_at_first": starts_at_first, "legislative": legislative,
                "why": f"标题是法规名、从第一条起共 {count} 条、且有立法句式"}
    if name is None and core and count >= LAW_STRONG_CLAUSES:
        return {"is_law": True, "law_name": None, "clause_count": count,
                "starts_at_first": starts_at_first, "legislative": legislative,
                "why": f"标题不可用，但正文从第一条起共 {count} 条且有立法句式"}
    return {"is_law": False, "clause_count": count, "law_name": name,
            "starts_at_first": starts_at_first, "legislative": legislative,
            "why": ("标题不是法规名" if name is None else "缺少立法句式或不是从第一条起"
                    if not core else "标题不可用且条数不足 " + str(LAW_STRONG_CLAUSES))}


def collect_text(project_id: str, *, title: str, text: str, url: str | None = None,
                 source_tier: str | None = None, published_at: str | None = None,
                 kind: str | None = None, note: str | None = None,
                 max_chars: int = mi.DEFAULT_MAX_CHARS) -> dict[str, Any]:
    """登记一条**自采**材料（文本形态：网页正文/接口返回的正文）。

    **返回值里 `review_status` 恒为 `pending`**——本函数没有任何途径把它设成别的值。

    Args:
        project_id: 落进哪个参考资料项目。
        title: 标题（**必填**：评审人要看的第一眼就是标题）。
        text: 正文（会被切成切片；切片文本本身就是**存档副本**——网页没有"源文件"）。
        url: 出处 URL（强烈建议给；不给就是"身份未知"，按 `authority` 的纪律不能互证）。
        source_tier: 轴 A 的可信度。**不给则 T3 起**（"网上找来的"在没证据前不该默认可信）。
        published_at: 发布时间（有则记）。
        kind: `legal` / `other`。不给则按 `looks_like_standard` 自动判定。
        note: 采集说明（进 `tier_reason`，评审人会看到"这条是怎么来的"）。
    """
    if not str(title or "").strip():
        raise ValueError("collect_text: title 必填（评审人第一眼看的就是标题）")
    body = str(text or "")
    if not body.strip():
        raise ValueError("collect_text: text 为空——没有正文的采集件不该登记（会变成盲签对象）")
    # 二进制容器当作正文送来 ⇒ **拒收**（不是"清洗"，是"这不是正文"）。
    # 判据的所有者是 `text_utils.looks_like_binary`（采集侧也调它，理由见那里）。
    # 为什么要挡在**这扇唯一的门**上：登记进来的东西直接进评审队列，
    # 而一条"读不了的正文"要等到分析时才暴露——那时它可能已经被批准了。
    if looks_like_binary(body):
        raise ValueError(
            "collect_text: 正文不是文本（看起来是 PDF/图片/压缩包等二进制容器）——"
            "本入口不接收二进制，请先走文档解析管线（`ingestion.material_ingest`）")

    # ---- 判重（完全相同）----
    chash = text_hash(body)
    for existing in mr.list_materials(project_id):
        if existing.get("content_hash") == chash:
            existing["duplicate"] = True
            existing["chunk_count"] = mr.chunk_count(existing["material_id"])
            return existing

    # ---- 认出可能是标准/法规（Track L 的入口；**不**在这里入库）----
    # ⚠ **优先级**：有标准号 ⇒ 走标准那一支（判据更精确；带标准号的文本不该被当法规）。
    # 只有认不出标准时才试着认法规（`第X条` 形态），否则"法规正文入库"这句承诺是空的。
    std = looks_like_standard(title, body)
    law = {"is_law": False} if std.get("is_standard") else looks_like_law(title, body)
    is_legal = bool(std.get("is_standard") or law.get("is_law"))
    resolved_kind = kind or ("legal" if is_legal else "other")

    # ---- 近似判重（标注给人看，不做自动决定）----
    near = _near_duplicates(project_id, body)

    pages: list[tuple[int, str]] = [(1, body)]
    canonical, spans = mi.build_document(pages)
    chunks = mi.chunk_text(canonical, spans, max_chars=max_chars)

    evidence: dict[str, Any] = {"collected": True}
    if near:
        evidence["near_duplicate_of"] = near
    if std.get("is_standard"):
        evidence["track_l"] = {"doc_kind": "standard",
                               "standard_no": std.get("standard_no"), "year": std.get("year"),
                               "status": "pending_review"}
    elif law.get("is_law"):
        evidence["track_l"] = {"doc_kind": "law", "law_name": law.get("law_name"),
                               "clause_count": law.get("clause_count"),
                               "status": "pending_review"}

    reason_parts = [p for p in [note] if p]
    if near:
        reason_parts.append(f"疑似与已有材料同稿（{len(near)} 条内容近似）——请核对后决定")
    if std.get("is_standard"):
        reason_parts.append(f"疑似标准正文（{std.get('standard_no')}）——"
                            "批准后才会自动入库为法条（Track L）")
    elif law.get("is_law"):
        reason_parts.append(f"疑似**法规**正文（{law.get('law_name') or '名称未取到'}，"
                            f"{law.get('clause_count')} 条）——批准后才会自动入库为法条（Track L）；"
                            "⚠ 效力层级由本系统按名称**推断**（采网页拿不到发行机关），"
                            "不确定时记为「未定」")

    mat = mr.add_material(
        project_id,
        title.strip(),
        origin="collected",                 # ← 采集来源必须留痕（与用户自有件区分）
        kind=resolved_kind,
        source_tier=source_tier,            # None ⇒ add_material 给 T3（网上找来的默认不可信）
        url=url,
        domain=domain_of(url),
        content_hash=chash,
        published_at=published_at,
        tier_evidence=evidence,
        tier_reason="；".join(reason_parts) if reason_parts else None,
        # 引用锚点（方案 §12 未决第 5 条）：网页材料的"派生全文"就是**调用方交给我们的
        # 这段文本**（`html_to_text` 的产物在调用方那一层完成），所以指纹记的是
        # **本采集入口**的身份；网页没有留存原始字节 ⇒ 指纹不同时**无法**重解析复算，
        # `locator.reverify_material_locators()` 会如实回 `unavailable`（不是 ok）。
        derived_text_hash=chash,
        parser_fingerprint=COLLECT_PARSER_FINGERPRINT,
    )
    n = mr.add_chunks(mat["material_id"], chunks)
    out = mr.get_material(mat["material_id"]) or mat
    out["chunk_count"] = n
    out["duplicate"] = False
    out["near_duplicate_of"] = near
    out["track_l"] = evidence.get("track_l")
    return out
