"""真问题探针 · 第二步：**逐主题查库里的覆盖**（这决定"该不该再加 3 万本"）。

上一步只用了每题随手写的几个关键词。这一步换成**逐主题精确查标准名**，
把"库里到底有没有这个主题的标准"问清楚 —— 这是"加语料有没有用"的直接证据。

⚠ 只查**标准名**（6,797 条），不查条文正文 —— 因为要回答的是"库里有没有这个**主题的文档**"。
⚠ 命中数只是"名字里有这些字"，**最终判读是我的**，证据一并给出。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\02-topic-coverage.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
OUT = HERE / "topic-coverage.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

#: 主题 → 该主题在标准名里可能出现的字
TOPICS = {
    "高处作业/特种作业": ["高处作业", "特种作业", "坠落"],
    "气体检测报警（探头安装）": ["气体检测", "检测报警", "探测", "报警器"],
    "建设项目安全设施/设计规范": ["建设项目", "安全设施", "建筑设计防火", "工业企业设计"],
    "消防（报警系统/施工）": ["火灾自动报警", "消防"],
    "易制毒化学品": ["易制毒"],
    "危险化学品（储存/仓库）": ["危险化学品", "储存"],
    "工贸企业手续/证照": ["安全生产许可", "排污许可", "环境影响评价", "安全评价", "工贸"],
    "职业健康监护/体检": ["职业健康监护", "职业健康检查"],
    "职业病危害评价/危害因素": ["职业病危害", "危害因素", "职业病"],
    "民法典/合同/租赁": ["民法典", "合同", "租赁"],
    "安全生产协议/发包承包": ["安全生产协议", "发包", "承包", "相关方"],
}


def main() -> int:
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    docs = c.execute("SELECT standard_no, standard_name FROM doc_meta").fetchall()
    print(f"[cov] 库里标准 {len(docs)} 篇\n")

    out = {"catalog_size": len(docs), "topics": {}}
    for topic, kws in TOPICS.items():
        hits = [(s, n) for s, n in docs if any(k in (n or "") for k in kws)]
        out["topics"][topic] = {
            "keywords": kws, "n_hits": len(hits),
            "samples": [{"std": s, "name": (n or "")[:60]} for s, n in hits[:14]],
        }
        print(f"=== {topic}  → 命中 {len(hits)} 篇")
        for s, n in hits[:8]:
            print(f"     {s}  {(n or '')[:56]}")
        if len(hits) > 8:
            print(f"     …另有 {len(hits)-8} 篇")
        print()

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写 {OUT}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
