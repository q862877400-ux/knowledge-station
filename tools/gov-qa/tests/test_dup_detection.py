"""测试：重复 id 判据必须**跨文件**也生效（spec 005 T203 之二）。

**为什么这条必须有**：原实现把 `per_src` 放在**文件循环内** ⇒ 同一个
`(source, id)` 落在两个不同文件里**永远比不到**，判据报 `DUPS=0`。
受控复现：两个文件各一条同 `(source,id)`，旧写法算出 0。
⇒ 本用例钉住"全局计数"这个行为；谁改回按文件计数，它必红。
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

AUDIT = Path(__file__).resolve().parent.parent / "recon" / "audit-coverage.py"


def _load_audit():
    spec = importlib.util.spec_from_file_location("audit_cov", AUDIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rec(src="X", mid="1"):
    return {"source": src, "id": mid, "question": "q", "answer": "a", "extra": {}}


def _write(path: Path, recs: list) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
                    encoding="utf-8")


def _data_dir(root: Path) -> Path:
    """`show_gate()` 读的是 `<ROOT>/data/*.jsonl` —— 所以语料要放 `data/` 子目录。

    ⚠ 这是我自己第一版踩的坑：把文件直接放在 `tmp_path` 下 ⇒ 实现扫不到
    ⇒ 它报 `DUPS=0` 而测试以为"跨文件重复检测失败"。
    """
    d = root / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_duplicate_id_across_two_files_is_detected(tmp_path, monkeypatch):
    """**跨文件**的同 `(source,id)` 必须被数出来。

    ⚠⚠ **2026-10-10 重写（独立复核发现 2，中-高）**：原用例**自己内联复刻**了
    计数逻辑（在测试文件里把 `hits`/`dups` 重写一遍）⇒ 它测的是**副本**，
    不是实现。复核实测：把 `audit-coverage.py` 退回单文件口径，**三条用例仍全绿**，
    而文档却写"谁改回去必红"。
    ⇒ 现在**真的调实现**（`audit_coverage.show_gate`），并捕获它的 stdout。
    """
    ac = _load_audit()
    dd = _data_dir(tmp_path)
    _write(dd / "a.jsonl", [_rec()])
    _write(dd / "b.jsonl", [_rec()])          # 同 source 同 id，另一个文件
    monkeypatch.setattr(ac, "ROOT", tmp_path)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ac.show_gate()
    out = buf.getvalue()
    m = re.search(r"^DUPS=(\d+)", out, re.M)
    assert m, f"show_gate 应打出 DUPS=，实际：{out[:200]}"
    assert int(m.group(1)) == 1, f"跨文件重复应数出 1，实际 {m.group(1)}"


def test_no_duplicate_when_ids_differ(tmp_path, monkeypatch):
    """**反向用例**：id 不同不得误报（判据不能恒真）。

    ⚠ 同样改为**调真实实现**（原版内联复刻，测的是副本）。
    """
    ac = _load_audit()
    dd = _data_dir(tmp_path)
    _write(dd / "a.jsonl", [_rec(mid="1")])
    _write(dd / "b.jsonl", [_rec(mid="2")])
    monkeypatch.setattr(ac, "ROOT", tmp_path)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ac.show_gate()
    m = re.search(r"^DUPS=(\d+)", buf.getvalue(), re.M)
    assert m and int(m.group(1)) == 0, f"id 不同不得报重复：{buf.getvalue()[:200]}"


def test_source_implementations_use_global_counting():
    """**结构判据**：`show_gate` 与 `show_dups` 都不得把 per-file 状态放回文件循环内。

    ⚠⚠ **2026-10-10 收紧（独立复核发现 2）**：原版只断言 `"hits" in body` ——
    复核实测：把实现退回单文件口径（键里加文件名）后 **`hits` 仍在 body 里**，
    这条照样通过。⇒ 现在改为**检查 per-file 状态确实在循环外**：
    即 `for p in` 这一行**之后**不得再出现新的 `= {}` / `defaultdict` 初始化。
    """
    src = AUDIT.read_text(encoding="utf-8")
    for fn in ("def show_gate", "def show_dups"):
        start = src.find(fn)
        assert start >= 0, f"找不到 {fn}"
        end = src.find("\ndef ", start + 1)
        body = src[start:end if end > 0 else len(src)]
        lines = body.splitlines()
        loop_at = next((i for i, ln in enumerate(lines) if "for p in" in ln), None)
        assert loop_at is not None, f"{fn} 里应有 `for p in` 遍历文件"
        # 循环体 = 从 `for p in` 到**下一个顶格行**（缩进回到 0 即出循环）
        indent = len(lines[loop_at]) - len(lines[loop_at].lstrip())
        end_at = len(lines)
        for k in range(loop_at + 1, len(lines)):
            if lines[k].strip() and (len(lines[k]) - len(lines[k].lstrip())) <= indent:
                end_at = k
                break
        loop_body = "\n".join(lines[loop_at + 1:end_at])
        bad = [ln.strip() for ln in loop_body.splitlines()
               if ("= {}" in ln or "defaultdict" in ln)]
        assert not bad, (
            f"{fn} 的 `for p in` **循环体内**又出现了 per-file 计数器 "
            f"⇒ 跨文件重复会漏检：{bad}")


def test_health_py_has_the_same_fix():
    """**兄弟文件判据**：`health.py` 的重复 id 判据也必须是**全局**口径。

    ⚠ 独立复核发现 5：本批在 `audit-coverage.py` 修了跨文件盲区，
    **却把 `health.py` 原样留着**（同一个 bug）。这条防它再退回去。
    """
    hp = Path(__file__).resolve().parent.parent / "health.py"
    src = hp.read_text(encoding="utf-8")
    assert "def count_duplicate_ids" in src, "health.py 应有独立的重复 id 函数"
    i = src.find("def count_duplicate_ids")
    j = src.find("\ndef ", i + 1)
    body = src[i:j if j > 0 else len(src)]
    lines = body.splitlines()
    loop_at = next((k for k, ln in enumerate(lines) if "for p in" in ln), None)
    assert loop_at is not None
    indent = len(lines[loop_at]) - len(lines[loop_at].lstrip())
    end_at = len(lines)
    for k in range(loop_at + 1, len(lines)):
        if lines[k].strip() and (len(lines[k]) - len(lines[k].lstrip())) <= indent:
            end_at = k
            break
    loop_body = "\n".join(lines[loop_at + 1:end_at])
    bad = [ln.strip() for ln in loop_body.splitlines()
           if ("= {}" in ln or "defaultdict" in ln)]
    assert not bad, f"health.py 的循环体内又出现 per-file 计数器：{bad}"
