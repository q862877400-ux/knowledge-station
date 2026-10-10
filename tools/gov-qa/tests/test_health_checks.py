"""测试：`health.py` 的四项判据必须被**各自的**测试钉住。

## 为什么需要（独立复核 Finding 3）

复核实测：把 `health.py` 的**任意一项**判据改成恒真，`test_health.py` **全绿**；
四项**同时**改才变红。⇒ 那些判据实际上**没有各自被钉住**，
`test_health_detects_all_three_faults` 只验证了输出格式（`VERDICT=not_usable` 等字符串），
不是"每项判据真的会因该项故障而失败"。

⇒ 本文件给**每一项**单独造故障，断言该项**单独**就能让 `verdict` 变成不可用。
谁把某项规定改恒真，对应用例必红。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_health():
    spec = importlib.util.spec_from_file_location("health_mod", ROOT / "health.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _isolate(mod, tmp_path: Path):
    mod.DATA = tmp_path
    return tmp_path


def _rec(i, *, q="q", a="a", label="咨询", src="s", mid=None):
    ex = {}
    if label:
        ex["msg_type_norm"] = label
    return {"source": src, "id": str(mid if mid is not None else i),
            "question": q, "answer": a, "extra": ex}


def _write(tmp_path: Path, recs: list) -> None:
    (tmp_path / "x.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")


def _checks(mod):
    """跑 collect() 并返回 {判据名: 是否通过}。"""
    s = mod.collect()
    return s, mod.check_all(s) if hasattr(mod, "check_all") else None


# ---------------------------------------------------------------- 逐项造故障

def test_empty_adapter_alone_makes_unusable(tmp_path, monkeypatch):
    """**只有「零数据适配器」这一项坏** ⇒ 必须判不可用。

    做法：让 `count_empty_adapters` 返回 1，其余指标全好。
    """
    mod = _load_health()
    _isolate(mod, tmp_path)
    _write(tmp_path, [_rec(i) for i in range(3)])
    monkeypatch.setattr(mod, "count_empty_adapters", lambda files: 1)
    monkeypatch.setattr(mod, "FLOOR_FILE", tmp_path / "nofloor")
    s = mod.collect()
    checks = mod.build_checks(s) if hasattr(mod, "build_checks") else None
    assert checks is not None, "health.py 应有可单独调用的判据构造函数"
    got = {n: ok for n, ok, _d in checks}
    assert got.get("无零数据适配器") is False, f"该项应单独失败，实际 {got}"
    assert not all(got.values()), "至少一项失败 ⇒ 整体不得判可用"


def test_duplicate_ids_alone_makes_unusable(tmp_path, monkeypatch):
    """**只有「重复 id」这一项坏** ⇒ 必须判不可用。"""
    mod = _load_health()
    _isolate(mod, tmp_path)
    # 同 source 同 id 两条 ⇒ dups=1
    _write(tmp_path, [_rec(1), _rec(1)])
    monkeypatch.setattr(mod, "FLOOR_FILE", tmp_path / "nofloor")
    s = mod.collect()
    checks = mod.build_checks(s)
    got = {n: ok for n, ok, _d in checks}
    assert s["dups"] == 1, f"应数出 1 条重复，实际 {s['dups']}"
    assert got.get("无重复 id") is False, f"该项应失败，实际 {got}"


def test_floor_breach_alone_makes_unusable(tmp_path, monkeypatch):
    """**只有「数据总数低于地板」这一项坏** ⇒ 必须判不可用。"""
    mod = _load_health()
    _isolate(mod, tmp_path)
    _write(tmp_path, [_rec(i) for i in range(3)])
    fl = tmp_path / ".round-floor"
    fl.write_text("999999", encoding="utf-8")
    monkeypatch.setattr(mod, "FLOOR_FILE", fl)
    s = mod.collect()
    checks = mod.build_checks(s)
    got = {n: ok for n, ok, _d in checks}
    assert got.get("数据总数 ≥ 地板") is False, f"该项应失败，实际 {got}"


def test_low_label_coverage_alone_makes_unusable(tmp_path, monkeypatch):
    """**只有「标签覆盖率不足」这一项坏** ⇒ 必须判不可用。"""
    mod = _load_health()
    _isolate(mod, tmp_path)
    # 3 条里只有 1 条有干净标签 ⇒ 33% < 90%
    _write(tmp_path, [_rec(1, label="咨询"), _rec(2, label=None), _rec(3, label=None)])
    monkeypatch.setattr(mod, "FLOOR_FILE", tmp_path / "nofloor")
    s = mod.collect()
    checks = mod.build_checks(s)
    got = {n: ok for n, ok, _d in checks}
    name = next(n for n in got if "标签覆盖率" in n)
    assert got[name] is False, f"该项应失败，实际 {got}"
    assert s["coverage"] < 90


def test_all_good_is_usable(tmp_path, monkeypatch):
    """**反向用例**：四项全好必须判可用（判据不能恒假）。"""
    mod = _load_health()
    _isolate(mod, tmp_path)
    _write(tmp_path, [_rec(i) for i in range(5)])
    monkeypatch.setattr(mod, "FLOOR_FILE", tmp_path / "nofloor")
    monkeypatch.setattr(mod, "count_empty_adapters", lambda files: 0)
    s = mod.collect()
    checks = mod.build_checks(s)
    got = {n: ok for n, ok, _d in checks}
    assert all(got.values()), f"四项全好却判不可用：{got}"
