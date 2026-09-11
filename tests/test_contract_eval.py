"""业主合同 ground truth 永久回归：16 条植入不合理条款的审查召回（阶段3 评测基准）。"""
import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def contract_eval_db(_isolate_data_dir):
    """种入民法典节选（法条文本直灌通道）。"""
    from src.core.storage.sqlite_db import init_schema
    from src.core.ingestion.law_text import ingest_law_text
    init_schema()
    out = ingest_law_text(
        (FIXTURES / "民法典节选.txt").read_text(encoding="utf-8"),
        "民法典(回归)", "中华人民共和国民法典(节选)", "法律", ["合同", "租赁"])
    assert out["status"] == "ok"
    yield


def test_contract_ground_truth(contract_eval_db):
    from src.core.compliance.engine import create_review_task, execute_review

    raw = (FIXTURES / "rental_contract.md").read_text(encoding="utf-8")
    content = raw.split("# 附录")[0]
    out = create_review_task("contract", "回归合同", content)
    verdicts = list(execute_review(out["task_id"]))

    ground_truth = [
        ("续租时租金由甲方根据市场情况重新确定", "red"),
        ("每逾期一日按月租金的10%支付违约金", "red"),
        ("未住满12个月押金一律不退", "red"),
        ("押金在乙方退房后30个工作日内退还", "yellow"),
        ("不得在房屋内怀孕、生产及坐月子", "red"),
        ("甲方一律不承担责任，均由乙方自行承担", "red"),
        ("应按原价三倍赔偿", "red"),
        ("已付租金、押金及所有费用一律不予退还", "red"),
        ("还应额外支付两个月租金作为违约金", "yellow"),
        ("有权提前解除合同收回房屋，且不承担任何违约责任", "red"),
        ("每季度调整一次租金", "red"),
        ("全年物业管理费", "yellow"),
        ("水电费按", "yellow"),
        ("全年维修费", "yellow"),
        ("由甲方所在地人民法院管辖", "yellow"),
        ("本合同最终解释权归甲方所有", "red"),
    ]
    captured = red_correct = flagged = 0
    misses = []
    for key, expect in ground_truth:
        v = next((x for x in verdicts if key in x.get("point_content", "")), None)
        if v is None:
            misses.append(key)
            continue
        captured += 1
        if v["verdict"] in ("red", "yellow"):
            flagged += 1
        if expect == "red":
            if v["verdict"] == "red":
                red_correct += 1
            else:
                misses.append(f"{key}→{v['verdict']}")
    # 基准：全部抽到、标红精确、至少 15/16 标出风险（允许 1 条误判绿）
    assert captured == 16, f"植入条款抽取遗漏: {misses}"
    assert red_correct == 10, f"标红不精确: {misses}"
    assert flagged >= 15, f"风险标出不足: {flagged}/16"
