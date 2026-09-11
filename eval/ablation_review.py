"""消融·审查场景：16 条植入条款 ground truth 在 behavior_scope 开/关下的召回对比。

Task 10.3：通道消融必须分"问答/审查"两组判定（ROADMAP 10.3 明确）。
输出：两组数据（red 命中数 / yellow 命中数 / 风险标出率）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.core.compliance.engine import judge_point_rule, _behavior_scope_of, _anchor_terms
from src.core.retrieval.hybrid_engine import perform_hybrid_search, set_db_override
from src.core.storage.sqlite_db import load_vec_extension, get_db_connection

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


def run(channels: list[str] | None, db: Path) -> dict:
    set_db_override(str(db))
    conn = get_db_connection(db)
    load_vec_extension(conn)
    red_hit = yellow_hit = total_red = total_yellow = 0
    for text, expect in GROUND_TRUTH:
        point = {"point_type": "测试", "point_content": text}
        anchor = _anchor_terms(text)
        q = f"{text} {anchor}" if anchor else text
        matched = perform_hybrid_search(q, top_k=5, channels=channels,
                                        behavior_scope_filter=_behavior_scope_of(point))
        v = judge_point_rule(point, matched)
        if expect == "red":
            total_red += 1
            if v["verdict"] == "red":
                red_hit += 1
        else:
            total_yellow += 1
            if v["verdict"] in ("red", "yellow"):
                yellow_hit += 1
    set_db_override(None)
    return {"red": f"{red_hit}/{total_red}", "yellow": f"{yellow_hit}/{total_yellow}"}


def main() -> int:
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("eval/golden/knowledge-snapshot.db")
    full = run(None, db)
    no_bs = run([c for c in ("exact", "fts", "vec", "modality", "legal_element")
                 if c != "behavior_scope"], db)
    print(json.dumps({"all_channels": full, "no_behavior_scope": no_bs},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
