"""测试：字段体检 + 健康结论（US3 / US4）。

对应 spec 004 的 FR-015 ~ FR-021 / SC-008 ~ SC-011。
"""
from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "recon"))


# ---------------------------------------------------------------- US3 字段体检

def test_field_audit_detects_both_empty(tmp_path, monkeypatch):
    """**SC-008**：能检出「问题与答复同时为空」。"""
    import importlib
    fa = importlib.import_module("field-audit")
    d = tmp_path / "data"
    d.mkdir()
    (d / "x.jsonl").write_text(
        json.dumps({"source": "s", "id": "1", "question": "q", "answer": "a"}) + "\n" +
        json.dumps({"source": "s", "id": "2", "question": "", "answer": ""}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(fa, "DATA", d)
    monkeypatch.setattr(sys, "argv", ["field-audit.py", "--quiet"])
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    fa.main()
    out = buf.getvalue()
    assert "BOTH_EMPTY=1" in out, out
    assert "TOTAL=2" in out, out


def test_field_audit_detects_q_empty_a_ok(tmp_path, monkeypatch):
    """能单独列出「问题为空但答复有内容」（nat-mohurd 的实际问题）。"""
    import importlib
    fa = importlib.import_module("field-audit")
    d = tmp_path / "data"
    d.mkdir()
    (d / "x.jsonl").write_text(
        json.dumps({"source": "nat-mohurd", "id": "1", "question": "",
                    "answer": "有内容"}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(fa, "DATA", d)
    monkeypatch.setattr(sys, "argv", ["field-audit.py", "--quiet"])
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    fa.main()
    assert "Q_EMPTY_A_OK=1" in buf.getvalue(), buf.getvalue()


def test_field_audit_exit_code_on_both_empty(tmp_path, monkeypatch):
    """有问题与答复同时为空 ⇒ 退出码 1（可被闸门用）。"""
    import importlib
    fa = importlib.import_module("field-audit")
    d = tmp_path / "data"
    d.mkdir()
    (d / "x.jsonl").write_text(
        json.dumps({"source": "s", "id": "1", "question": "", "answer": ""}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(fa, "DATA", d)
    monkeypatch.setattr(sys, "argv", ["field-audit.py", "--quiet"])
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    assert fa.main() == 1


# ---------------------------------------------------------------- US3 标签准确率

def test_label_accuracy_refuses_without_human_check(tmp_path, monkeypatch, capsys):
    """**宪法 III**：未人工核对时必须输出「明确未做」，**不给数字**。

    ⚠⚠ **2026-10-10 修（spec 005 T502）**：原断言是
    `assert "%" not in out or "未做" in out` —— 那是**「或」**，
    只要输出里有「未做」两字，**塞进去一个假百分比也照样过**（独立复核实测）。
    ⇒ 现在改成**两条独立断言**：必须说「未做」**且**不得出现百分比数字。
    """
    import importlib
    la = importlib.import_module("label-accuracy")
    p = tmp_path / "c.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["label", "label_ok"])
        w.writeheader()
        w.writerow({"label": "咨询", "label_ok": ""})      # 未填
    monkeypatch.setattr(sys, "argv", ["label-accuracy.py", "--score", str(p)])
    rc = la.main()
    out = capsys.readouterr().err + capsys.readouterr().out
    assert rc == 1
    # ① 必须明确说「未做」
    assert "未做" in out, f"未核对时必须说「明确未做」，实际输出：{out[:300]}"
    # ② **且**不得把百分比当**结论**给出来。
    #    ⚠ 不能简单断言"输出里没有 %" —— 未做分支的**解释句**里
    #      本来就引用了"模型自评的 78.9%"来说明"不许拿它充数"
    #      （第一版这么断言，当场误报）。⇒ 只查**结论形态**。
    #    ⚠⚠ **2026-10-10 接手方修（本判据自己的第二个洞）**：原正则写
    #      `准确率[：:]\s*\d+…` —— **要求"准确率"后面必须紧跟冒号**，
    #      而上面那行注释明写要抓两种形态：`真实准确率：NN.N%` **或** `准确率 NN.N%`。
    #      ⇒ 后者（**空格分隔、无冒号**）**抓不到**（实测：`准确率 88.8%` ⇒ 匹配为空）。
    #      改成**冒号可有可无**（`[：:]?`），与注释的意图对齐。
    import re as _re
    conclusion = _re.findall(r"(?:真实)?准确率[：:]?\s*\d+(?:\.\d+)?\s*%", out)
    assert not conclusion, f"未核对时不得给出准确率结论，实际出现了 {conclusion}"


def test_label_accuracy_scores_after_human_check(tmp_path, monkeypatch):
    """人工填完后能算准确率，并按标签来源分层（**关键：模型标的那部分**）。"""
    import importlib
    la = importlib.import_module("label-accuracy")
    p = tmp_path / "c.csv"
    rows = [
        {"label": "咨询", "label_source": "source_label", "label_ok": "1"},
        {"label": "咨询", "label_source": "source_label", "label_ok": "1"},
        {"label": "建议", "label_source": "model", "label_ok": "1"},
        {"label": "建议", "label_source": "model", "label_ok": "0"},
    ]
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["label", "label_source", "label_ok"])
        w.writeheader()
        w.writerows(rows)
    monkeypatch.setattr(sys, "argv",
                        ["label-accuracy.py", "--score", str(p), "--quiet"])
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    rc = la.main()
    out = buf.getvalue()
    assert "ACCURACY=75.0" in out, out
    assert "SAMPLED=4" in out, out
    assert rc == 1, "75% < 80% 应返回 1"


# ---------------------------------------------------------------- US4 健康结论

def test_health_reports_usable(tmp_path, monkeypatch):
    """**SC-011**：可用时一句话结论 + VERDICT=usable。"""
    import importlib
    h = importlib.import_module("health")
    d = tmp_path / "data"
    d.mkdir()
    (d / "x.jsonl").write_text(
        json.dumps({"source": "s", "id": "1", "question": "q", "answer": "a",
                    "extra": {"msg_type_norm": "咨询"}}) + "\n", encoding="utf-8")
    fl = tmp_path / ".round-floor"
    fl.write_text("0", encoding="utf-8")
    monkeypatch.setattr(h, "DATA", d)
    monkeypatch.setattr(h, "FLOOR_FILE", fl)
    # 临时目录里只有 1 个文件 ⇒ 331 个 adapter 会被判「零数据」（正确但干扰测试）
    # ⇒ mock 掉这个检查，专注验证「健康」路径
    monkeypatch.setattr(h, "count_empty_adapters", lambda files: 0)
    monkeypatch.setattr(sys, "argv", ["health.py", "--quiet"])
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    rc = h.main()
    out = buf.getvalue()
    assert "VERDICT=usable" in out, out
    assert "COVERAGE=100.0" in out, out
    assert rc == 0


def test_health_detects_all_three_faults(tmp_path, monkeypatch):
    """**SC-009**：一次运行检出全部故障（重复 id + 覆盖不足）。"""
    import importlib
    h = importlib.import_module("health")
    d = tmp_path / "data"
    d.mkdir()
    rec = json.dumps({"source": "s", "id": "1", "question": "q", "answer": "a"})
    # 同 id 两行 ⇒ 重复
    (d / "x.jsonl").write_text(rec + "\n" + rec + "\n", encoding="utf-8")
    fl = tmp_path / ".round-floor"
    fl.write_text("999999", encoding="utf-8")           # 地板高于实际 ⇒ 数据在退
    monkeypatch.setattr(h, "DATA", d)
    monkeypatch.setattr(h, "FLOOR_FILE", fl)
    monkeypatch.setattr(sys, "argv", ["health.py", "--quiet"])
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    rc = h.main()
    out = buf.getvalue()
    assert "VERDICT=not_usable" in out, out
    assert "DUPS=1" in out, out                          # 故障 1：重复
    assert "TOTAL=2" in out and "FLOOR=999999" in out    # 故障 2：数据在退
    assert "COVERAGE=0.0" in out, out                    # 故障 3：标签覆盖不足
    assert rc == 1


def test_health_quiet_is_pure_ascii(tmp_path, monkeypatch):
    """**R5**：机器可读输出必须纯 ASCII。"""
    import importlib
    h = importlib.import_module("health")
    d = tmp_path / "data"
    d.mkdir()
    (d / "x.jsonl").write_text("", encoding="utf-8")
    fl = tmp_path / ".round-floor"
    fl.write_text("0", encoding="utf-8")
    monkeypatch.setattr(h, "DATA", d)
    monkeypatch.setattr(h, "FLOOR_FILE", fl)
    monkeypatch.setattr(sys, "argv", ["health.py", "--quiet"])
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    h.main()
    buf.getvalue().encode("ascii")      # 非 ASCII 会抛异常


def test_health_trace_appends(tmp_path, monkeypatch):
    """**FR-019**：能追加执行轨迹。"""
    import importlib
    h = importlib.import_module("health")
    d = tmp_path / "data"
    d.mkdir()
    (d / "x.jsonl").write_text("", encoding="utf-8")
    fl = tmp_path / ".round-floor"
    fl.write_text("0", encoding="utf-8")
    tr = tmp_path / "trace.log"
    monkeypatch.setattr(h, "DATA", d)
    monkeypatch.setattr(h, "FLOOR_FILE", fl)
    monkeypatch.setattr(sys, "argv",
                        ["health.py", "--quiet", "--trace", str(tr)])
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    h.main()
    assert tr.exists() and "verdict=" in tr.read_text(encoding="utf-8")
