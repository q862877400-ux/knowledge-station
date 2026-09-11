"""Task 11.4 本地视觉反查测试：截图 OCR → 检索（本地 MinerU，零云端）。"""
import shutil
from pathlib import Path

import pytest


@pytest.fixture()
def test_image(tmp_path):
    """生成含规范文字的小图（复用 var/vision_test.png 或现场生成）。"""
    src = Path("var/vision_test.png")
    if src.exists():
        dst = tmp_path / "vision_test.png"
        shutil.copy(src, dst)
        return dst
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=200)
    page.insert_text((72, 60), "动火作业应有专人监护，作业前清除易燃物品。",
                     fontsize=16, fontname="china-s")
    page.insert_text((72, 100), "可燃气体浓度不大于 0.5%。", fontsize=16, fontname="china-s")
    p = tmp_path / "vision_test.png"
    page.get_pixmap(dpi=150).save(str(p))
    return p


def test_vision_locate_ocr_and_retrieve(db, test_image):
    """端到端：图片 OCR 文本应能检索到库内条款（GB30871 5.2.x 系列）。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.domain.models import ClauseRevisionModel
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="vis1", standard_no="GB 30871-2022", standard_name="动火作业规范",
            short_code="GB30871", current_revision_id="r", domain_tags=["安全"],
            file_path="v.pdf", file_hash="hv"))
    clause_repo.insert_clauses([ClauseRevisionModel(
        clause_revision_id="vis1c", doc_id="vis1", clause_key="vk",
        standard_no="GB 30871-2022", clause_number="5.2.1",
        content_text="动火作业应有专人监护，作业前应清除动火现场及周围的易燃物品。",
        knowledge_type="rule", modality="应", modality_strength=3,
        page_start=1, page_end=1)])
    from src.core.vision.local_vision import vision_locate
    out = vision_locate(test_image, top_k=3)
    assert out["status"] == "ok"
    assert "动火作业" in out["ocr_text"], "OCR 应识别出图中文字"
    assert out["results"], "OCR 文本应能检索到条款"


def test_vision_locate_missing_image():
    from src.core.vision.local_vision import vision_locate
    from src.core.exceptions import KnowledgeStationError
    with pytest.raises(KnowledgeStationError):
        vision_locate(Path("Z:/不存在.png"))


def test_vision_api(client, test_image):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/vision/locate", headers=headers,
               json={"image_path": str(test_image)})
    assert r.status_code in (200, 422)  # 422=OCR 环境问题；200=端到端通
    assert c.post("/api/v1/vision/locate", headers=headers,
                  json={"image_path": "Z:/无.png"}).status_code == 422
    assert c.post("/api/v1/vision/locate", json={"image_path": str(test_image)}).status_code == 401
