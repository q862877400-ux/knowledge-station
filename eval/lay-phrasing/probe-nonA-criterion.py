"""探针：把"非 A 子集"的口径**算清楚**——到底是"与术语名重合"还是"与定义条款重合"？

为什么要问（2026-09-25 自查时发现的对不上）：
* `docs/research/lay-gap-decomposition.md` §七 写：「1,651 只扣"与**定义条款**有**词级**重合"」，
  而 §二 又给了一张表说"命中定义条款"的 A 档 = **754 条（41.2%）"。
* 可是 `scripts/measure-term-bridge.py` 与几个探针里，判非 A 用的是
  `words(说法) & words(术语)` —— 比的是**术语名**，不是定义条款正文。
⇒ 两处说法不可能同时成立，必有一处是错的。这里把两个数都算出来，
  看 1,651 / 181 到底对应哪一个口径。**这一条会影响所有引用"非 A 1651"的地方。**
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.core.retrieval.term_bridge import TERM_ENTRY_RE   # noqa: E402
from src.core.text_utils import segment_for_fts            # noqa: E402

DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
CASES = REPO / "var" / "tmp" / "gen-V2.jsonl"
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")


def words(t: str) -> set[str]:
    return {w for w in segment_for_fts(t or "").split() if CJK.match(w)}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    rows = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    wanted = {r["term"] for r in rows}
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    # 术语 → 它的**全部**定义条款正文（与复算脚本同一套抽取）
    # ⚠ 用 `for (txt,) in ...` 解包 —— 第一版写成 `for txt in ...` 又把 `txt` 原样存进
    #   `def_text`，于是元组一路传到 jieba ⇒ `AttributeError: 'tuple' object has no
    #   attribute 'decode'`（本会话第二次踩同一个坑，留痕）。
    def_text: dict[str, list[str]] = {}
    for (txt,) in conn.execute("SELECT content_text FROM clause_revision"):
        m = TERM_ENTRY_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in wanted:
            def_text.setdefault(t, []).append(txt or "")

    n = a_name = a_def = 0
    name_hit_def_miss = def_hit_name_miss = 0
    for r in rows:
        t = r["term"]
        if t not in def_text:
            continue
        wn, wd = words(t), set()
        for d in def_text[t]:
            wd |= words(d)
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx:
                continue
            n += 1
            wq = words(tx)
            hn, hd = bool(wq & wn), bool(wq & wd)
            a_name += int(hn)
            a_def += int(hd)
            name_hit_def_miss += int(hn and not hd)
            def_hit_name_miss += int(hd and not hn)

    print(f"可判说法 {n} 条")
    print(f"  与**术语名**有词级重合（= 脚本现在用的口径）：{a_name} = {a_name/n:.1%}"
          f" ⇒ 非 A {n-a_name}")
    print(f"  与**定义条款正文**有词级重合（= 文档 §二 说的口径）：{a_def} = {a_def/n:.1%}"
          f" ⇒ 非 A {n-a_def}")
    print(f"  只被术语名判为 A、定义条款里没有的：{name_hit_def_miss}")
    print(f"  只被定义条款判为 A、术语名里没有的：{def_hit_name_miss}")
    print()
    print("  读法：哪个数与复算脚本印的'非 A 1651'对得上，就是脚本实际在用的口径；")
    print("  对不上的那个数（754）则属于另一个口径，**引用时必须一起说清**。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
