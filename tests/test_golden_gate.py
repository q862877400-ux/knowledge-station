"""Golden Set CI 门禁（Task 10.1，红线 v2 #6）：任何检索/核验改动不得回退。

判定：以 eval/baseline.json 为基线，逐指标断言回退 ≤2pp（绝对百分点）。

⚠ 自豁免通道已关闭（2026-09-16）：旧实现在基线缺失时**自动写盘 + pytest.skip**
——删掉 `eval/baseline.json` 即可让整条门禁失效（全项目唯一"一步可破坏"的防线）。
现在基线缺失 = **失败**，并提示重建方式；确需首次建立基线走显式开关：
`KS_BASELINE_BOOTSTRAP=1 pytest tests/test_golden_gate.py`。
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "eval" / "baseline.json"
SNAPSHOT = ROOT / "eval" / "golden" / "knowledge-snapshot.db"
KEYS = ("exact_hit@1", "recall@5", "recall@10", "modality_intercept_rate",
        "compliance_accuracy", "red_precision")

#: 显式开关：仅"真首次建立基线"时用。默认关闭，使基线缺失成为硬失败。
ENV_BOOTSTRAP = "KS_BASELINE_BOOTSTRAP"


def _baseline_tracked_by_git() -> bool | None:
    """基线是否被 git 跟踪。True/False；git 不可用（未装/非仓库）返回 None。

    这不影响判定，只影响**报错措辞**：被跟踪的基线删掉会以 `D` 出现在
    `git status` 里，删基线不再是静默行为。
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "eval/baseline.json"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=10)
        return out.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return None


@pytest.fixture(scope="module")
def current():
    if not SNAPSHOT.exists():
        pytest.skip("快照库缺失：先运行 eval/golden/build_golden.py 并生成 knowledge-snapshot.db")
    import sys
    sys.path.insert(0, str(ROOT))
    from eval.run_benchmark import run_benchmark
    return run_benchmark(db_path=SNAPSHOT)


def test_golden_gate_baseline_present(current):
    """门禁前置：基线必须存在（**不得**由本测试自行重建）。

    独立成一个用例，使"基线被删"报成一条可读的失败，而不是让
    `test_golden_gate_no_regression` 抛 KeyError 之类的次生错误。
    """
    if BASELINE.exists():
        return
    if os.environ.get(ENV_BOOTSTRAP) == "1":
        BASELINE.write_text(json.dumps(current, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        pytest.skip(f"首次建立基线（{ENV_BOOTSTRAP}=1）：已写入 eval/baseline.json，"
                    "请 review 后提交；后续运行受门禁约束")
    tracked = _baseline_tracked_by_git()
    hint = ("该文件受 git 跟踪，删除会以 'D' 出现在 git status 中——"
            if tracked else "")
    raise AssertionError(
        f"Golden Set 基线缺失：{BASELINE}。{hint}"
        "门禁**不会**自动重建基线（自动重建会连同任何回退一起写进新基线，"
        "使红线 #6 失效）。确需首次建立基线请显式执行："
        f"KS_BASELINE_BOOTSTRAP=1 pytest tests/test_golden_gate.py")


def test_golden_gate_no_regression(current):
    if not BASELINE.exists():
        pytest.fail("基线缺失（见 test_golden_gate_baseline_present）：拒绝在无基线时放行")
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    # 基线的键集必须覆盖门禁判定的全部指标——防"删除某个不利指标"式规避
    # （历史实例：citation_precision@5 从未进 KEYS，即从未受门禁保护）。
    missing = [k for k in KEYS if k not in base]
    assert not missing, (
        f"基线缺少受门禁保护的指标 {missing}——基线被人为裁剪？"
        f"受保护指标集为 KEYS={KEYS}")
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
