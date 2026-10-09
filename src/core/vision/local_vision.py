"""本地视觉反查（Task 11.4 落地为本地版，替代云端视觉 API）：
截图/图纸 → RapidOCR（本地单图毫秒级，零外发零预算）→ 失败回退 MinerU
图片 OCR（模型级精度）→ 文本 → 混合检索 → 条款定位。

方向纠正（扫描页 180°）同理：OCR 自带方向分类，或对页面旋转 4 角度取
OCR 文本置信度最高者——由入库管线在无文本层页面触发（本模块提供 locate
供截图反查）。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import subprocess
from pathlib import Path

from src.core.config import get_settings
from src.core.exceptions import KnowledgeStationError

logger = logging.getLogger(__name__)


def _ocr_worker(image_path: str, out_dir: str, result_queue) -> None:  # noqa: ANN001
    """子进程：调 mineru CLI 对图片 OCR（list args，无 shell）。"""
    try:
        mineru = _find_mineru_exe()
        proc = subprocess.run(
            [str(mineru), "-p", image_path, "-o", out_dir, "-b", "pipeline", "-m", "ocr"],
            capture_output=True, timeout=300)
        result_queue.put(("ok", proc.returncode))
    except Exception as e:  # noqa: BLE001
        result_queue.put(("error", f"{type(e).__name__}: {e}"))


def _find_mineru_exe() -> Path:
    import shutil
    exe = shutil.which("mineru")
    if exe:
        return Path(exe)
    # venv Scripts 内
    cand = Path(__file__).resolve().parents[3] / ".venv" / "Scripts" / "mineru.exe"
    if cand.exists():
        return cand
    raise KnowledgeStationError("mineru 不可用（pip install mineru）", code="mineru_missing")


def ocr_image_locally(image_path: Path, out_dir: Path) -> Path:
    """图片 OCR → 返回 markdown 文本路径（mp 子进程隔离 + 超时）。"""
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = ctx.Process(target=_ocr_worker, args=(str(image_path), str(out_dir), q))
    proc.start()
    try:
        status, payload = q.get(timeout=360)
    except Exception as e:
        if proc.is_alive():
            proc.terminate()
        proc.join()
        raise KnowledgeStationError(f"图片 OCR 超时: {e}", code="vision_timeout") from e
    proc.join(timeout=30)
    if status == "error":
        raise KnowledgeStationError(f"图片 OCR 失败: {payload}", code="vision_ocr_failed")
    # mineru 输出 md 位置：out_dir/<stem>/<method>/<stem>.md
    md_candidates = sorted(out_dir.rglob("*.md"))
    if not md_candidates:
        raise KnowledgeStationError("OCR 未产出文本", code="vision_no_output")
    return md_candidates[0]


def _rapidocr_text(image_path: Path) -> str:
    """RapidOCR 单图文本（行序拼接）；依赖 rapidocr_onnxruntime。"""
    from src.core.figure_redraw import get_ocr
    result, _elapse = get_ocr()(str(image_path))
    if not result:
        return ""
    return "\n".join(str(item[1]) for item in result if len(item) >= 2)


def ocr_image_text(image_path: Path, out_dir: Path | None = None) -> str:
    """图片 OCR 文本：**本地 RapidOCR 优先**（单图毫秒级，零外发零预算），
    不可用（未装包/首载失败）或空结果回退本地 MinerU（模型级精度）。

    2026-09-01 架构反转：云通道从本链路退役——截图反查属用户主动操作，
    本模块全程本地执行、零外发。
    """
    try:
        text = _rapidocr_text(image_path)
        if text.strip():
            logger.info("vision_ocr RapidOCR 成功 text_len=%d", len(text))
            return text
    except Exception as e:  # noqa: BLE001 - RapidOCR 不可用不阻塞，回退本地 MinerU
        logger.warning("vision_ocr RapidOCR 不可用回退本地 MinerU: %s", e)
    out = out_dir or (get_settings().data_dir / "vision_tmp" / image_path.stem)
    md = ocr_image_locally(image_path, out)
    text = md.read_text(encoding="utf-8").strip()
    logger.info("vision_ocr 本地 MinerU 回退 text_len=%d", len(text))
    return text


def vision_locate(image_path: Path, top_k: int = 5) -> dict:
    """截图反查：OCR 文本（RapidOCR 优先 → 本地 MinerU 回退）→ 混合检索 → 条款。"""
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    out_dir = get_settings().data_dir / "vision_tmp" / image_path.stem
    text = ocr_image_text(image_path, out_dir)
    if not text:
        return {"status": "ok", "ocr_text": "", "results": []}
    # 文本过长时取首段 + 关键句
    query = text[:400]
    # `rerank` 显式写 False —— 理由与 `src/core/api/server.py` 主问答路径那处**同一条**
    # （总纲 P0·0.7 修好前后保持逐位等价；实测见 `eval/recall-funnel/exp-11-rerank-fix/`）。
    results = perform_hybrid_search(query, top_k=top_k, rerank=False)
    return {"status": "ok", "ocr_text": text[:300],
            "results": [
                {"clause_revision_id": r.clause_revision_id,
                 "standard_no": r.standard_no, "clause_number": r.clause_number,
                 "modality": r.modality, "content_text": (r.content_text or "")[:200]}
                for r in results]}
