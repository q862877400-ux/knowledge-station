"""业主合同 ground truth 评测：16 条植入不合理条款的合规审查召回率。

持久化版本（原 var/eval_contract.py）。测试断言版见 tests/test_contract_eval.py，
本脚本用于人工/外部 AI 复评测：
    PYTHONPATH=. .venv/Scripts/python scripts/eval_contract.py [合同md路径]
默认路径 tests/fixtures/rental_contract.md（含附录答案，脚本会自动剥离附录）。
"""
import sys
from pathlib import Path

from src.core.compliance.engine import create_review_task, execute_review

# ground truth: 植入条款的特征串 → 期望 red/yellow（附录 16 条）
GROUND_TRUTH = [
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


def main(contract_path: Path) -> None:
    # 去掉附录部分（附录是给测试者看的答案，不能进审查输入）
    raw = contract_path.read_text(encoding="utf-8")
    content = raw.split("# 附录")[0].split("附录：不合理条款清单")[0]

    out = create_review_task("contract", "业主测试合同", content)
    verdicts = list(execute_review(out["task_id"]))

    hit_red = hit_any = 0
    missed = []
    for key, expect in GROUND_TRUTH:
        matched_v = next((v for v in verdicts if key in v["point_content"]), None)
        if matched_v is None:
            missed.append(f"[未抽到] {key}")
            continue
        hit_any += 1
        if expect == "red":
            if matched_v["verdict"] == "red":
                hit_red += 1
            else:
                missed.append(f"[期望red实际{matched_v['verdict']}] {key}")
        elif expect == "yellow" and matched_v["verdict"] == "green":
            missed.append(f"[期望yellow实际green] {key}")

    n = len(GROUND_TRUTH)
    flagged = sum(1 for k, _ in ((key, exp) for key, exp in GROUND_TRUTH)
                  if (v := next((x for x in verdicts if k in x["point_content"]), None))
                  and v["verdict"] in ("red", "yellow"))
    print(f"审查点总数: {len(verdicts)}")
    print(f"植入条款抽到: {hit_any}/{n}  | 标红正确: {hit_red}/"
          f"{sum(1 for _, e in GROUND_TRUTH if e == 'red')}")
    print(f"风险标出率(red|yellow): {flagged}/{n} = {flagged / n:.0%}")
    if missed:
        print("问题明细:")
        for m in missed:
            print("  -", m)
    counts = {"red": 0, "yellow": 0, "green": 0}
    for v in verdicts:
        counts[v["verdict"]] += 1
    print("总判定分布:", counts)


if __name__ == "__main__":
    default = Path(__file__).resolve().parent.parent / "tests/fixtures/rental_contract.md"
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
