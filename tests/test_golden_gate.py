"""Golden Set CI 门禁（Task 10.1，红线 v2 #6）：任何检索/核验改动不得回退。

判定：以 eval/baseline.json 为基线，逐指标断言回退 ≤2pp（绝对百分点）。
基线不存在时以当前结果落盘（首次运行即建立基线）。
"""
import json
from pathlib import Path

import pytest

BASELINE = Path(__file__).resolve().parent.parent / "eval" / "baseline.json"
SNAPSHOT = Path(__file__).resolve().parent.parent / "eval" / "golden" / "knowledge-snapshot.db"
KEYS = ("exact_hit@1", "recall@5", "recall@10", "modality_intercept_rate",
        "compliance_accuracy", "red_precision")


@pytest.fixture(scope="module")
def current():
    if not SNAPSHOT.exists():
        pytest.skip("快照库缺失：先运行 eval/golden/build_golden.py 并生成 knowledge-snapshot.db")
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from eval.run_benchmark import run_benchmark
    return run_benchmark(db_path=SNAPSHOT)


def test_golden_gate_no_regression(current):
    if not BASELINE.exists():
        BASELINE.write_text(json.dumps(current, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        pytest.skip("首次运行：已建立基线，后续改动受门禁约束")
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    fails = []
    for k in KEYS:
        delta_pp = round((current[k] - base[k]) * 100, 2)
        if delta_pp < -2.0:
            fails.append(f"{k}: {base[k]:.2%} → {current[k]:.2%}（回退 {abs(delta_pp)}pp）")
    assert not fails, "Golden Set 门禁回退: " + "; ".join(fails)


def test_golden_gate_minimums(current):
    """硬底线：核心指标不得低于可接受线（防集体塌方式缓慢劣化）。"""
    mins = {"modality_intercept_rate": 0.9, "red_precision": 0.9}
    fails = [f"{k} 低于底线 {v:.0%}: {current[k]:.2%}"
             for k, v in mins.items() if current[k] < v]
    assert not fails, "; ".join(fails)
