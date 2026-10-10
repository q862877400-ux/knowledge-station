"""别名/大白话反查（Phase 6：R48）。

抽取：从"术语和定义"章节文本按行抽取 [术语]：定义 → alias_store(term=术语, alias=定义核心名词)；
检索扩展：query 分词命中 alias_store.alias → 把标准 term 并入 FTS 查询（透明生效）。
"""
from __future__ import annotations

import re

from src.core.storage.sqlite_db import get_db_connection, write_transaction

# 术语行模式：'3.1.1 消防电梯 fire lift：定义……' / '术语——定义' / '术语：定义'
_TERM_LINE = re.compile(
    r"^[ 0-9.]*([一-鿿A-Za-z0-9·（）()/\-]{2,24}?)[：:—－](.+)$")
_DEF_NOISE = re.compile(r"^(本文件|本标准|本法|本规范|本术语|指|是指|系指)")

# 碎片防御：alias 中若含虚词/动词语义字，视为定义片段而非可用大白话
_ALIAS_DIRTY = "的在了与和是了从以于及或都也非不更很除利用进行场所处于状态产生可能涉及影响采用应将把被对为由向跟让使按据依随当若如例等中内上下前后间外里处时由于其之所此那这须可应再还既却则"


def _alias_clean(alias: str) -> bool:
    """alias 是否为可用的干净大白话（2-8 字纯中文、无虚词/动词碎片）。"""
    if not alias or len(alias) < 2 or len(alias) > 8:
        return False
    return not any(ch in _ALIAS_DIRTY for ch in alias)
# 术语章节标题。实测的**真实形态**（2026-10-10 真库抽样）：
#   `3 术语和定义`（最常见）/ `3 术语和定义、符号、缩略语` / `3.1 术语和定义`
#   `下列术语和定义` / `术语与定义` / `术语`
# ⚠ 原先写作 `^\s*[0-9]*\s*(术语和定义|…)\s*$` —— **要求整行只有"编号 + 这几个字"**，
#   于是把 `3 术语和定义、符号、缩略语` 判成不匹配 ⇒ 区间定位失败 ⇒ 回退全文 ⇒
#   前言又被扫进来（2026-10-10 实测：40 条里 8 条定位不到，正是这一类）。
#   ⇒ 改成"行首编号（可有可无）+ 这几个字 **开头**"，允许后面还有顿号分隔的并列词。
_TERM_SECTION = re.compile(
    r"^\s*(?:[0-9]+(?:\.[0-9]+)*\s*)?(?:下列)?术语(?:和定义|与定义)?\s*(?:[、，,].*)?$")

# 下一章标题（术语章节到此结束）。标准正文的章节标题形如 "4 结构型式和型号"。
# ⚠ **必须是「裸整数 + 标题」**（`4 结构型式和型号`），不能是 `3.1 动火作业：…`：
#   后者是**术语条目**（带小数点编号、且通常带冒号），若把它当章节边界，
#   术语章节会在**第一条术语行**处就结束 ⇒ 一条都抽不到（2026-10-10 实测踩到）。
# ⚠ **标题要够长**：目录页的"页码行"形如 `4`、`5`、`6` 或 `附录A (规范性附录) …`
#   也在正文里出现，若把裸数字当章节边界，区间会**在目录处就截断**。
#   ⇒ 要求标题正文 ≥2 字（`4 结构型式和型号` 满足；`4` 不满足）。
_NEXT_SECTION = re.compile(r"^\s*[0-9]+\s+\S{2,}")

# 前言类噪音行：起草单位 / 起草人 / 代替关系 / 发布实施 —— 它们不是术语定义。
_FRONT_MATTER = re.compile(
    r"起草单位|起草人|主要起草|参加起草|代替|被代替|发布|实施|"
    r"国家质量监督检验检疫总局|国家标准化管理委员会|"
    r"按照\s*GB/T\s*1\.1|给出的规则起草|规范性附录|资料性附录|"
    r"^ICS|^[A-Z]\d{2}\s*$|^前言$|^前\s+言$")

# 「引导句」不是术语：标准的术语章节常以一句**引用语**开头，形如
#   `GB/T 19278 界定的以及下列术语和定义适用于本文件。`
#   `下列术语和定义适用于本文件。`
# 它满足"术语行 + 定义行"的形状（下一行可能还有内容），但**它本身是章节引导语**，
# 抽出来会得到 term=`GB/T6274` / cores=`界定/术语/定义` 这种垃圾（2026-10-10 实测）。
# ⇒ 术语行**自身**命中这些词就整条丢掉。
_LEAD_IN = re.compile(
    r"适用于本文件|适用于本标准|界定的|下列术语和定义|术语和定义适用于|"
    r"^注\s*[0-9]|^警告$|^范围$|^规范性引用文件$|^一般要求$")


def _term_section_span(lines: list[str]) -> tuple[int, int] | None:
    """定位**术语章节**的行区间 `[start, end)`。

    为什么要它：本函数原先只判"全文含『术语和定义』"（`_TERM_SECTION.search(text)`），
    然后**扫描全文每一行**。而标准的正文前有**封面与前言**（起草单位、起草人、代替关系），
    那几行同样满足"编号+术语"或"术语行+下一行定义"的形状 ⇒ 被当术语抽走。

    实测后果（2026-10-10，真库只读）：`alias_store` 里出现
    `term='本标准负责起草单位' alias='西安'`、`term='本标准主要起草人' alias='赵卉'`、
    `term='规范性引用文件' alias='下列文件中的'` 这类**前言碎片**。

    ⇒ 现在先框出术语章节的**行区间**，只在区间内扫描。
    找不到区间（章节标题不在行首/不独立成行）⇒ 返回 `None`，由调用方按老行为处理。
    """
    start = None
    for i, ln in enumerate(lines):
        if _TERM_SECTION.match(ln):
            start = i
            break
    if start is None:
        return None
    # 章节结束：标题之后第一个"编号 + 非空标题"的行
    for j in range(start + 1, len(lines)):
        s = lines[j].strip()
        if not s:
            continue
        if _NEXT_SECTION.match(s) and not _TERM_SECTION.match(s):
            return (start, j)
    return (start, len(lines))



def _term_key(term: str) -> str:
    return term.strip().replace(" ", "").replace("　", "")


def extract_terms_from_text(text: str, source_doc_id: str | None = None,
                            auto_store: bool = True) -> list[dict]:
    """从含"术语和定义"章节的文本抽取术语行 → alias_store（幂等 UPSERT）。

    定义中的核心名词（2-6 字、非虚词开头）作 alias，供用户"大白话"反查。
    """
    found: list[dict] = []
    lines = [ln.strip() for ln in text.splitlines()]

    # ★ 区间定位不到 ⇒ **不再回退全文**（2026-10-10 修）。
    #   判据（真库 300 条抽样，`var/tmp/n5-fallback-tradeoff.py`）：
    #   定位不到的 **96 条**里，回退全文抽出的 **86** 个 term，
    #   逐条看**全部**是前言/标准号/目录/注（`GB/T10544`、`本标准使用翻译法等同采用ISO3862`、
    #   `第4部分`、`注1`、`范围`、`规范性引用文件`…），**没有一个真术语**。
    #   ⇒ 回退的收益是 0、代价是往 `alias_store` 灌垃圾，而垃圾别名会被
    #   `expand_with_alias` 真的并进用户查询（污染 FTS 的 OR 扩展）。
    #   **宁可少抽，不可抽错。**
    span = _term_section_span(lines)
    if span is None:
        return []
    lo, hi = span
    lines = lines[lo:hi]

    # 模式B：术语行（编号+术语，可含英文，无冒号）→ 下一行为定义
    #   例：'3.1 特殊作业 special work' \n '危险化学品企业……的作业。'
    # 模式B 术语行必须行首带编号（排除封面/前言等无编号噪音行）
    _TERM_ONLY = re.compile(r"^[0-9.]+[ ]*([一-鿿A-Za-z][一-鿿A-Za-z0-9·（）()/ -]{1,23})$")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _TERM_LINE.match(line)
        if m:
            term, definition = m.group(1).strip(), m.group(2).strip()
        else:
            m2 = _TERM_ONLY.match(line)
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            nxt_starts_with_no = bool(re.match(r"^[0-9.]*[0-9]", nxt))
            if m2 and not nxt_starts_with_no and len(nxt) >= 4:
                term = m2.group(1).strip()
                if term in ("术语和定义", "下列术语和定义", "术语与定义", "术语"):
                    i += 1
                    continue
                definition = nxt
                i += 1  # 吃掉定义行
            else:
                # 模式C：纯编号行 + 术语行 + 定义行（MinerU 三行式）
                #   '3.1' \n '特殊作业 special work' \n '危险化学品企业……'
                m3 = re.match(r"^[0-9.]+$", line)
                term_candidate = lines[i + 1] if i + 1 < len(lines) else ""
                def_candidate = lines[i + 2] if i + 2 < len(lines) else ""
                if (m3 and term_candidate
                        and not re.match(r"^[0-9.]+$", term_candidate)
                        and not re.match(r"^[0-9.]+[ ]*[0-9]", term_candidate)
                        and len(def_candidate) >= 4
                        and not re.match(r"^[0-9.]+", def_candidate)):
                    term = term_candidate.strip()
                    if term in ("术语和定义", "下列术语和定义", "术语与定义", "术语"):
                        i += 1
                        continue
                    definition = def_candidate
                    i += 2  # 吃掉术语行与定义行
                else:
                    i += 1
                    continue
        i += 1
        if len(term) < 2 or len(term) > 24 or len(definition) < 4:
            continue
        if _DEF_NOISE.search(definition):
            continue
        # ★ 前言类噪音闸（2026-10-10 修）：术语行**自身**若像前言条目，整条丢掉。
        #   区间定位已挡住绝大多数；这一条挡"术语章节里混进前言句"的残余形态。
        if _FRONT_MATTER.search(term) or _FRONT_MATTER.search(definition[:24]):
            continue
        # ★ 引导句闸（2026-10-10 修）：术语行自身若是"…界定的…适用于本文件"这类
        #   章节引导语，整条丢掉（它会被抽成 term=`GB/T6274` 这种）。
        if _LEAD_IN.search(term) or _LEAD_IN.search(definition[:24]):
            continue
        cores = _core_nouns(definition)[:3]
        found.append({"term": term, "definition": definition, "cores": cores})

    if auto_store and found and source_doc_id:
        import hashlib
        with write_transaction() as conn:
            for f in found:
                base = hashlib.sha256(f["term"].encode("utf-8")).hexdigest()[:16]
                for i, core in enumerate(f["cores"]):
                    conn.execute(
                        "INSERT OR IGNORE INTO alias_store"
                        " (alias_id, term, alias, source_type, source_doc_id, confidence)"
                        " VALUES (?,?,?,?,?,?)",
                        (f"al_{base}_{i}", f["term"], core,
                         "auto_extract", source_doc_id, 0.8))
    return found


_STOP_WORD_HEAD = re.compile(r"^(指|是|为|系|凡|即|在|进行|直接|间接|产生|采用|使用|用于|具有|指在|指为|通过|按照|依据|根据|由|对|向|将|以|可|应|须|不得|应当|必须|表示|规定|要求)")


def _core_nouns(definition: str) -> list[str]:
    """定义中 2-6 字名词候选（去虚词/动作词开头），作 alias 集合。

    优先 jieba 词性提取（名词/动名词、无碎片脏字），失败回退 2-6 字块。
    """
    cleaned = _DEF_NOISE.sub("", definition)
    out: list[str] = []
    try:
        import jieba.posseg as pseg
        for w, flag in pseg.cut(cleaned):
            w = w.strip()
            if len(w) < 2 or len(w) > 6:
                continue
            if flag[0] not in ("n", "v"):
                continue
            if any(ch in _ALIAS_DIRTY for ch in w):
                continue
            if w not in out:
                out.append(w)
    except Exception:
        out = []
    if out:
        return out
    # ★ jieba 不可用时的回退（2026-10-10 修）：**不再对整段中文做滑窗切块**。
    #   原实现是 `re.findall(r"[一-鿿]{2,6}", cleaned)` —— `{2,6}` 是**贪婪**的，
    #   对一整段连续中文会**每 6 个字切一段**，于是产出
    #     "危险化学品企" / "业生产经营过" / "程中可能涉及" / "的，可能造成" …
    #   这些**不是词**，是窗口碎片。实测后果（真库只读）：`alias_store` 的 32 行里
    #   有 25 行是这种碎片，其中 **7 条标 `active`** ⇒ 会被 `expand_with_alias`
    #   真的并进用户查询（"危险化学品企" 这种假词会污染 FTS 的 OR 扩展）。
    #   ⇒ 现在改成**按标点/顿号切段，只接受"整段就是 2-6 字"的段** ——
    #   枚举式定义（"挖土、打桩、钻探"）仍能抽出可用别名，
    #   而散文式长定义**什么都不抽**（宁可少抽，不可抽错：错别名会污染检索）。
    for seg in re.split(r"[，,。；;：:、（）()【】\[\]/\\\s]+", cleaned):
        seg = seg.strip()
        if not (2 <= len(seg) <= 6):
            continue
        if not re.fullmatch(r"[一-鿿]+", seg):
            continue
        if _STOP_WORD_HEAD.match(seg):
            continue
        if any(ch in _ALIAS_DIRTY for ch in seg):
            continue
        if seg not in out:
            out.append(seg)
    return out


def expand_with_alias(query: str) -> str:
    """检索扩展：query 中含 alias → 追加对应标准 term（供 FTS OR 扩展）。

    零成本规则实现；无命中原样返回。
    """
    import jieba
    words = [w for w in jieba.cut_for_search(query) if len(w) >= 2]
    if not words:
        return query
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT DISTINCT term, alias FROM alias_store WHERE status='active'"
    ).fetchall()
    # 双向包含匹配（alias 库规模小，全表扫成本可忽略，命中率远高于精确 IN）
    # 防御：跳过句子碎片类 alias（含虚词/动词语义字），防止定义碎片污染检索查询
    extra_terms: list[str] = []
    for w in words:
        for r in rows:
            alias = (r["alias"] or "").strip()
            if not _alias_clean(alias):
                continue
            if (w in alias) or (alias in w):
                term = (r["term"] or "").strip()
                # 术语含英文长串时只取中文首段（如"受限空间 confined space"→"受限空间"）
                if len(term) > 24:
                    term = term.split()[0]
                if term and term not in extra_terms:
                    extra_terms.append(term)
    if not extra_terms:
        return query
    return f"{query} {' '.join(extra_terms[:5])}"
