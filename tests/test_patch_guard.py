"""纠错补丁防乱检测（patch guard）测试，2026-08-23 新增。"""
from src.core.verification.patch_guard import check_patch

# 一段典型条款原文
ORIG = ("5.2.1 动火作业应有专人监护,作业前应清除动火现场及周围的易燃物品，"
        "或采取其他有效安全防火措施，并配备足够的消防器材。")


def test_ok_minor_fix():
    """正常 OCR 纠错（局部小改）→ ok。"""
    new = ORIG.replace("专人监护,", "专人监护，")
    out = check_patch(ORIG, new)
    assert out["verdict"] == "ok"


def test_reject_unrelated_paste():
    """贴完全无关内容 → reject。"""
    new = "今天天气不错，适合出去玩。Python is a great programming language!"
    out = check_patch(ORIG, new)
    assert out["verdict"] == "reject"


def test_reject_garbage():
    """大量不可打印字符（乱码/二进制）→ reject。"""
    new = "".join(chr(i) for i in range(1, 32)) * 20
    out = check_patch(ORIG, new)
    assert out["verdict"] == "reject"


def test_warning_length_grow():
    """长度暴增 3 倍以上 → warning（疑似贴了多余内容）。"""
    new = ORIG + "\n" + ("无关的补充内容测试用例数据。" * 20)
    out = check_patch(ORIG, new)
    assert out["verdict"] == "warning"
    assert any("倍" in r for r in out["reasons"])


def test_warning_length_shrink():
    """长度骤减到 1/3 以下 → warning（疑似误删大段）。"""
    new = ORIG[:20]
    out = check_patch(ORIG, new)
    assert out["verdict"] in ("warning", "reject")  # 截断也可能低相似
    assert out["reasons"]


def test_warning_language_shift():
    """中文占比骤降（贴英文代码）→ warning。"""
    new = "5.2.1 hot work shall have dedicated supervision, fire watch, extinguisher ready."
    out = check_patch(ORIG, new)
    assert out["verdict"] in ("warning", "reject")


def test_short_original_skips_similarity():
    """原文太短（<12 字）跳过相似度检查。"""
    out = check_patch("短标题", "全新的一句话内容")
    assert out["verdict"] == "ok"
