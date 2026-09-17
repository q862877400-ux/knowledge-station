"""R27 入库预览报告（Dry-Run）+ 决策 2 批量分桶——**只读**实现。

## 只读红线（硬约束）
- 不写库、不建表、不动 `doc_meta`/`clause_revision`/`clause_patch`/收藏/批注；
- 不移动、不改写、不复制用户文件（隔离区的移动是正式批量入库 `bulk.fast_scan` 的职责，
  预览只在报告里标 `quarantine_candidate`）；
- 临时解析产物只落在 `settings.data_dir/dryrun/tmp/<sha256[:16]>/`（按文件哈希隔离，
  避免并发预览互相覆盖），24h 后可由运维清理。

## 外发（2026-09-17 由"零外发"改为"默认不外发 + 可显式开启 + 如实标注"）
`parse_pdf_with_mineru` 的深度通道触发条件是 `if not blocks:`（与 `force_deep` 无关），
而深度通道**云优先** → 若预览直接调它，扫描件的 PDF 会被上传到云端解析，而用户以为
"我只是在本地看一眼"。所以：**默认 `deep_fallback=False`**——无文本层就不解析，如实报
`text_layer_state="empty"` + `deep_fallback_skipped=True`（零外发、零 GPU）；调用方**显式**
传 `deep_fallback=True` 才走深度通道，此时报告里的 `egress` **如实标成非 `none`**。

> **为什么改**（业主 2026-09-17 裁定，`ENCYCLOPEDIA` §16.2 **D5**）：原实现把"零外发"做成
> **结构性事实**（函数**不接受** `deep_fallback` 参数），本意是防"有人改默认值导致静默外发"，
> 但那也**永久封死了**扫描件在预览里走深度解析的能力。现行口径：**默认保持安全**（默认值
> 仍是 `False`，且**补上了当年缺的测试网**——断言默认 False 且显式 True 真的透传到解析层），
> 把"能不能外发"的决定权交还调用方并留痕，而不是由结构禁止。

## 与正式入库的一致性纪律
- 分型口径必须与入库一致：预览调 `classify_clause(content, doc_type)` 也**传 doc_type**
  （既有 `analyze_preview` 漏传，法规类文档会全判成 rule → 分型预览准确率无从谈起）。
- 查重语义与 `run_full_ingest` 一致（file_hash 相同 → duplicate；standard_no 相同但
  hash 不同 → standard_exists）。这里是**只读镜像**，不重构生产入库路径。
- 预览文本**永不入库**；`head` 只是 `content_text[:80]` 的展示截断，不做任何归一化
  （证据文本不可变红线）。
"""

from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from typing import Any, Iterable

from src.core.quality.grading import (
    grade_document,
    legal_element_quality,
    one_line_summary,
    typing_quality,
    verdict_document,
)
from src.core.quality.recognition import (
    clause_ocr_confidence,
    measure_skew,
    page_layout_metrics,
    text_layer_metrics,
)
from src.core.quality.grading import THRESHOLDS

__all__ = [
    "PREVIEW_SCHEMA_VERSION",
    "analyze_preview_report",
    "preview_batch",
    "scan_preview_dir",
]

#: 报告结构版本（UI 前向兼容用）
PREVIEW_SCHEMA_VERSION = 1

#: 批量预览的硬上限（同步接口，防单请求内存/payload 膨胀——**不是超时保护**：
#: 单本预览在负载下实测可达 135s。真正的节流是 `sample` 默认 5；全量万级需异步版本）
BATCH_MAX_FILES = 200
BATCH_DEFAULT_SAMPLE = 5
#: 逐条抽样预览条数（前 N / 后 N）
SAMPLE_N = 5
#: 可疑条款清单上限（防 payload 爆炸）
MAX_SUSPECTS = 200
#: head 展示截断（仅展示，绝不入库）
HEAD_CHARS = 80

#: 同一份源文件的解析锁——按哈希**分片**（§10.77）。
#: 为什么是分片而不是"每个目录一把"：后者要为进程见过的**每个文件**留一个锁对象，
#: 万级批量预览就是万级条目（虽然小，但无界）；分片表**内存有界**，且不同文件几乎不撞。
#: 为什么不是"全局一把"：那会把**不同文件**的预览也串起来（批量预览与手动预览互相等），
#: 属于"为了安全把吞吐也一起牺牲"——而这里的风险是**同一目录**的并发写，不是全局状态。
_PARSE_LOCK_STRIPES = 64
_PARSE_LOCKS = [threading.Lock() for _ in range(_PARSE_LOCK_STRIPES)]


def _parse_lock(tmp_dir: Path) -> threading.Lock:
    """取 `tmp_dir` 对应的分片锁（同一目录 → 同一把；不同目录大概率不同把）。"""
    key = hashlib.sha256(str(tmp_dir).encode("utf-8")).digest()
    return _PARSE_LOCKS[int.from_bytes(key[:4], "big") % _PARSE_LOCK_STRIPES]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _looks_like_pdf(path: Path) -> bool:
    """按**内容魔数**判定是不是 PDF（不是只看扩展名）。

    为什么不能只看后缀：DSH 的附件是**无扩展名**的哈希文件（实测库内
    `doc_meta.file_path` 形如 `…/Attachments/files/2026-09-01/1788220822060-cf6fe615`），
    按 `.pdf` 卡会把真实语料整片误拒。同时保留后缀豁免：魔数认不出但后缀是 .pdf 的文件
    仍交给解析器，让它给出**真实的**解析错误，而不是被我们提前拒掉。
    """
    try:
        with path.open("rb") as fh:
            head = fh.read(5)
    except OSError:
        return False
    return head[:5] == b"%PDF-" or path.suffix.lower() == ".pdf"


def _dup_probe(conn: Any, file_hash: str, standard_no: str | None) -> dict[str, Any]:
    """只读查重（语义镜像 `run_full_ingest`）。"""
    row = conn.execute("SELECT doc_id, standard_no FROM doc_meta WHERE file_hash=?",
                       (file_hash,)).fetchone()
    if row:
        return {"kind": "file_hash", "doc_id": row["doc_id"],
                "standard_no": row["standard_no"], "message": "同一文件已入库（哈希相同）"}
    if standard_no:
        same = conn.execute("SELECT doc_id, file_hash FROM doc_meta WHERE standard_no=?",
                            (standard_no,)).fetchone()
        if same and same["file_hash"] != file_hash:
            return {"kind": "standard_no", "doc_id": same["doc_id"], "standard_no": standard_no,
                    "message": f"标准号 {standard_no} 已存在（哈希不同），如需覆盖请先废弃旧文档"}
    return {"kind": "none", "doc_id": None, "standard_no": standard_no, "message": ""}


def _identity_guess(pdf_path: Path) -> dict[str, Any]:
    """标准号/名称猜测：复用既有唯一所有者（`bulk._extract_first_page` + `auto_tag`）。"""
    from src.core.ingestion.bulk import extract_first_page_identity
    from src.core.knowledge.auto_tag import auto_tag

    no, name = extract_first_page_identity(pdf_path)
    guess: dict[str, Any] = {
        "standard_no": {"value": no, "source": "first_page" if no else "", "confidence": 0.9 if no else 0.0},
        "standard_name": {"value": name, "source": "first_page" if name else ""},
        "cover_meta": {},
    }
    try:
        import fitz
        with fitz.open(str(pdf_path)) as doc:
            head = "".join(doc[i].get_text("text") for i in range(min(3, doc.page_count)))[:4000]
        tags = auto_tag(head, filename=pdf_path.name)
        guess["cover_meta"] = {
            "standard_no": getattr(tags, "standard_no", None),
            "effective_from": getattr(tags, "effective_from", None),
            "superseded": getattr(tags, "superseded", None),
            "domain_tags": list(getattr(tags, "domain_tags", []) or []),
        }
        if not guess["standard_no"]["value"] and getattr(tags, "standard_no", None):
            guess["standard_no"] = {"value": tags.standard_no, "source": "cover_text",
                                    "confidence": 0.7}
    except Exception:  # noqa: BLE001 — 元数据猜测失败不影响体检主体
        pass
    return guess


def analyze_preview_report(pdf_path: Path | str, *, doc_type: str = "standard",
                           deep_fallback: bool = False, skew_pages: int = 40,
                           sample_n: int = SAMPLE_N,
                           max_suspects: int = MAX_SUSPECTS) -> dict[str, Any]:
    """生成 R27 入库预览报告。**只读**（默认不外发，见下方 `deep_fallback`）；
    解析异常不抛，转为 status=error + block。

    :param doc_type: 传给分型器的文档类型（standard|law），必须与入库一致
    :param deep_fallback: False（默认）= 无文本层时**不调深度通道**（不外发）；
        True = 允许走云优先的深度通道，报告里 `egress` 会如实变成非 `none`
        （2026-09-17 D5 前的实现恒为 False，且调用方无从开启）
    """
    t0 = time.monotonic()
    path = Path(pdf_path)
    report: dict[str, Any] = {
        "schema_version": PREVIEW_SCHEMA_VERSION,
        "status": "ok",
        "source": {"path": str(path), "file_name": path.name, "file_size": 0, "file_hash": None},
        "pages": 0, "total_clauses": 0, "clauses_dropped_tiny": 0,
        "grade": "C", "grade_reasons": [], "doc_confidence": 0.0,
        "verdict": "warn", "verdict_reasons": [],
        "head_samples": [], "tail_samples": [], "sample": [],
        "ocr_suspects": [], "ocr_suspects_truncated": False,
        "knowledge_type_distribution": {}, "typing_quality": {}, "legal_elements": {},
        "recognition": {"text_layer_state": "", "weird_ratio": 0.0, "cjk_ratio": 0.0,
                        "replacement_ratio": 0.0, "nonprint_ratio": 0.0,
                        "skew_deg": None, "skew_measured": False, "skew_pages_ratio": 0.0,
                        "measured_lines": 0},
        "layout": {}, "collected_signals": {},
        "standard_no_guess": {}, "standard_name_guess": {}, "cover_meta": {},
        "duplicate": {"kind": "none"},
        "quarantine_candidate": False,
        # 请求级：本次预览**是否禁用**了深度通道（默认 True；显式 deep_fallback=True 才 False）
        "deep_fallback_disabled": not deep_fallback,
        # 文档级：这份文档**真的**走到"本该深度分析却被跳过"的分支（无文本层才会 True）
        "deep_fallback_skipped": False,
        # 外发如实标注（2026-09-17 D5）：**保守口径**——只要本次**允许**深度通道就报
        # `deep_channel`，哪怕这份文档恰好有文本层、根本不需要走深度分析。
        # 宁可高报不可漏报：真实外发以 `egress_audit` 落库为准（红线 4 / D2）。
        "egress": "none" if not deep_fallback else "deep_channel",
        "elapsed_ms": 0,
        "error_code": None, "error_message": None, "one_line": "",
    }

    if not path.exists() or not path.is_file():
        report.update(status="error", error_code="file_not_found",
                      error_message=f"文件不存在: {path}")
        return _finalize(report, t0)
    if not _looks_like_pdf(path):
        report.update(status="error", error_code="unsupported_type",
                      error_message=("内容不是 PDF（魔数既非 %PDF- 且后缀也不是 .pdf）"
                                     f"：{path.name}"))
        return _finalize(report, t0)

    report["source"]["file_size"] = path.stat().st_size
    report["source"]["file_hash"] = _sha256_file(path)

    # 身份猜测 + 查重（只读）
    guess = _identity_guess(path)
    report["standard_no_guess"] = guess["standard_no"]
    report["standard_name_guess"] = guess["standard_name"]
    report["cover_meta"] = guess["cover_meta"]
    try:
        from src.core.storage.sqlite_db import get_db_connection
        conn = get_db_connection()
        report["duplicate"] = _dup_probe(conn, report["source"]["file_hash"],
                                        guess["standard_no"]["value"])
    except Exception as e:  # noqa: BLE001 — 查重失败不阻断体检，但要如实说
        report["duplicate"] = {"kind": "unknown", "message": f"查重失败: {type(e).__name__}"}

    # 解析（隔离临时目录 + 明确不调深度通道）
    from src.core.config import get_settings
    from src.core.ingestion.parser_worker import run_parser_isolated
    tmp_dir = (get_settings().data_dir / "dryrun" / "tmp"
               / str(report["source"]["file_hash"])[:16])
    # ⚠ **同一份源文件的解析必须串行**（§10.77，§10.73 登记的连带风险）：
    # 临时目录按**源文件哈希**命名 ⇒ 同一文件的两个并发预览会写同一个目录；显式走深通道时
    # 那个落地目录还会被**读回**（`layout.json` + `images/`）⇒ 理论上有撕裂读。
    # 默认路径（`deep_fallback=False`）只写不读、且同一哈希的输入**逐字节相同**，所以危害
    # 查不出来；但并发**本来就有**（jobs 的 worker 线程 vs 同步请求），§10.73 把预览端点改成
    # `def` 之后更宽（两次点击即可）。这里按哈希**分片**加锁：同文件串行、不同文件照常并行。
    with _parse_lock(tmp_dir):
        try:
            parsed = run_parser_isolated(path, tmp_dir, force_deep=False,
                                         deep_fallback=deep_fallback)
        except Exception as e:  # noqa: BLE001 — 解析失败是"可判定的坏文档"，转 block
            code = "parser_error"
            name = type(e).__name__
            if "Timeout" in name:
                code = "parser_timeout"
            report.update(status="error", error_code=code,
                          error_message=f"{name}: {e}")
            return _finalize(report, t0)

    blocks = parsed.get("blocks") or []
    geometries = parsed.get("geometries") or {}
    report["deep_fallback_skipped"] = bool(parsed.get("deep_fallback_skipped"))
    report["recognition"]["text_layer_state"] = str(parsed.get("text_layer_state") or "")

    # 度量
    tlm = text_layer_metrics(blocks)
    report["recognition"].update({
        "weird_ratio": round(tlm.weird_ratio, 6),
        "cjk_ratio": round(tlm.cjk_ratio, 6),
        "replacement_ratio": round(tlm.replacement_ratio, 6),
        "nonprint_ratio": round(tlm.nonprint_ratio, 6),
    })
    try:
        skew = measure_skew(path, max_pages=skew_pages)
        report["recognition"].update({
            "skew_deg": skew.skew_deg, "skew_measured": skew.measured,
            "skew_pages_ratio": round(skew.skew_pages_ratio, 4),
            "measured_lines": skew.measured_lines,
        })
    except Exception:  # noqa: BLE001 — 测斜失败不影响其余判据（measured=False 即"未测"）
        report["recognition"]["skew_measured"] = False

    # 建条：**复用生产入库的建条实现**（`build_clause_models` 是纯函数，不写库）。
    #
    # 为什么必须复用而不是自己 join texts（verifier 审计 P0-3 的根因）：
    # ① 入库的 content_text 经过**家具剥离 / 4000 字截断 / <4 守卫豁免（表格/插图/章头）**，
    #    自己 `"\n".join(cl.texts)` 会让"预览看到的条款"≠"真正入库的条款"，
    #    分型预览准确率与条款数都失去意义；
    # ② 框线表格重建（`_extract_vector_table_items` + `_merge_table_items`）也在这一层，
    #    不复用它 → 预览**结构上**拿不到 `content_markdown` → 6 个体检标签里 3 个表格标签
    #    在预览里恒为 0（把判据抽成唯一所有者也白搭）。注：某张表最终能否**绑到条款**
    #    （从而出现在 content_markdown 里）取决于上游切分器的题注绑定规则，与入库完全同源；
    #    预览这一层只保证不丢信息（见 tests/test_dryrun_report.py 的两层用例）；
    # ③ 分型与法理要素（subject/exception/cross_refs/legal_refs）都由它**在同一处**产出，
    #    预览再调一次 classify_clause 就是第二套口径。
    from src.core.ingestion.pipeline import (_extract_vector_table_items,
                                             _merge_table_items,
                                             build_clause_models,
                                             load_middle_items_from_blocks,
                                             split_items_into_clauses)
    o_blocks = [b for b in blocks if b.get("text")]
    try:
        tbl_items, drop_idx = _extract_vector_table_items(
            path, o_blocks, is_ocr=bool(parsed.get("is_ocr")))
    except Exception:  # noqa: BLE001 — 表格重建失败不阻断预览（少一类标签也要如实出报告）
        tbl_items, drop_idx = [], set()
    if drop_idx:
        o_blocks = [b for i, b in enumerate(o_blocks) if i not in drop_idx]
    items, _ = load_middle_items_from_blocks(o_blocks)
    if tbl_items:
        items = _merge_table_items(items, tbl_items)
    page_sizes = {int(k) - 1: (float(v["width"]), float(v["height"]))
                  for k, v in geometries.items()}
    # 2026-09-17：把（猜出的）标准号也传给切分层 —— 让预览与真入库在"家具剥离"上
    # 同口径（真入库用已确认的标准号；预览只能用猜测值，猜不出则 None = 历史行为）。
    # ⚠ 占位符 `"未知标准号"` **不能**传给切分层：`_own_key_of` 要求标准号含数字，
    #   占位符会被挡回 None（否则等于把家具剥离整体关掉）。
    _guess_no = guess["standard_no"]["value"] or None
    split = split_items_into_clauses(items, standard_no=_guess_no)
    standard_no_for_key = _guess_no or "未知标准号"
    models, _raw_edges = build_clause_models("preview", standard_no_for_key,
                                             doc_type, split, page_sizes)

    clauses: list[dict[str, Any]] = []
    for ordinal, m in enumerate(models):
        content = m.content_text or ""
        conf, reasons = clause_ocr_confidence(
            content, page_skew_deg=report["recognition"].get("skew_deg"),
            is_tiny=len(content.strip()) < 10)
        clauses.append({
            "ordinal": ordinal, "number": m.clause_number,
            "page_start": m.page_start, "page_end": m.page_end,
            "text_len": len(content),
            "head": content[:HEAD_CHARS],
            "knowledge_type": m.knowledge_type,
            "type_confidence": m.type_confidence,
            "modality": m.modality,
            "modality_strength": m.modality_strength,
            "modality_confidence": m.modality_confidence,
            "subject": bool(m.subject), "exception": bool(m.exception),
            "cross_refs_count": len(m.cross_refs or []),
            "external_refs_count": len(m.legal_refs or []),
            "suspicious": bool(m.is_suspicious),
            "ocr_confidence": conf,
            "reasons": reasons,
        })

    report["total_clauses"] = len(clauses)
    report["clauses_dropped_tiny"] = max(0, len(split) - len(models))
    report["pages"] = len(geometries)
    lay = page_layout_metrics(geometries, blocks, total_clauses=len(clauses))
    report["layout"] = {
        "pages": lay.pages, "chars": tlm.chars,
        "chars_per_page": round(lay.chars_per_page, 2),
        "pages_no_text": lay.pages_no_text,
        "pages_no_text_ratio": round(lay.pages_no_text_ratio, 4),
        "clauses_per_1000chars": round(lay.clauses_per_1000chars, 3),
        "rotation_anomaly_pages": lay.rotation_anomaly_pages,
        "page_size_outliers": lay.page_size_outliers,
        "blocks": tlm.blocks,
        "tables_rebuilt": len(tbl_items),
    }

    dist: dict[str, int] = {}
    for c in clauses:
        dist[c["knowledge_type"]] = dist.get(c["knowledge_type"], 0) + 1
    report["knowledge_type_distribution"] = dist
    report["typing_quality"] = typing_quality(clauses, doc_type=doc_type)
    report["legal_elements"] = legal_element_quality(clauses)

    # 样例（前 N / 后 N）+ 可疑清单（R27：置信度 < 0.85）+ 体检标签聚合
    report["head_samples"] = clauses[:sample_n]
    # 条款数 ≤ N 时尾部样本退回「全部」，不给空数组（否则 UI 会显示"后 0 条"）
    report["tail_samples"] = (clauses[-sample_n:] if len(clauses) > sample_n
                              else list(clauses))
    report["sample"] = clauses[:10]  # 兼容 analyze_preview 的老字段语义
    suspects = [c for c in clauses if c["ocr_confidence"] < THRESHOLDS["suspect_confidence"]]
    report["ocr_suspects_truncated"] = len(suspects) > max_suspects
    report["ocr_suspects"] = suspects[:max_suspects]

    from src.core.quality import clause_health
    signals: dict[str, int] = {}
    table_anomalies: list[str] = []
    for m in models:
        health = clause_health(m.content_text or "", m.content_markdown)
        for tag in health.tags:
            signals[tag] = signals.get(tag, 0) + 1
        if "表格列数不一致" in health.tags or "表格脏单元格" in health.tags:
            table_anomalies.append(m.clause_number)
    report["collected_signals"] = dict(signals)
    report["collected_signals"]["table_anomaly_clauses"] = table_anomalies[:50]

    confs = [c["ocr_confidence"] for c in clauses]
    report["doc_confidence"] = (sorted(confs)[len(confs) // 2] if confs else 0.0)

    # verdict_document 返回 (str, list[dict])，与上方 clause 级 reasons（list[str]）同名不同物
    verdict, doc_reasons = verdict_document(report)
    report["verdict"] = verdict
    report["verdict_reasons"] = doc_reasons
    grade, grade_reasons = grade_document(verdict, report["doc_confidence"])
    report["grade"] = grade
    report["grade_reasons"] = grade_reasons
    report["quarantine_candidate"] = verdict == "block"
    return _finalize(report, t0)


def _finalize(report: dict[str, Any], t0: float) -> dict[str, Any]:
    """统一收尾：补 elapsed、一行摘要，并在 status=error 时强制走 verdict 判据。"""
    report["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
    if report.get("status") == "error":
        verdict, reasons = verdict_document(report)
        report["verdict"] = verdict
        report["verdict_reasons"] = reasons
        grade, grade_reasons = grade_document(verdict, 0.0)
        report["grade"] = grade
        report["grade_reasons"] = grade_reasons
        report["quarantine_candidate"] = verdict == "block"
    report["one_line"] = one_line_summary(report)
    return report


def scan_preview_dir(directory: Path | str, *, recursive: bool = False,
                     limit: int = BATCH_MAX_FILES) -> list[Path]:
    """列出目录下的候选 PDF（字典序，确定性）。"""
    d = Path(directory)
    if not d.is_dir():
        raise NotADirectoryError(str(d))
    it = d.rglob("*.pdf") if recursive else d.glob("*.pdf")
    files = sorted((p for p in it if p.is_file()), key=lambda p: str(p).lower())
    return files[:limit]


def _stride_sample(items: list[Path], n: int) -> list[Path]:
    """确定性等距抽样（不用随机，便于测试精确断言与复现）。

    n<=0 或 n>=len → 全部（`sample=0` 表示"不抽样"）。"""
    if n <= 0 or n >= len(items):
        return list(items)
    if n == 1:
        return [items[0]]
    step = (len(items) - 1) / (n - 1)
    picked = {items[round(i * step)] for i in range(n)}
    return sorted(picked, key=lambda p: str(p).lower())


def preview_batch(paths: Iterable[Path | str], *, sample: int = BATCH_DEFAULT_SAMPLE,
                  doc_type: str = "standard", deep_fallback: bool = False,
                  limit_files: int = BATCH_MAX_FILES) -> dict[str, Any]:
    """批量 Dry-Run（决策 2：总账分桶 ✅/⚠️/❌，⚠️ 集中处理；新语料源先抽样几本）。

    **单文件失败不中断整批**（逐件 try，沿用 `bulk.parse_loop` 的既有范式）。
    只读：不写库、不落文件账本（账本是异步版本的事，见台账已知缺口）。

    **外发口径（2026-09-17 D5 修订）**：`deep_fallback` **默认 `False`** ⇒ 批量路径
    **默认不外发**（无文本层就不解析，如实报 `deep_fallback_skipped=True`）；调用方显式传
    `True` 才允许走云优先的深度通道，此时每件的 `egress` 会如实标成 `deep_channel`。

    历史（保留以防重犯）：2026-09-11 verifier 审计 P0-2 曾**要求删掉**这个参数——理由是
    "原先留了一个没人传的死参数，一旦有人改默认值就会静默外发，而批量侧没有任何测试网"。
    删参数能消除风险，但代价是**永久封死**该能力。D5 后改为**把缺的那张网补上**：
    `tests/test_dryrun_batch.py` 同时断言①**默认必须为 False**（防静默外发）
    ②**显式 True 必须真的透传**到 `analyze_preview_report`（防"参数加了却不接线"）。
    ⇒ 安全性质由**测试**保证，而不是由"函数不接受该参数"保证。
    """
    t0 = time.monotonic()
    all_paths = [Path(p) for p in paths]
    total = len(all_paths)
    limit_files = max(0, min(int(limit_files), BATCH_MAX_FILES))
    truncated = total > limit_files
    candidates = all_paths[:limit_files]
    sampled = _stride_sample(candidates, sample)

    buckets: dict[str, list[dict[str, Any]]] = {"ok": [], "warn": [], "block": []}
    files: list[dict[str, Any]] = []
    for p in sampled:
        try:
            # 透传调用方的决定（默认 False ⇒ 默认不外发，见 docstring）
            rep = analyze_preview_report(p, doc_type=doc_type, deep_fallback=deep_fallback)
        except Exception as e:  # noqa: BLE001 — 单件崩溃不得中断整批
            rep = {"status": "error", "error_code": "unexpected", "verdict": "block",
                   "error_message": f"{type(e).__name__}: {e}", "grade": "D",
                   "total_clauses": 0, "layout": {"pages": 0}, "ocr_suspects": [],
                   "typing_quality": {"distribution": {}},
                   "verdict_reasons": [{"code": "B8", "reason": "未预期异常"}],
                   "source": {"file_name": p.name, "path": str(p)}}
        row = {
            "path": str(p), "file_name": p.name,
            "verdict": rep.get("verdict"), "grade": rep.get("grade"),
            "pages": rep.get("pages", 0), "total_clauses": rep.get("total_clauses", 0),
            "doc_confidence": rep.get("doc_confidence", 0.0),
            "one_line": rep.get("one_line") or one_line_summary(rep),
            "reasons": [r.get("code") for r in (rep.get("verdict_reasons") or [])][:4],
            "error": rep.get("error_message"),
        }
        files.append(row)
        buckets.setdefault(str(row["verdict"] or "block"), []).append(row)

    counts = {k: len(v) for k, v in buckets.items()}
    return {
        "total_candidates": total,
        "truncated": truncated,
        "limit_files": limit_files,
        "sampled": len(sampled),
        "unprocessed": max(0, len(candidates) - len(sampled)),
        "evaluated": len(files),
        "sample_requested": sample,
        "buckets": counts,
        "by_bucket": buckets,
        "files": files,
        "conservation_ok": counts["ok"] + counts["warn"] + counts["block"] == len(files),
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "doc_type": doc_type,
        # 批量总账的外发标注（与每件报告同口径，2026-09-17 D5）：默认 none；
        # 只要本次允许深度通道就如实标成 deep_channel（保守高报，见 analyze_preview_report）。
        "egress": "none" if not deep_fallback else "deep_channel",
    }
