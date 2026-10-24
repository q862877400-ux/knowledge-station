"""`answer_confidence` 的判据（2026-10-24 统一化第五批）。

## 为什么这个文件必须存在

同一判据原来在 `api/server.py` 与 `llm/ks_answer.py` 里**各写一份且已分叉**：

| | server（旧） | ks_answer（旧） |
|---|---|---|
| 空证据 | **不特判** → `high` | 特判 → `low` |
| 字段名 | `is_suspicious` / `type_confidence` | `_is_suspicious` / `_type_confidence` |

**实测后果**：把 server 形态的证据喂给 ks_answer 那份，低可信证据被读成
`{'level': 'high', 'reasons': ['核验通过且证据高可信']}` —— **静默漏判**。

两份都在 `create_app` 闭包里 / 被闭包调用 ⇒ **没有单测能发现分叉**。
本文件就是那个缺失的单测，同时钉住「只有一处实现」这件事。

## 判据分四组

1. **两处是同一个函数对象**（防有人又各写一份）；
2. **两种字段名结果相同**（这是原来分叉的地方）；
3. **四种输入的档位**（空证据 / 核验不过 / 低可信 / 高可信）；
4. **阈值边界**（0.85 上下一格）。
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.llm.ks_answer import answer_confidence  # noqa: E402


def _v(ok: bool = True):
    return SimpleNamespace(is_valid=ok)


def _ev(no="-", suspicious=False, conf=1.0, underscore=False):
    """造一条证据。`underscore=True` 用 ks_answer 的字段名，否则用 server 的。"""
    p = "_" if underscore else ""
    return {f"{p}clause_number" if False else "clause_number": no,
            f"{p}is_suspicious": suspicious,
            f"{p}type_confidence": conf}


# ── 组 1：只有一处实现 ────────────────────────────────────────────────
def test_two_call_sites_are_the_same_function():
    """`server._answer_confidence` 必须是**转发**，不是第二份实现。

    它是 `create_app` 闭包里的局部函数（模块外拿不到），所以用**源码静态检查**。

    ⚠ **必须先把 docstring 剥掉再判**（本测试第一版就踩了）：
    server.py 那个函数的 docstring 里**故意写了 `is_suspicious` / `0.85`**
    —— 那是记录「旧实现长什么样、为什么分叉」的留痕。
    不剥 docstring 就会把留痕当成「分叉回潮」，得到一条**假红**。
    `ast` 能干净地剥：`ast.get_docstring()` 拿到的就是它。
    """
    import ast

    path = Path(__file__).resolve().parents[1] / "src" / "core" / "api" / "server.py"
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)

    # 找 create_app 里那个 def _answer_confidence
    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_answer_confidence":
            target = node
            break
    assert target is not None, "server.py 里的 _answer_confidence 不见了（被改名/删除？）"

    # 代码面（去掉 docstring）—— 这里才该只有一行转发
    def _is_docstring(n: ast.stmt) -> bool:
        return isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)

    body_stmts = [n for n in target.body if not _is_docstring(n)]
    code = "\n".join(ast.unparse(n) for n in body_stmts)

    assert "answer_confidence(verification, ev_dicts)" in code, (
        "server.py 的 _answer_confidence 不再是转发 —— 判据又分叉了")
    assert "is_suspicious" not in code, (
        "server.py 的 _answer_confidence 里又出现了判据本体（is_suspicious）—— 分叉回潮")
    assert "0.85" not in code, "server.py 里又出现了 0.85 阈值 —— 分叉回潮"


# ── 组 2：两种字段名结果必须相同（这就是原来分叉的地方）────────────────
@pytest.mark.parametrize("suspicious,conf,expect", [
    (False, 1.0, "high"),
    (False, 0.5, "mid"),
    (True, 1.0, "mid"),
])
def test_both_field_spellings_agree(suspicious, conf, expect):
    """裸名与下划线名必须给出**同一个档位**。

    旧实现里 `server` 只认裸名、`ks_answer` 只认下划线名 ⇒
    同一批证据在两处得到不同结论（一个是 `mid`、一个是 `high`）。
    """
    plain = answer_confidence(_v(), [_ev("5.22", suspicious, conf, underscore=False)])
    under = answer_confidence(_v(), [_ev("5.22", suspicious, conf, underscore=True)])
    assert plain["level"] == expect, f"裸名字段：期望 {expect}，实际 {plain}"
    assert under["level"] == expect, f"下划线字段：期望 {expect}，实际 {under}"
    assert plain == under, f"两种命名结论不一致：{plain} vs {under}"


# ── 组 3：四种输入的档位 ──────────────────────────────────────────────
def test_empty_evidence_is_low_not_high():
    """**空证据 ⇒ low**。

    旧 `server` 实现不特判空证据，直接走到最后 `return high` ——
    也就是说「一条依据都没找到」会被标成「核验通过且证据高可信」。
    这是本批修掉的**静默错误结论**。
    """
    got = answer_confidence(_v(True), [])
    assert got["level"] == "low", f"空证据必须 low（旧 server 给 high，那是错的），实际 {got}"
    assert "无有效现行证据" in "".join(got["reasons"])


def test_failed_verification_is_low():
    got = answer_confidence(_v(False), [_ev("5.22", False, 1.0)])
    assert got["level"] == "low"
    assert "核验拦截项未清零" in "".join(got["reasons"])


def test_low_confidence_evidence_is_mid():
    got = answer_confidence(_v(True), [_ev("5.22", False, 0.5)])
    assert got["level"] == "mid"
    assert "5.22" in "".join(got["reasons"])


def test_all_high_confidence_is_high():
    got = answer_confidence(_v(True), [_ev("5.22", False, 0.95), _ev("5.23", False, 1.0)])
    assert got["level"] == "high"


# ── 组 4：阈值边界（0.85 是分界线，两边各测一格）────────────────────────
@pytest.mark.parametrize("conf,expect", [
    (0.849, "mid"),    # 差一点 → 低可信
    (0.85, "high"),    # 正好 → 高可信（判据是 `< 0.85`）
    (0.851, "high"),
])
def test_threshold_boundary(conf, expect):
    got = answer_confidence(_v(True), [_ev("5.22", False, conf)])
    assert got["level"] == expect, f"conf={conf} 期望 {expect}，实际 {got}"


def test_missing_confidence_defaults_to_high():
    """没有 `type_confidence` 字段时按 1.0 处理（缺字段 ≠ 低可信）。"""
    got = answer_confidence(_v(True), [{"clause_number": "5.22"}])
    assert got["level"] == "high"
