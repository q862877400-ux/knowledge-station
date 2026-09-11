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
_TERM_SECTION = re.compile(r"术语和定义|下列术语和定义|术语与定义")


def _term_key(term: str) -> str:
    return term.strip().replace(" ", "").replace("　", "")


def extract_terms_from_text(text: str, source_doc_id: str | None = None,
                            auto_store: bool = True) -> list[dict]:
    """从含"术语和定义"章节的文本抽取术语行 → alias_store（幂等 UPSERT）。

    定义中的核心名词（2-6 字、非虚词开头）作 alias，供用户"大白话"反查。
    """
    if not _TERM_SECTION.search(text):
        return []
    found: list[dict] = []
    lines = [ln.strip() for ln in text.splitlines()]
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
    for w in re.findall(r"[一-鿿]{2,6}", cleaned):
        if len(w) < 2:
            continue
        if _STOP_WORD_HEAD.match(w):
            continue
        if any(ch in _ALIAS_DIRTY for ch in w):
            continue
        if w in out:
            continue
        out.append(w)
    if not out:
        return [cleaned[:4]]
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
