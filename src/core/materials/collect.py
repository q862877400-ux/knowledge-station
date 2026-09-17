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

#: 法规名常见结尾（**窄**：只用于"标题像不像法规"，不用于判层级）。
#: ⚠ `法典` 必须单列：`中华人民共和国民法典` **不以"法"结尾**，而它是中国最重要的一部法律
#: （第一版漏了它，被自己的用例抓出来）。
LAW_NAME_SUFFIXES = ("法", "法典", "条例", "规定", "办法", "细则", "规则", "决定", "解释", "通知")
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
    """从标题（或正文首行）取**法规名**（取不到返回 None）。

    三条来源，按可信度排：标题里的 `《…》` → 标题本身就是法规形态 → 正文首行。
    ⚠ 只取"名字"，**不**在这里判层级（那要发行机关，采网页拿不到；见 `track_l`）。
    """
    t = (title or "").strip()
    m = _RE_LAW_TITLE.search(t)
    if m:
        return m.group(0)[1:-1].strip()
    if t and len(t) <= 40 and t.endswith(LAW_NAME_SUFFIXES):
        return t
    first = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
    if not first:
        return None
    m2 = _RE_LAW_TITLE.search(first[:120])
    if m2:
        return m2.group(0)[1:-1].strip()
    if len(first) <= 40 and first.endswith(LAW_NAME_SUFFIXES):
        return first
    return None


def looks_like_law(title: str, text: str) -> dict[str, Any]:
    """认出"这可能是一部**法规**的正文"（Track L 的**法规入口**，Phase C 第八步）。

    ## 为什么需要它（这是 C-3 留下的一句"走不通"）
    `looks_like_standard` 复用 `auto_tag` 的**标准号正则** ⇒ **法规没有标准号**，
    永远认不出（`track_l.import_to_library` 自己的 docstring 就写着"当前实际只会走
    标准那一支"）。于是"采集到的法规正文自动入库"这句承诺在法规这一侧是**空的**。

    ## 判据（两条信号，**都要**真有"第X条"条文；宁可不认，也不要把新闻当法规）
    1. **有法规形态的标题**（`《…》` 或以上述后缀结尾）**且**条数 ≥ `LAW_MIN_CLAUSES`(3)；
    2. **条数 ≥ `LAW_STRONG_CLAUSES`(10)** —— 没有可用标题也认（采网页常丢标题）。

    条数由 `ingestion.law_text.split_law_text` 数（**第X条切分的唯一所有者**，
    本函数**不新写**第二份正则——标准号那次教训就是"同一机制两份实现必然分叉"）。

    ⚠ **优先级在调用方**：若同时认成标准（有标准号），走**标准**那一支
    （标准号的判据更精确；有标准号的文本不该被当法规入库）。
    """
    articles = split_law_text(str(text or ""))
    count = len(articles)
    name = _law_name_of(title, text)
    if name is not None and count >= LAW_MIN_CLAUSES:
        return {"is_law": True, "law_name": name, "clause_count": count,
                "why": f"标题是法规形态且含 {count} 条条文"}
    if count >= LAW_STRONG_CLAUSES:
        return {"is_law": True, "law_name": name, "clause_count": count,
                "why": f"含 {count} 条条文（标题不可用，按条数认）"}
    return {"is_law": False, "clause_count": count, "law_name": name}


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
    )
    n = mr.add_chunks(mat["material_id"], chunks)
    out = mr.get_material(mat["material_id"]) or mat
    out["chunk_count"] = n
    out["duplicate"] = False
    out["near_duplicate_of"] = near
    out["track_l"] = evidence.get("track_l")
    return out
