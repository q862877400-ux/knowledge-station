"""Task 11.5 Dry-Run 预览测试：解析不落库 + 统计输出。"""
import hashlib
from pathlib import Path


def _make_pdf(tmp_path: Path) -> Path:
    import fitz
    p = tmp_path / "预览.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 80), "5.2.1 动火作业应有专人监护。", fontsize=12, fontname="china-s")
    page.insert_text((72, 110), "5.2.2 可燃气体浓度不大于0.5%。", fontsize=12, fontname="china-s")
    doc.save(str(p))
    doc.close()
    return p


def test_analyze_preview_no_write(db, tmp_path):
    from src.core.ingestion.pipeline import analyze_preview
    p = _make_pdf(tmp_path)
    out = analyze_preview(p)
    assert out["status"] == "ok"
    assert out["total_clauses"] >= 2
    assert set(out["knowledge_type_distribution"]) <= {"rule", "data", "legal"}
    assert "sample" in out
    # 不落库：无 doc_meta 新增
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    n = conn.execute("SELECT COUNT(*) FROM doc_meta WHERE file_hash=?",
                     (hashlib.sha256(p.read_bytes()).hexdigest(),)).fetchone()[0]
    assert n == 0, "Dry-Run 不得落库"


def test_analyze_preview_missing():
    from src.core.ingestion.pipeline import analyze_preview
    assert analyze_preview(Path("Z:/无.pdf"))["status"] == "error"
