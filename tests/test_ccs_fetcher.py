"""CCS 自动分类查询测试（2026-08-23 新增）。"""
import pytest


def test_ccs_to_tag_fallback_local():
    """网络不可用时回退本地映射表（不阻塞入库）。"""
    from src.core.knowledge.ccs_fetcher import ccs_to_tag
    # 无网络结果 → 本地表兜底
    tag = ccs_to_tag(None, "GB 30871-2022")
    assert tag is not None and tag.startswith("CCS:")
    assert "C65" in tag
    # 未收录标准 → None
    assert ccs_to_tag(None, "GB 99999-9999") is None


def test_ccs_to_tag_live_result():
    """有网络结果 → 用实时 CCS。"""
    from src.core.knowledge.ccs_fetcher import ccs_to_tag
    tag = ccs_to_tag({"code": "P16", "major": "P", "sub": "工程防火"}, "GB 55037-2022")
    assert tag == "CCS:P16 工程防火"


def test_classify_uses_ccs_tag():
    """分类优先用 domain_tags 的 CCS 标签（4 级树）。"""
    from src.core.knowledge.doc_catalog import classify_document
    cl = classify_document({
        "standard_no": "GB 55037-2022", "standard_name": "建筑防火通用规范",
        "doc_type": "standard", "legal_hierarchy": "GB",
        "domain_tags": ["CCS:P16 工程防火", "消防"],
    })
    assert cl["top"] == "std" and cl["top_name"].startswith("国家标准")
    assert cl["level2"] == "P 土木、建筑"
    assert "P15/19" in cl["level3"]          # 区间
    assert cl["level4"].startswith("P16")    # 具体类目
    # 无标签 → 兜底
    cl2 = classify_document({
        "standard_no": "GB 99999-9999", "standard_name": "x",
        "doc_type": "standard", "legal_hierarchy": "GB", "domain_tags": [],
    })
    assert cl2["top"] == "std"


def test_law_classify_levels():
    """法规分类（三级体系《法律法规分类编码体系》）：效力层级 → 法律部门 → 业务领域。"""
    from src.core.knowledge.doc_catalog import classify_document
    cl = classify_document({
        "standard_no": "消防法(2021修正全本)", "standard_name": "消防法",
        "doc_type": "法律法规", "legal_hierarchy": "法律",
        "domain_tags": ["消防", "法律"],
    })
    assert cl["top"] == "law"
    assert cl["level2"] == "法律（狭义）"          # 第一级效力层级（12 类）
    assert cl["level3"] == "宪法与行政法"          # 第二级法律部门（A~G；消防→公安/行政）
    assert cl["level4"] == "未细分"                # 第三级业务领域（消防被领域黑名单过滤 → 未细分）
