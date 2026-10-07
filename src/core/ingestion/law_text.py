"""法条文本直灌通道（阶段3 新增，依据业主输入：法律法规以网页纯文本发布，基本无扫描版）。

跳过 PDF/MinerU 全链路，直接从法规原文文本切分入库：
适合从政府网站复制的法律正文、法规 Markdown 等。

用法:
    python -m src.core.ingestion.law_text <text_file> --standard-no "民法典(节选)" \
        --name "中华人民共和国民法典(节选)" [--hierarchy 法律]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from ulid import ULID

from src.core.config import get_settings
from src.core.domain.models import ClauseRevisionModel
from src.core.knowledge.classifier import classify_clause
from src.core.storage import clause_repo
from src.core.storage.sqlite_db import get_db_connection, init_schema, write_transaction
from src.core.text_utils import store_standard_no

_LAW_SPLIT = re.compile(r"(?=第[一二三四五六七八九十百千零]+条)")
_LAW_NO = re.compile(r"^(第[一二三四五六七八九十百千零]+条)")
_CHAPTER_HEAD = re.compile(r"^第[一二三四五六七八九十百千]+[章节编]\s*.*$")

#: 「一、二、三、」编号（2026-10-07：部分司法解释/规定不用「第X条」）。
#: 只匹配**行首**且编号后紧跟「、」或「.」——「(一)」这类带全角括号的子项不匹配。
_LAW_ENUM_SPLIT = re.compile(r"(?=^[ \t]*[一二三四五六七八九十百]+[、.．])", re.M)
_LAW_ENUM_NO = re.compile(r"^[ \t]*([一二三四五六七八九十百]+)[、.．]\s*")


_GB_SPLIT = re.compile(r"(?=^\s*[A-Za-z]?\d+[．.]\d+(?:[．.]\d+)?(?![\d.])(?:\s+[^0-9]|[一-鿿(（A-Za-z]))", re.M)
_GB_HEAD = re.compile(r"^\s*([A-Za-z]?\d+[．.]\d+(?:[．.]\d+)?)\s*(.*)$", re.S)


def split_gb_text(text: str) -> list[tuple[str, str]]:
    """按 GB 风格条款号（3.1 / 4.2 / A.1）切分标准文本。条款号可单独成行或同行带正文。"""
    text = re.sub(r"[ 	　]+", " ", text)
    text = re.sub(r"[．]", ".", text)  # 全角点→半角
    parts = [p.strip() for p in _GB_SPLIT.split(text) if p.strip()]
    out: list[tuple[str, str]] = []
    chapter_ctx = ""
    for p in parts:
        m = _GB_HEAD.match(p)
        if not m:
            # 仅并入短章标题（如“3 术语和定义”）；长前言不并入
            piece = p.strip()
            if len(piece) <= 24 and "\n" not in piece:
                chapter_ctx = piece
            else:
                chapter_ctx = ""
            continue
        body = (m.group(2) or "").strip()
        out.append((m.group(1), (chapter_ctx + chr(10) + body).strip() if chapter_ctx else body))
    return out


def split_law_text(text: str) -> list[tuple[str, str]]:
    """按'第X条'切分法规文本。返回 [(条号, 正文)]；章/节标题并入其后条文上下文。

    支持网文常见格式：'第一条 xxx'、'**第一条** xxx'、'1. 第一条'。
    """
    # 归一 markdown 粗体与序号前缀
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"^[ \t]*\d+[\.、]\s*(?=第[一二三四五六七八九十百千零]+条)", "", text,
                  flags=re.M)
    text = re.sub(r"\*{0,2}(第[一二三四五六七八九十百千零]+条)\*{0,2}", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)

    parts = [p.strip() for p in _LAW_SPLIT.split(text) if p.strip()]
    out: list[tuple[str, str]] = []
    chapter_ctx = ""
    for p in parts:
        m = _LAW_NO.match(p)
        if not m:
            chapter_ctx = (chapter_ctx + " " + p)[:60]
            continue
        body = _LAW_NO.sub("", p, count=1).strip()
        out.append((m.group(1), (chapter_ctx + "\n" + body).strip() if chapter_ctx else body))
    return out


def split_law_enum_text(text: str) -> list[tuple[str, str]]:
    """按「一、二、三、」切分法规文本（**部分司法解释/规定不用「第X条」**）。

    2026-10-07 新增。触发场景：业主那批 LawRefBook 法规里，有 39 件**全是司法解释**
    （《人民检察院办理行政执法机关移送涉嫌犯罪案件的规定》等）用的是

        一、对于行政执法机关移送检察机关的涉嫌犯罪案件……
        二、人民检察院控告检察部门审查……

    而 :func:`split_law_text` 只认「第X条」⇒ 一条都切不出 ⇒ 入库报
    "未识别到任何'第X条'条文"（实测 39 件全部如此）。

    **只在「第X条」一条都没切出来时才调用**（调用方 `ingest_law_text` 保证），
    所以不会把「第X条」正文里的「一、二、」子项误当成条款。

    层级：(一)(二) 这类**不匹配**（编号前是全角括号），仍留在所属条目正文里。
    """
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    parts = [p.strip() for p in _LAW_ENUM_SPLIT.split(text) if p.strip()]
    out: list[tuple[str, str]] = []
    for p in parts:
        m = _LAW_ENUM_NO.match(p)
        if not m:
            continue
        body = _LAW_ENUM_NO.sub("", p, count=1).strip()
        if body:
            out.append((m.group(1), body))
    return out


def ingest_law_text(text: str, standard_no: str, standard_name: str,
                    legal_hierarchy: str = "法律",
                    domain_tags: list[str] | None = None,
                    effective_from: str | None = None,
                    *, doc_type: str = "法律法规",
                    short_code: str | None = None,
                    source_marker: str = "law-text://inline",
                    source_url: str | None = None,
                    clause_doc_type: str | None = None,
                    legal_status: str | None = "__default__",
                    quality_grade: str | None = "__default__",
                    standard_type: str | None = "__default__",
                    change_signal: str | None = "__default__",
                    fallback_single_clause: bool = False) -> dict:
    """法规纯文本 → 切分 → 分型 → 单事务原子入库（无源 PDF，file_path 记录来源标记）。

    Args:
        doc_type: 落 `doc_meta.doc_type`。默认 `法律法规`。
            **2026-09-17 新增**（Track L）：自采到的**标准**正文走同一条通道时必须传
            `standard` —— 生产库里 6417 行 `doc_meta` **全是** `standard`
            （6130 GB/T + 287 GB），把标准写成 `法律法规` 会与全库不一致。
            参数化而不是另写一份：切分/分型/建边/事务这段逻辑**只该有一份**
            （本战役已因"同一机制两份实现"栽过多次）。
        short_code: 跨版本稳定的短码。不给时用法规口径（去括号截断）；标准应传
            `standard_no.replace(" ","").replace("-","")`（与 `docx_ingest` 同口径）。
        source_marker: 落 `file_path` 的来源标记（本通道没有源文件，用标记占位）。
        source_url: 采集来源 URL（有则落 `doc_meta.source_url`，**溯源要看得到**）。
        clause_doc_type: **条款分型**用的 `doc_type`（`classify_clause` 的入参）。
            不给则**跟随 `doc_type`**。⚠ 2026-09-17 复核发现这里原来**写死**
            `"法律法规"`：于是 Track L 入的**标准**条款被判成 `knowledge_type='legal'`
            而不是 `'rule'`（标准条款不是法条）。
        legal_status / quality_grade / standard_type: 落库的效力/质量/类型值。
            **不给 = 沿用 `insert_document` 的既有默认**（`effective`/`A`/`mandatory`）。
            采集路径（`materials.track_l`）应传**诚实值**——它来自网页、不是官方原件，
            见那边的调用点。
            ⚠ **措辞更正**（2026-09-17 复核 b7 的 LOW-1）：原话写"为了不改**既有调用方**
            （docx/官方法规源）的行为"——那两条路**根本不调用本函数**
            （`docx_ingest.py` 与 `pipeline.py` 直接 `insert_document`）。
            哨兵真正护住的是**仓外/未来的调用方**以及 `track_l` 的两个分支：
            谁没显式传，就仍然拿到 `insert_document` 的默认值。
        change_signal: 落 `doc_meta.change_signal`（2026-09-24，§10.195）——"这份文件是某个
            法规/标准**发生变化**的线索"（`draft`/`repealed`/`revised`/`issued`/None），
            与本文档自己的 `legal_status` **正交**。同样用 `__default__` 哨兵：
            **不给 = 不写这列**（既有调用方行为一字不变），显式给 None = 写 NULL。
            判定单点在 `web_ingest.classify_change_signal`（确定性规则，**不是模型输出**）。
    """
    settings = get_settings()
    init_schema()
    conn = get_db_connection()
    file_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    # ⚠ 这里的查重按 `standard_no` 的**存储形**比对（§11.0 R6c-3d，查重与写入两边同口径）：
    # Track L 的调用方负责先用 `text_utils.standard_no_key` 判过"库里有没有"，
    # 并传**库里那种写法**进来——两处判据不要混。
    if conn.execute("SELECT doc_id FROM doc_meta WHERE file_hash=?", (file_hash,)).fetchone():
        return {"status": "duplicate"}
    same_no = conn.execute(
        "SELECT doc_id, file_hash FROM doc_meta WHERE standard_no=?",
        (store_standard_no(standard_no),)).fetchone()
    if same_no and same_no["file_hash"] != file_hash:
        return {"status": "standard_exists", "existing_doc_id": same_no["doc_id"]}

    doc_id = f"doc_{ULID()}"
    articles = split_law_text(text)
    if not articles:
        # 2026-10-07：司法解释/规定常用「一、二、三、」而不是「第X条」。
        # 放在「第X条」之后 ⇒ 正常法律不受影响，只有切不出条文时才启用。
        articles = split_law_enum_text(text)
    if not articles:
        articles = split_gb_text(text)
    if not articles and fallback_single_clause:
        # 政府网站的**公告/通知**常常没有"第X条"（一句到几段就是全文）。
        # 这类正文走同一条通道时不该被"未识别到条文"挡在门外 ⇒ 整篇作**一条**（编号"全文"）。
        # ⚠ 只在这个显式开关为真时生效：既有调用方（法规/标准正文）行为一字不变。
        body = text.strip()
        if body:
            articles = [("全文", body)]
    if not articles:
        return {"status": "error",
                "message": "未识别到任何条文（已试「第X条」、「一、二、三、」、GB 风格条款号）"}

    clause_type = clause_doc_type or doc_type
    models: list[ClauseRevisionModel] = []
    number_to_id: dict[str, str] = {}
    for no, body in articles:
        if len(body.strip()) < 4:
            continue
        tc = classify_clause(f"{no} {body}", doc_type=clause_type)
        cid = f"clrev_{ULID()}"
        number_to_id[no] = cid
        models.append(ClauseRevisionModel(
            clause_revision_id=cid, doc_id=doc_id,
            clause_key=clause_repo.make_clause_key(doc_id, no),
            standard_no=standard_no, clause_number=no,
            content_text=f"{no} {body}"[:4000], hierarchy_path=None,
            knowledge_type=tc.knowledge_type, type_confidence=tc.type_confidence,
            modality=tc.modality, modality_strength=tc.modality_strength,
            modality_confidence=tc.modality_confidence,
            subject=tc.subject, exception=tc.exception,
            legal_refs=tc.external_refs, cross_refs=tc.cross_refs,
            is_mandatory=tc.is_mandatory, is_suspicious=tc.is_suspicious,
            page_start=1, page_end=1))

    raw_edges: list[tuple[str, str, str]] = []
    for m in models:
        for ref in m.cross_refs:
            raw_edges.append(("reference_relation", m.clause_number, ref))
    edges = [(t, number_to_id[m.clause_number], number_to_id[ref])
             for t, src, ref in raw_edges
             if src in number_to_id and ref in number_to_id]

    doc_row: dict = {
        "doc_id": doc_id, "standard_no": standard_no, "standard_name": standard_name,
        "short_code": short_code or standard_no.replace("(", "").replace(")", "")[:24],
        "current_revision_id": f"rev_{ULID()}", "doc_type": doc_type,
        "legal_hierarchy": legal_hierarchy, "domain_tags": domain_tags or ["法律"],
        "effective_from": effective_from,
        "file_path": source_marker, "file_hash": file_hash,
        "source_url": source_url}
    # `__default__` 哨兵：**显式**区分"调用方没给"（沿用既有默认）与"调用方要给 NULL"
    # （采集路径就要 NULL ⇒ 效力状态"未知" ⇒ 效力报告显示 ⚪ 而不是 🟢）。
    if legal_status != "__default__":
        doc_row["legal_status"] = legal_status
    if quality_grade != "__default__":
        doc_row["quality_grade"] = quality_grade
    if standard_type != "__default__":
        doc_row["standard_type"] = standard_type
    # 变更信号（2026-09-24，§10.195）：同样用 `__default__` 哨兵——不给 = **不写这列**
    # （保持既有调用方的行为一字不变），给了（含显式 None）= 写 NULL。
    # ⚠ 只有"这份文件是某法规/标准变化的线索"才给值；判定在
    #   `web_ingest.classify_change_signal`（确定性规则，落库即可复算——**不是模型输出**）。
    if change_signal != "__default__":
        doc_row["change_signal"] = change_signal

    with write_transaction() as txn:
        clause_repo.insert_document(txn, doc_row)
        clause_repo.insert_clauses_in_txn(txn, models)
        clause_repo.insert_edges_in_txn(
            txn, [(t, s, d, 0.9, "active") for t, s, d in edges])

    # R8 运维日志：文本直灌入库成功也写 operation_log
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO operation_log (operation, target_type, target_id, detail)"
            " VALUES (?,?,?,?)",
            ("ingest_law_text", "doc", doc_id,
             json.dumps({"standard_no": standard_no, "clauses": len(models)},
                        ensure_ascii=False)))

    return {"status": "ok", "doc_id": doc_id, "total_clauses": len(models),
            "evidence_edges": len(edges)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text_file", type=Path, help="法规纯文本/Markdown 文件")
    ap.add_argument("--standard-no", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--hierarchy", default="法律")
    ap.add_argument("--domain-tags", default="法律")
    args = ap.parse_args(argv)
    if not args.text_file.exists():
        print(json.dumps({"status": "error", "message": f"文件不存在: {args.text_file}"},
                         ensure_ascii=False))
        return 1
    out = ingest_law_text(args.text_file.read_text(encoding="utf-8"),
                          args.standard_no, args.name or args.standard_no,
                          args.hierarchy,
                          [t for t in args.domain_tags.split(",") if t])
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
    sys.stdout.flush()
    os._exit(0 if out.get("status") in ("ok", "duplicate", "standard_exists") else 1)


if __name__ == "__main__":
    sys.exit(main())
