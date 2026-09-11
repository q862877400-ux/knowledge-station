"""高亮 bbox 离屏验证：把 source_span bbox（**底部原点**，v5 契约）画到 PDF 页，对比框内文本是否是该条款。

坐标换算：存储为底部原点（y 向上，页顶文本 y≈页高）→ fitz 为顶部原点（y 向下），
验证时必须 y' = H − y 换算后再取带内文字（2026-08-26 修正：旧版直接按顶部原点画框，
对正确数据必然错位，等于没有验证能力）。

结论判定：框内文本命中条款正文 → bbox 正确（问题在前端）；否则 → 入库 bbox 有问题。
"""
import json
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.storage.sqlite_db import get_db_connection  # noqa: E402


def main() -> None:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT cr.clause_revision_id, cr.clause_number, cr.content_text, dm.file_path"
        " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
        " WHERE cr.clause_number IN ('5.2.1','6.4.2') LIMIT 1").fetchone()
    if row is None:
        print("未找到测试条款")
        return
    pdf = Path(row["file_path"])
    if not pdf.exists():
        print("PDF 不存在:", pdf)
        return
    spans = conn.execute(
        "SELECT page_number, bbox_json FROM source_span WHERE clause_revision_id=?",
        (row["clause_revision_id"],)).fetchall()
    print(f"条款 {row['clause_number']} 来自 {pdf.name}")
    print("条款文本前 30 字:", row["content_text"][:30].replace("\n", " "))
    doc = fitz.open(str(pdf))
    for s in spans:
        pno = s["page_number"]
        bbox = json.loads(s["bbox_json"])
        page = doc[pno - 1]
        h = page.rect.height
        # 底部原点存储 → fitz 顶部原点：y' = H − y（端点交换）
        x0, y0, x1, y1 = [float(v) for v in bbox]
        rect = fitz.Rect(x0, h - y1, x1, h - y0)
        words = page.get_text("words")
        inside = [w[4] for w in words
                  if fitz.Rect(w[:4]).intersects(rect)]
        text_in_box = "".join(inside)[:60]
        print(f"  页{pno} bbox={bbox} → fitz 矩形={tuple(round(v,1) for v in rect)} 框内文本: {text_in_box}")
        # 画框到验证图
        if s is spans[0]:
            page0 = doc[s["page_number"] - 1]
            page0.draw_rect(rect, color=(1, 0, 0), width=2)
    out = Path("var/highlight_verify.png")
    page0.get_pixmap(dpi=120).save(str(out))
    print("验证图:", out)


if __name__ == "__main__":
    main()
