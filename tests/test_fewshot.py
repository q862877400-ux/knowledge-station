"""Task 13.4 R17 轻量版测试：负向反馈聚类 → Few-shot 注入。"""
import pytest


def test_fewshot_injection_from_feedback(db):
    from src.core.llm import fewshot
    # 种 4 条负向反馈（2 条模态错误同内容去重、1 条数值错误、1 条条款号错误）
    db.execute(
        "INSERT INTO feedback_log (feedback_id, feedback_type, feedback_content, rating)"
        " VALUES ('f1','modality_error','把应改成了宜，模态强度不对',-1)")
    db.execute(
        "INSERT INTO feedback_log (feedback_id, feedback_type, feedback_content, rating)"
        " VALUES ('f2','modality_error','把应改成了宜，模态强度不对',-1)")
    db.execute(
        "INSERT INTO feedback_log (feedback_id, feedback_type, feedback_content, rating)"
        " VALUES ('f3','number_error','数值 13m 被写成 13.2m',-1)")
    db.execute(
        "INSERT INTO feedback_log (feedback_id, feedback_type, feedback_content, rating)"
        " VALUES ('f4','clause_error','引用了不存在的条款号',-1)")
    db.commit()

    patterns = fewshot.collect_feedback_patterns()
    assert len(patterns) <= 3, "同内容去重"
    assert any(p["type"] == "number_error" for p in patterns)

    prompt = fewshot.inject_fewshot("你是合规助手。")
    assert "用户历史纠错提示" in prompt
    assert "数值 13m" in prompt


def test_fewshot_empty_no_change(db):
    from src.core.llm import fewshot
    db.execute("DELETE FROM feedback_log")
    db.commit()
    assert fewshot.inject_fewshot("原样") == "原样"
