"""真问题探针：业主给的 **11 条真实提问**，量三件事。

## 为什么要这么量（而不是直接跑检索看结果）
业主问的是「**我 OCR 出 3 万多本国标加进去，能不能行**」。
要回答它，必须分清两种失败：
 · **库里没有这个主题的标准** ⇒ 加语料有用；
 · **库里有、但检索没找到** ⇒ 加语料没用（那是今天已经确认的"尺子"问题）。

**关键**：第二种失败**不能**用"检索返回了什么"来判断（检索失败时返回的当然不是对的那个）。
所以本脚本用**标准名**（`doc_meta` 的 6797 条）做主题命中 —— 这才是"库里有没有"的直接证据。

## 三件事
 1. **主题命中**：按每题的领域关键词，在**标准名**里找 ⇒ 库里有没有这个主题的标准、有几篇、都是哪些；
 2. **旧模型返回什么**（生产现役 bge-small，真库只读）；
 3. **新模型返回什么**（Qwen3-Embedding-0.6B，E4 的影子表，副本只读）。

⚠ 关键词是我为每题手写的（写在这里，可复核）；命中只说明"标准名里含这些字"，**不等于语义对得上**。
⚠ 判定"有没有"是我的**人工判读**，会连同证据一起给出，不掩盖。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\01-probe-real-questions.py
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
OUT = HERE / "real-questions-result.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
SHADOW = ROOT / "eval" / "recall-funnel" / "exp-4-embedding-shadow" / "exp.db"

#: 业主原话（一字不改）+ 我为每题写的主题关键词（可复核）
QUESTIONS = [
    ("r1", "我要做高处作业了，我不知道我这个作业是到底算几级，我应该遵守那些规定",
     ["高处作业", "坠落"]),
    ("r2", "我们买了一个有毒气体的探头，但是安装我不知道装什么位置比较合适",
     ["气体探测", "探测器", "报警器", "有毒气体"]),
    ("r3", "我们厂现在打算去重新修一个厂房，但是我不知道修这个厂房需要考虑哪些法律法规或者国家标准上的问题",
     ["建设项目", "安全设施", "厂房", "工业企业设计"]),
    ("r4", "我们施工的时候能不能关闭消防报警系统呢？那个国标法规上是怎么要求的",
     ["火灾自动报警", "消防", "报警系统"]),
    ("r5", "我们这个易制毒化学品仓库，到底要符合哪些要求才行？我怎么去自查有没有违规项",
     ["易制毒", "危险化学品", "储存", "仓库"]),
    ("r6", "我们企业是一般工贸企业，光刻机制造企业，在手续证照方面，我们要办哪些手续？安全环保的手续都要说",
     ["安全评价", "环境影响评价", "排污许可", "安全生产许可", "工贸"]),
    ("r7", "我们工厂里的岗位，哪些岗位要做职业健康体检，哪些不用这个东西，我怎么去判断",
     ["职业健康监护", "职业健康检查", "职业病危害"]),
    ("r8", "我们公司有些人，他不愿意参加职业健康体检，但是法律法规要求公司必须要给他们做体检，那这种情况冲突了怎么去解决呢",
     ["职业健康监护", "职业健康检查"]),
    ("r9", "如果说这个我们公司因为一些工艺调整，现在要增加一个职业危害因素，那我应该怎么去做才能保证不管是从现场还是体检还是其他方面都能合规呢",
     ["职业病危害", "现状评价", "危害因素"]),
    ("r10", "我要签租房合同，里面说这个我要半年一付，然后还要付一个月押金，如果我没有租满一年的话，押金不退，像这种条款是不是合法呢",
     ["租赁", "合同", "押金", "民法典"]),
    ("r11", "我看到有的企业和供应商签的安全协议里面说，如果是供应商因为自己违章导致的事故的，那甲方不负任何责任，这到底合不合法",
     ["安全生产协议", "承包", "供应商", "免责"]),
]


def main() -> int:
    from src.core.retrieval import embedder
    from src.core.storage.sqlite_db import load_vec_extension

    real = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    load_vec_extension(real)

    docs = real.execute("SELECT standard_no, standard_name FROM doc_meta").fetchall()
    print(f"[q] 库里标准 {len(docs)} 篇", flush=True)

    # 影子库（新模型）只读打开
    shadow = None
    if SHADOW.exists():
        shadow = sqlite3.connect(f"file:{SHADOW.as_posix()}?mode=ro", uri=True)
        load_vec_extension(shadow)
        print(f"[q] 影子库已开（新模型向量 {shadow.execute('SELECT COUNT(*) FROM clause_vec_qwen').fetchone()[0]} 条）",
              flush=True)

    out = []
    for qid, q, kws in QUESTIONS:
        # ① 主题命中：在**标准名**里找关键词
        hits = []
        for std, name in docs:
            nm = name or ""
            if any(k in nm for k in kws):
                hits.append({"standard_no": std, "standard_name": nm})
        # ② 旧模型：真库 clause_vec
        qv = embedder.embed_query(q)
        old = _knn(real, "clause_vec", qv, 5)
        # ③ 新模型：影子库 clause_vec_qwen（查询用 Qwen3）
        new = []
        if shadow is not None:
            new = _knn_shadow(shadow, q, 5)

        out.append({"id": qid, "query": q, "keywords": kws,
                    "catalog_hits_n": len(hits),
                    "catalog_hits_sample": hits[:12],
                    "old_model_top5": old, "new_model_top5": new})
        print(f"[q] {qid} 主题命中 {len(hits)} 篇 | 旧模型前5 {[r['std'] for r in old]}", flush=True)

    result = {
        "why": "业主给的 11 条真实提问；量『库里有没有这个主题的标准』（按标准名），并对比新旧模型返回",
        "catalog_size": len(docs),
        "note": ("关键词是本脚本手写的（见 QUESTIONS），命中只代表标准名含这些字；"
                 "『有没有』的最终判定是我的**人工判读**，证据一并给出。"),
        "questions": out,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    real.close()
    if shadow is not None:
        shadow.close()
    return 0


def _rows(conn, sql, args):
    return conn.execute(sql, args).fetchall()


def _knn(conn, table, qv, k):
    rows = _rows(conn, f"SELECT clause_revision_id FROM {table}"
                      " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
                 (array.array("f", qv).tobytes(), k))
    return _describe(conn, [r[0] for r in rows])


def _knn_shadow(conn, q, k):
    """影子库里用 **Qwen3** 嵌入查询（与 E4 同口径：不加指令前缀）。"""
    import torch
    from transformers import AutoModel, AutoTokenizer
    global _TOK, _MODEL
    try:
        _TOK, _MODEL
    except NameError:
        _TOK = AutoTokenizer.from_pretrained("Qwen/Qwen3-Embedding-0.6B", padding_side="left")
        _MODEL = AutoModel.from_pretrained("Qwen/Qwen3-Embedding-0.6B",
                                           dtype=torch.float16).to("cuda").eval()
    enc = _TOK([q], padding=True, truncation=True, max_length=512, return_tensors="pt").to("cuda")
    with torch.no_grad():
        o = _MODEL(**enc)
    v = torch.nn.functional.normalize(o.last_hidden_state[:, -1][:, :512], p=2, dim=1)
    blob = array.array("f", v[0].float().cpu().numpy()).tobytes()
    rows = _rows(conn, "SELECT clause_revision_id FROM clause_vec_qwen"
                      " WHERE embedding MATCH ? AND k = ? ORDER BY distance", (blob, k))
    return _describe(conn, [r[0] for r in rows])


def _describe(conn, ids):
    res = []
    for cid in ids:
        r = conn.execute(
            "SELECT dm.standard_no, dm.standard_name, cr.clause_number,"
            "       substr(coalesce(cr.content_text,''),1,60)"
            " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
            " WHERE cr.clause_revision_id=?", (cid,)).fetchone()
        if r:
            res.append({"std": r[0], "name": (r[1] or "")[:44], "no": r[2], "text": (r[3] or "").replace("\n", " ")})
    return res


if __name__ == "__main__":
    sys.exit(main())
