"""STARD 在库率 · **第二刀：条文级**（法律名对上了，那"这一条"在不在、内容对不对）。

## 为什么必须补这一刀
上一刀量的是**法律级**：`中华人民共和国民法典` 在我们库里 ✅ ⇒ 2717/2717 = 100%。
但**法律在库 ≠ 这一条在库**。而且 STARD **每条金标都给了法条全文**（`相关法规` 字段），
⇒ 可以**拿它的原文与我们的条文做内容比对**，这才是"能不能当考卷"的决定性证据。

## 三档判据（逐条金标）
 · **L1 法律在库**（上一刀已量，100%）；
 · **L2 条号命中**：该法律所属文档下，`clause_number` 里能找到这个条号；
 · **L3 内容对得上**：把它的法条全文与我们的条文做**归一化后的相似度**，
   ≥ 阈值才算"同一条内容"。

## 口径
 · 条号：STARD 的 `match_name` 末尾「第…条」→ 拿它去 `clause_revision.clause_number` 里找；
 · 内容相似：去空白/标点后，用**最长公共子序列的比例**（不引外部依赖）与**首 30 字是否一致**双判；
 · **只读**：不写库、不改任何东西。

用法： .venv\\Scripts\\python.exe tools\\measure-stard-clause-level.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "research" / "STARD-在库率-条文级.json"
QUERIES = ROOT / "var" / "tmp" / "stard-queries.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

CLAUSE_TAIL = re.compile(r"(第[一二三四五六七八九十百千零〇\d]+条(?:之[一二三四五六七八九十]+)?)\s*$")
PUNC = re.compile(r"[\s《》（）()【】\[\]·•・，。、；：！？,.;:!?\"'“”‘’\-—–~`|/\\]+")


def norm(s: str) -> str:
    return PUNC.sub("", s or "")


def split_name(full: str) -> tuple[str, str]:
    m = CLAUSE_TAIL.search(full)
    if not m:
        return full.strip(), ""
    return full[: m.start()].strip(), m.group(1).strip()


def main() -> int:
    if not QUERIES.exists():
        print(f"⛔ 缺 {QUERIES}")
        return 1
    rows = json.loads(QUERIES.read_text(encoding="utf-8"))
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)

    lib: dict[str, str] = {}
    for no, nm in c.execute("SELECT standard_no, standard_name FROM doc_meta"):
        if nm:
            lib[norm(nm)] = no

    def find_doc(name: str) -> str | None:
        k = norm(name)
        if not k:
            return None
        if k in lib:
            return lib[k]
        k2 = norm(re.sub(r"^中华人民共和国", "", k))
        if k2 and k2 in lib:
            return lib[k2]
        return None

    stat = Counter()
    per = []
    n_gold = 0
    for r in rows:
        hits = 0
        tot = 0
        details = []
        for full, text in (r.get("相关法规") or {}).items():
            tot += 1
            n_gold += 1
            law, cl = split_name(full)
            no = find_doc(law)
            if not no:
                stat["L1_法律不在库"] += 1
                details.append({"full": full, "level": "无法律"})
                continue
            stat["L1_法律在库"] += 1
            if not cl:
                stat["L2_无条号"] += 1
                details.append({"full": full, "level": "无条号", "lib_no": no})
                continue
            # 库里该文档下有没有这个条号
            row = c.execute(
                "SELECT content_text FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
                " WHERE dm.standard_no=? AND cr.clause_number=?", (no, cl)).fetchone()
            if not row:
                stat["L2_条号未命中"] += 1
                details.append({"full": full, "level": "条号未命中", "lib_no": no})
                continue
            stat["L2_条号命中"] += 1
            ours = norm(row[0])
            theirs = norm(text)
            ratio = SequenceMatcher(None, ours[:1200], theirs[:1200]).ratio()
            head_same = ours[:30] == theirs[:30]
            if head_same or ratio >= 0.85:
                stat["L3_内容对得上"] += 1
                hits += 1
            else:
                stat["L3_内容对不上"] += 1
            details.append({"full": full, "level": "条号命中", "ratio": round(ratio, 3),
                            "head_same": head_same, "lib_no": no})
        per.append({"query_id": r.get("query_id"), "问题": (r.get("问题") or "")[:60],
                    "n_gold": tot, "ok": hits, "details": details})

    print(f"[s] 问题 {len(rows)} 条；金标法条 {n_gold} 个\n")
    print("[s] === 逐档统计 ===")
    for k in ("L1_法律在库", "L1_法律不在库", "L2_无条号", "L2_条号命中", "L2_条号未命中",
              "L3_内容对得上", "L3_内容对不上"):
        if stat[k]:
            print(f"     {k:16s} {stat[k]:6d}  ({stat[k]/max(1,n_gold):.1%})")
    fully = sum(1 for p in per if p["n_gold"] and p["ok"] == p["n_gold"])
    anyok = sum(1 for p in per if p["ok"] > 0)
    print(f"\n[s] ★ 整条问题**全部**金标都'条号命中且内容对得上' = {fully}/{len(rows)} = {fully/len(rows):.1%}")
    print(f"[s]   至少有一条对得上 = {anyok}/{len(rows)} = {anyok/len(rows):.1%}")

    OUT.write_text(json.dumps({
        "why": "STARD 在库率·条文级（法律名对上了，这一条在不在、内容对不对）",
        "source": "https://github.com/oneal2000/STARD (MIT); arXiv 2406.15313",
        "n_queries": len(rows), "n_gold": n_gold,
        "stats": dict(stat),
        "fully_matched_queries": fully, "any_matched_queries": anyok,
        "rates": {"fully": round(fully / len(rows), 4), "any": round(anyok / len(rows), 4)},
        "per_query": per[:200],
        "boundary": ["内容比对用归一化后 LCS 比例 ≥0.85 或首 30 字一致；",
                     "STARD 与我们库可能版本不同（法条修订），'对不上'不等于我们错；",
                     "只读；未写库。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
