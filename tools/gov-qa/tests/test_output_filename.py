"""测试：**落盘文件名必须过滤非法字符**（2026-10-10 实测的真缺陷）。

## 为什么

`ay-zmhd` 的站名是 `安阳市·政民互动（市长信箱/连线政府/市长电话）` —— 里面有 `/`。
`harvest.py` 原来**原样拼接** `f"{key}-{name}.jsonl"`
⇒ 路径被当成**多一层目录** ⇒ `FileNotFoundError`。

**最坏的地方**：整个采集**跑完全程**（翻完 30 页、日志正常）**却一条没落盘**，
日志末尾看起来像"采集完了"。**静默丢数据**。

## 两处命名规则必须一致

`poll.py::data_path_for` **本来就过滤**非法字符，而 `harvest.py` 没有
⇒ 首采与增量轮询会写进**不同文件**（一个带 `/`、一个不带）。
本组用例钉住两边**同规则**。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ILLEGAL = '\\/:*?"<>|'


def test_poll_data_path_for_strips_illegal_chars():
    """`poll.data_path_for` 必须过滤非法字符（这是既有行为，钉住不许退）。"""
    from poll import data_path_for
    p = data_path_for("ay-zmhd", "安阳市·政民互动（市长信箱/连线政府/市长电话）")
    assert "/" not in p.name, f"文件名不得含 `/`：{p.name}"
    assert p.parent.name == "data", f"不得多出一层目录：{p}"
    for ch in ILLEGAL:
        assert ch not in p.name, f"文件名不得含 {ch!r}：{p.name}"


def test_harvest_module_actually_sanitises():
    """**核心判据（真的读 harvest.py 的源码来判）**。

    ⚠ 我第一版把 `harvest.py` 的算法**在测试里重抄了一遍**再比对 ——
    那是"测副本"，把 `harvest.py` 退回原样拼接时**它照样全绿**
    （实测变异验证：退回后 `3 passed`）。
    ⇒ 现在**直接读 `harvest.py` 的源码**，断言它确实做了过滤：
    ① 有 `safe = ...` 这一行；
    ② 拼接用的是 `safe` 而不是 `site['name']`。
    """
    src = (ROOT / "harvest.py").read_text(encoding="utf-8")
    assert "safe = " in src, (
        "harvest.py 必须先把站名过滤非法字符再拼文件名 —— "
        "否则站名含 `/` 的适配器会把路径当目录，**跑完全程却一条不落盘**")
    assert "f\"{site['key']}-{safe}.jsonl\"" in src, (
        "harvest.py 的落盘路径必须用 `safe`（过滤后的站名），不能用原始 `site['name']`")
    assert "f\"{site['key']}-{site['name']}.jsonl\"" not in src, (
        "harvest.py 又退回用原始站名拼路径了")


def test_harvest_and_poll_agree_on_the_filename():
    """**判据**：`harvest.py` 的过滤规则与 `poll.py` 必须**逐字符一致**。

    两处不一致 ⇒ 首采与增量轮询各写各的文件 ⇒ 数据分裂。
    做法：把两个文件里那条 `ch not in ...` 的**字面量**抠出来比。
    """
    import re
    h = (ROOT / "harvest.py").read_text(encoding="utf-8")
    p = (ROOT / "poll.py").read_text(encoding="utf-8")
    pat = re.compile(r"ch not in '([^']*)'")
    mh, mp = pat.search(h), pat.search(p)
    assert mh, "harvest.py 里找不到非法字符过滤"
    assert mp, "poll.py 里找不到非法字符过滤"
    assert mh.group(1) == mp.group(1), (
        f"两处过滤字符集不一致：harvest={mh.group(1)!r} poll={mp.group(1)!r}")


def test_no_adapter_name_breaks_the_path():
    """**全量判据**：任何适配器的 `SITE['name']` 都不得在落盘路径里出问题。

    这条扫**全部适配器**，不依赖"我记得改了哪几个"。
    """
    import adapters
    from poll import data_path_for
    bad = []
    for k in sorted(adapters.ADAPTERS):
        try:
            m = adapters.load(k)
        except Exception:                                               # noqa: BLE001
            continue
        name = str((m.SITE or {}).get("name") or "")
        p = data_path_for(k, name)
        if p.parent.name != "data" or not p.name.endswith(".jsonl"):
            bad.append((k, name, str(p)))
        elif any(ch in p.name for ch in ILLEGAL):
            bad.append((k, name, p.name))
    assert not bad, f"这些适配器的站名会让落盘路径出问题：{bad[:5]}"
