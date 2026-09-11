"""法规入库编排（方案 §4/§5）：官方源 → docx → PDF → 现有 run_full_ingest 管线。

主路径与标准件完全同构（预览/高亮/目录/条款修正复用既有链路）；
docx 解析仅用于：无转换器时的直解降级 + 元数据溯源。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import get_settings
from src.core.knowledge.law_source import convert
from src.core.knowledge.law_source import flk_client as flk
from src.core.knowledge.law_source import govcn_client as govcn
from src.core.storage import clause_repo
from src.core.storage.sqlite_db import get_db_connection, write_transaction

# flk 分类(flxz) → 法规树 L2 效力等级（LAW_LEVELS 词汇表，未列出的落"其他法规"）
FLK_LEVEL_MAP = {
    "宪法": "宪法",
    "法律": "法律",
    "行政法规": "行政法规",
    "监察法规": "行政法规",
    "军事法规": "行政法规",
    "司法解释": "司法解释",
    "地方性法规": "地方性法规",
    "部门规章": "部门规章",
}
DEFAULT_LEVEL = "其他法规"

_SAFE = re.compile(r"[^\w\-.()（）]", re.U)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def law_source_dir(source: str, source_id: str) -> Path:
    return get_settings().data_dir / "law_source" / source / _SAFE.sub("_", source_id)


def ensure_schema() -> None:
    """幂等迁移：doc_meta 增加官方来源溯源列（新库 schema.sql 已含）。"""
    clause_repo.ensure_law_source_columns()


def _write_meta(source_dir: Path, meta: dict) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _update_doc_source(doc_id: str, *, source: str, source_id: str, url: str,
                       downloaded_at: str, source_status: str | None) -> None:
    with write_transaction() as txn:
        txn.execute(
            "UPDATE doc_meta SET source=?, source_id=?, source_url=?, downloaded_at=?,"
            " source_status=? WHERE doc_id=?",
            (source, source_id, url, downloaded_at, source_status, doc_id))


def _ingest(docx_path: Path, *, standard_no: str, standard_name: str,
            domain_tags: list[str], legal_hierarchy: str,
            reingest: bool, source: str, source_id: str, source_url: str,
            source_status: str | None, content_origin: str = "official") -> dict:
    """docx → PDF（缓存复用）→ 现有管线入库；无转换器走 docx 直解降级。"""
    ensure_schema()
    source_dir = docx_path.parent
    pdf_path = source_dir / "source.pdf"
    converter = ""
    # 缓存 PDF 必须通过完整性校验（LibreOffice 截断产物不得复用）
    if pdf_path.exists() and pdf_path.stat().st_size > 0 \
            and convert.pdf_completeness(docx_path, pdf_path):
        converter = "cached-pdf"
    else:
        converter = convert.convert_docx_to_pdf(
            docx_path, pdf_path, prefer=("com" if content_origin == "web" else "libreoffice"))

    if converter:
        from src.core.ingestion.pipeline import run_full_ingest
        out = run_full_ingest(pdf_path, standard_no, standard_name,
                              doc_type="法律法规", legal_hierarchy=legal_hierarchy,
                              domain_tags=domain_tags, reingest=reingest)
    else:
        from src.core.ingestion.docx_ingest import run_docx_ingest
        out = run_docx_ingest(docx_path, standard_no, standard_name,
                              doc_type="法律法规", legal_hierarchy=legal_hierarchy,
                              domain_tags=domain_tags)

    downloaded_at = _now_iso()
    if out.get("status") == "ok":
        _update_doc_source(out["doc_id"], source=source, source_id=source_id,
                           url=source_url, downloaded_at=downloaded_at,
                           source_status=source_status)
    _write_meta(source_dir, {
        "source": source, "source_id": source_id, "source_url": source_url,
        "standard_no": standard_no, "standard_name": standard_name,
        "content_origin": content_origin, "downloaded_at": downloaded_at,
        "source_status": source_status, "converter": converter,
        "docx": str(docx_path), "pdf": str(pdf_path) if pdf_path.exists() else None,
        "ingest": out,
    })
    return {**out, "source": source, "source_id": source_id,
            "source_url": source_url, "downloaded_at": downloaded_at,
            "converter": converter, "docx_path": str(docx_path),
            "pdf_path": str(pdf_path) if pdf_path.exists() else None}


# ---------------------------------------------------------------------------
# flk.npc.gov.cn
# ---------------------------------------------------------------------------

def ingest_law_from_flk(bbbs: str, *, standard_no: str | None = None,
                        standard_name: str | None = None,
                        domain_tags: list[str] | None = None,
                        reingest: bool = False) -> dict:
    """按 bbbs 从国家法律法规数据库下载官方 docx → 转 PDF → 入库。"""
    d = flk.detail(bbbs)
    if not d.title:
        return {"status": "error", "message": f"flk 详情无标题: bbbs={bbbs}"}
    source_id = bbbs
    source_dir = law_source_dir("flk", source_id)
    source_dir.mkdir(parents=True, exist_ok=True)
    docx_path = source_dir / "source.docx"
    if not docx_path.exists():
        try:
            flk.download(bbbs, docx_path, fmt="docx")
        except Exception as e:
            return {"status": "error", "message": f"flk 下载 docx 失败: {e}"}
    return _ingest(
        docx_path,
        standard_no=standard_no or d.title,
        standard_name=standard_name or d.title,
        domain_tags=domain_tags or [],
        legal_hierarchy=FLK_LEVEL_MAP.get(d.flxz, DEFAULT_LEVEL),
        reingest=reingest, source="flk", source_id=source_id,
        source_url=f"https://flk.npc.gov.cn/detail?id={bbbs}",
        source_status=str(d.sxx) if d.sxx is not None else None,
        content_origin="official")


# ---------------------------------------------------------------------------
# gov.cn 政策文件库
# ---------------------------------------------------------------------------

_CRUMB_RE = re.compile(r"^\s*(首页\s*[>›»]\s*.*|字号[:：]\s*.*|默认.*超大\s*[|｜].*|打印.*分享.*|收藏.*打印.*)\s*$")
_CLAUSE_RE = re.compile(r"^第[一二三四五六七八九十百千零]+[条款条目]\s*")
_CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百千零]+[章节编]\s*")


def _build_docx_from_html(source_dir: Path, g: govcn.GovDetail) -> Path:
    """兜底：详情页无官方下载链接时，用正文 HTML 生成 docx（仍记官方来源 URL）。

    按 第X章/第X条 切分段落（公报正文常为连续长文，不切分则 MinerU 无法拆条款）；
    清洗面包屑/字号/打印等导航噪声。content_origin="web" 由调用方标记。
    """
    from docx import Document
    source_dir.mkdir(parents=True, exist_ok=True)
    doc = Document()
    if g.title:
        doc.add_heading(g.title, level=0)
    lines = []
    for raw in (g.content_text or "").splitlines():
        line = " ".join(raw.split())
        if not line or _CRUMB_RE.match(line):
            continue
        lines.append(line)
    # 按行切分：第X章/第X条 开头的行独立成段，其余并入当前段
    # （公报正文常为无空行的连续长文，按"块"切分会导致整篇并成一段 → MinerU 无法拆条款）
    current: list[str] = []
    for line in lines:
        if _CLAUSE_RE.match(line) or _CHAPTER_RE.match(line):
            if current:
                doc.add_paragraph(" ".join(current))
                current = []
            doc.add_paragraph(line)
        else:
            current.append(line)
    if current:
        doc.add_paragraph(" ".join(current))
    docx_path = source_dir / "source.docx"
    doc.save(str(docx_path))
    return docx_path


def ingest_law_from_govcn(url: str, *, standard_no: str | None = None,
                          standard_name: str | None = None,
                          domain_tags: list[str] | None = None,
                          reingest: bool = False,
                          legal_hierarchy: str = "部门规章") -> dict:
    """按详情页 URL 从国务院政策文件库下载官方 docx → 转 PDF → 入库。

    政策库收录国务院文件（行政法规级别）与部门文件（部门规章）；详情页
    source 字段常为空（公报页），默认按部门规章处理，可显式覆盖。
    """
    g = govcn.fetch_detail(url)
    if not g.title and not g.content_text:
        return {"status": "error", "message": f"gov.cn 详情页解析为空: {url}"}
    source_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    source_dir = law_source_dir("govcn", source_id)
    source_dir.mkdir(parents=True, exist_ok=True)
    docx_path = source_dir / "source.docx"
    content_origin = "official"
    if not docx_path.exists():
        if g.download_urls:
            try:
                docx_path = govcn.download(source_dir, g.download_urls[0], referer=url)
            except Exception as e:
                return {"status": "error", "message": f"gov.cn 下载失败: {e}"}
        else:
            docx_path = _build_docx_from_html(source_dir, g)
            content_origin = "web"
    name = standard_name or g.title or url
    return _ingest(
        docx_path,
        standard_no=standard_no or name,
        standard_name=name,
        domain_tags=domain_tags or [],
        legal_hierarchy=legal_hierarchy,
        reingest=reingest, source="govcn", source_id=source_id,
        source_url=url, source_status=None, content_origin=content_origin)


def find_by_source(source: str, source_id: str) -> dict | None:
    """按来源幂等键查库内文档（供重复导入/更新检测）。"""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT doc_id, standard_no, standard_name, file_path, downloaded_at"
        " FROM doc_meta WHERE source=? AND source_id=?",
        (source, source_id)).fetchone()
    return dict(row) if row else None
