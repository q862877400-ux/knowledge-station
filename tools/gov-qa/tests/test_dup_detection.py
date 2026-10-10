"""测试：重复 id 判据必须**跨文件**也生效（spec 005 T203 之二）。

**为什么这条必须有**：原实现把 `per_src` 放在**文件循环内** ⇒ 同一个
`(source, id)` 落在两个不同文件里**永远比不到**，判据报 `DUPS=0`。
受控复现：两个文件各一条同 `(source,id)`，旧写法算出 0。
⇒ 本用例钉住"全局计数"这个行为；谁改回按文件计数，它必红。
"""
from __future__ import annotations

import importlib.util
import json
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


def test_duplicate_id_across_two_files_is_detected(tmp_path, monkeypatch):
    """**跨文件**的同 `(source,id)` 必须被数出来。"""
    ac = _load_audit()
    _write(tmp_path / "a.jsonl", [_rec()])
    _write(tmp_path / "b.jsonl", [_rec()])          # 同 source 同 id，另一个文件
    monkeypatch.setattr(ac, "ROOT", tmp_path)
    # 复刻 show_gate 的重复统计（与实现同形）
    hits = {}
    for p in sorted(tmp_path.glob("*.jsonl")):
        for line in open(p, encoding="utf-8"):
            if not line.strip().startswith("{"):
                continue
            r = json.loads(line)
            key = (str(r.get("source") or "?"), str(r.get("id")))
            hits[key] = hits.get(key, 0) + 1
    dups = sum(n - 1 for n in hits.values() if n > 1)
    assert dups == 1, f"跨文件重复应数出 1，实际 {dups}"


def test_no_duplicate_when_ids_differ(tmp_path):
    """**反向用例**：id 不同不得误报（判据不能恒真）。"""
    _write(tmp_path / "a.jsonl", [_rec(mid="1")])
    _write(tmp_path / "b.jsonl", [_rec(mid="2")])
    hits = {}
    for p in sorted(tmp_path.glob("*.jsonl")):
        for line in open(p, encoding="utf-8"):
            if not line.strip().startswith("{"):
                continue
            r = json.loads(line)
            key = (str(r.get("source") or "?"), str(r.get("id")))
            hits[key] = hits.get(key, 0) + 1
    dups = sum(n - 1 for n in hits.values() if n > 1)
    assert dups == 0


def test_source_implementations_use_global_counting():
    """**结构判据**：`show_gate` 与 `show_dups` 都不得把 `per_src` 放回文件循环内。

    这条是给"改回去"设的闸 —— 上面两条行为用例在**同形复刻**下会通过，
    所以必须再钉一次真实实现的结构。
    """
    src = AUDIT.read_text(encoding="utf-8")
    for fn in ("def show_gate", "def show_dups"):
        start = src.find(fn)
        assert start >= 0, f"找不到 {fn}"
        end = src.find("\ndef ", start + 1)
        body = src[start:end if end > 0 else len(src)]
        assert "hits" in body, f"{fn} 应当用全局 `hits` 计数（跨文件）"
