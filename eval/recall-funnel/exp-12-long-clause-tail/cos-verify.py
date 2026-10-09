"""P0·0.10 机制复验：尾巴到底进没进向量（余弦）。

**为什么单独一个脚本**（2026-10-09 独立复核 P1）：本批属"必验类别"，首要理由就是
"结论由作者自己的检查得出"；而"余弦复验"这一组读数**原先只在 README 里，没有可跑的尺子**
⇒ 冻结产物**不足以自证**。复核者自己写脚本复现了它（读数成立），但**脚本必须进仓**。
本文件补上那把尺子。

口径（跑前写死）
================
- 对每条条款算四个嵌入：`全文` / `前 512 字` / `前 800 字` / `尾段(512字之后)`。
- **判据**：`cos(全文, 前 800 字)` 应 **恰好 1.000000**（800 字 > 模型窗口 ⇒ 两者都被截到同一段）；
  而 `cos(全文, 前 512 字)` 应 **≠1**（512 字 < 窗口 ⇒ 全文多截了一段进去）。
- **截断点阶梯**：对一条 1,300–1,500 字的条款，逐字加长前缀，找出 cos 首次变 1.0 的字符位置
  （用真分词器同时报该前缀的 token 数）⇒ 定位"模型窗口 = 512 token ≈ 多少字"。

只读真库、不写库、不改生产代码、零网络（模型已缓存；调用方需带 HF_HUB_OFFLINE=1）。
"""

from __future__ import annotations

import glob
import json
import math
import os
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

DB_PATH = os.path.expandvars(r"%APPDATA%\KnowledgeStation\database\knowledge.db")
SNAP_GLOB = os.path.expandvars(
    r"%APPDATA%\KnowledgeStation\models\models--Qdrant--bge-small-zh-v1.5\snapshots\*\tokenizer.json")
OUT = Path(__file__).resolve().parent / "cos-verify.json"

SAMPLE_N = 5
LADDER = [512, 600, 640, 660, 700, 760, 800]


def cos(a: list[float], b: list[float]) -> float:
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return s / (na * nb)


def main() -> int:
    from src.core.retrieval import embedder
    from tokenizers import Tokenizer

    tk = glob.glob(SNAP_GLOB)
    tok = Tokenizer.from_file(tk[0]) if tk else None
    cfg = None
    if tk:
        with open(os.path.join(os.path.dirname(tk[0]), "tokenizer_config.json"), encoding="utf-8") as f:
            cfg = json.load(f).get("model_max_length")

    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT clause_revision_id, title, content_text FROM clause_revision "
        "WHERE LENGTH(content_text) BETWEEN 900 AND 2000 "
        "ORDER BY clause_revision_id LIMIT ?", (SAMPLE_N,)).fetchall()

    recs = []
    for r in rows:
        t = r["title"] or ""
        c = r["content_text"]
        vfull = embedder.embed_query(f"{t}\n{c}")
        vh = embedder.embed_query(f"{t}\n{c[:512]}")
        v800 = embedder.embed_query(f"{t}\n{c[:800]}")
        vtail = embedder.embed_query(c[512:])
        recs.append({
            "crid": r["clause_revision_id"], "len": len(c),
            "cos_full_head512": round(cos(vfull, vh), 6),
            "cos_full_first800": round(cos(vfull, v800), 6),
            "cos_full_tail": round(cos(vfull, vtail), 6),
        })

    # 截断点阶梯（一条 1,300–1,500 字的条款）
    r2 = con.execute(
        "SELECT content_text FROM clause_revision WHERE LENGTH(content_text) BETWEEN 1300 AND 1500 "
        "ORDER BY clause_revision_id LIMIT 1").fetchone()
    ladder = []
    if r2 is not None:
        c2 = r2["content_text"]
        vf = embedder.embed_query(c2)
        for L in LADDER:
            pref = c2[:L]
            ladder.append({
                "chars": L,
                "tokens": len(tok.encode(pref).ids) if tok else None,
                "cos_full_prefix": round(cos(vf, embedder.embed_query(pref)), 6),
            })

    out = {
        "db_path": DB_PATH,
        "tokenizer_model_max_length": cfg,
        "sample_n": len(recs),
        "rows": recs,
        "ladder_clause_len": len(r2["content_text"]) if r2 is not None else None,
        "ladder": ladder,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
