"""E4 · 步骤 5：**保真探针** —— 证明"只换了模型"，没换文本。

## 为什么必须做
E4 的结论是「换嵌入模型 ⇒ 向量@1000 +32.5pt」。这个结论只有在**两臂用的条文文本逐字相同**时才成立。
`01-embed-qwen.py` 里有它自己的一份文本公式副本；若它与生产入库公式有任何差别，
那测出来的就是"**换文本 + 换模型**"，而不是"只换模型"。

## 怎么验（与 E1 的保真探针同一思路）
取真库里一批条文，**用 E4 那份公式重算 bge-small 向量**，与**生产存好的** `clause_vec` 比余弦：
 · 若余弦 ≈ **1.000000** ⇒ E4 的公式 = 生产公式 ⇒ 文本没变，E4 测的确实只是模型；
 · 若明显 < 1 ⇒ 公式不同 ⇒ **E4 结论作废**，必须先修公式再重跑。

只读真库；不写任何东西。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4-embedding-shadow\\05-fidelity-probe.py
"""
from __future__ import annotations

import array
import json
import os
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
OUT = HERE / "fidelity-probe.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
N = 1500


def display_text(title: str | None, body: str | None) -> str:
    """**必须与 `01-embed-qwen.py` 里那一份逐字相同**（这里是它的独立副本，
    故意不 import —— 若 import，验的就是同一份代码，等于没验）。"""
    return f"{title or ''}\n{(body or '')[:512]}"


def main() -> int:
    from src.core.retrieval import embedder
    from src.core.storage.sqlite_db import load_vec_extension

    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    load_vec_extension(conn)
    rows = conn.execute(
        "SELECT v.clause_revision_id, cr.title, cr.content_text, v.embedding"
        " FROM clause_vec v JOIN clause_revision cr"
        "   ON cr.clause_revision_id = v.clause_revision_id"
        " WHERE trim(coalesce(cr.content_text,'')) <> ''"
        " ORDER BY cr.rowid LIMIT ?", (N,)).fetchall()
    print(f"[fid] 抽样 {len(rows)} 条（真库只读）", flush=True)

    texts = [display_text(r[1], r[2]) for r in rows]
    t0 = __import__("time").perf_counter()
    embs = embedder.embed_batch(texts)
    print(f"[fid] 重算完，用时 {__import__('time').perf_counter()-t0:.0f}s", flush=True)

    cos, diffs = [], []
    for (cid, _t, _b, stored), e in zip(rows, embs):
        s = list(array.array("f", bytes(stored)))
        c = sum(a * b for a, b in zip(s, e))
        cos.append(c)
        diffs.append(max(abs(a - b) for a, b in zip(s, e)))
    cos.sort()
    worst = min(cos)
    result = {
        "question": "E4 用的条文文本是不是生产那一份？（若否 ⇒ E4 结论作废）",
        "n": len(rows),
        "cosine_min": worst, "cosine_median": cos[len(cos) // 2], "cosine_max": cos[-1],
        "max_abs_component_diff": max(diffs),
        "n_below_0.999": sum(1 for c in cos if c < 0.999),
        "verdict": ("✅ 公式一致（余弦 ≈1.0）⇒ 文本没变，E4 测的确实只是模型"
                    if worst > 0.999 else
                    "⛔ 公式不一致 ⇒ E4 测的是『换文本 + 换模型』⇒ **结论作废、先修公式重跑**"),
        "note": "与 E1 的保真探针同思路：用同一份公式重算，与库里存好的向量比余弦。",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    conn.close()
    return 0 if worst > 0.999 else 1


if __name__ == "__main__":
    sys.exit(main())
