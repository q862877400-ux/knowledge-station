"""复核法规重入结果：**条数对不对 + 正文还带不带文件头**（目标第 ② 步）。

## 判据（都是可核的）
 · **条数**：与公开事实的**真实条数**对照（不是我定的）——
   劳动合同法 **98**、劳动法 **107**、行政处罚法 **86**、社会保险法 **98**、
   特种设备安全法 **101**、环境保护法 **70**、矿山安全法 **50**、职业病防治法 **90**、
   刑法 **452**（注意：刑法含目录与修正案，可能偏高）。
 · **正文**：不该再出现「全国人民代表大会常务委员会…会议通过/修正」这类**立法沿革**，
   也不该以「# 中华人民共和国XX法」开头（那是文件头）。

只读副本；不写任何东西。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\41-verify-law-counts.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "verify-law-counts.json"
sys.path.insert(0, str(ROOT))          # 让 `import src.*` 生效
TRIAL = ROOT / "var" / "tmp" / "ingest-trial" / "data" / "database" / "knowledge.db"

#: 公开事实的真实条数（用于判切分准不准）
TRUTH = {"劳动合同法": 98, "劳动法": 107, "行政处罚法": 86, "社会保险法": 98,
         "特种设备安全法": 101, "环境保护法": 70, "矿山安全法": 50, "职业病防治法": 90}

#: 文件头特征（不该出现在条文正文里）
FRONT_PAT = re.compile(r"会议通过|会议修正|<!--\s*INFO\s*END")


def main() -> int:
    c = sqlite3.connect(f"file:{TRIAL.as_posix()}?mode=ro", uri=True)
    c.execute("PRAGMA busy_timeout=30000")
    total = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("doc_meta", "clause_revision")}
    from src.core.storage.sqlite_db import load_vec_extension
    load_vec_extension(c)
    total["clause_vec"] = c.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    print(f"[v] 副本现状：{total}", flush=True)

    rows = c.execute(
        "SELECT doc_id, standard_no, standard_name FROM doc_meta"
        " WHERE file_path LIKE 'lawrefbook://%'").fetchall()
    print(f"[v] 已重入的法规 = {len(rows)} 篇\n", flush=True)

    hits, miss = [], []
    for name, truth in TRUTH.items():
        r = next((x for x in rows if x[2] == name or (x[2] or "").startswith(name)), None)
        if not r:
            miss.append({"name": name, "真实": truth, "库里": None})
            continue
        n = c.execute("SELECT COUNT(*) FROM clause_revision WHERE doc_id=?", (r[0],)).fetchone()[0]
        hits.append({"name": name, "真实": truth, "库里": n, "差": n - truth,
                     "标准号": r[1]})
    print(f"[v] 与真实条数对照：")
    for h in hits:
        flag = "✅" if h["差"] == 0 else ("≈" if abs(h["差"]) <= 3 else "⚠")
        print(f"    {flag} {h['name']:14s} 真实 {h['真实']:>4d}  库里 {h['库里']:>4d}  差 {h['差']:+d}")
    for m in miss:
        print(f"    ⛔ {m['name']}：库里没找到")
    exact = sum(1 for h in hits if h["差"] == 0)
    near = sum(1 for h in hits if abs(h["差"]) <= 3)
    print(f"\n    ⇒ 完全一致 {exact}/{len(hits)}；差 ≤3 的 {near}/{len(hits)}")

    # 文件头检查：抽 8 部看第一条正文
    print(f"\n[v] 条文正文是否还带文件头（抽 8 部看第一条）：")
    bad = 0
    samples = []
    for r in rows[:8]:
        row = c.execute(
            "SELECT clause_number, substr(content_text,1,90) FROM clause_revision"
            " WHERE doc_id=? ORDER BY rowid LIMIT 1", (r[0],)).fetchone()
        if not row:
            continue
        txt = (row[1] or "").replace("\n", " ")
        has = bool(FRONT_PAT.search(txt))
        bad += has
        samples.append({"name": (r[2] or "")[:30], "no": row[0], "text": txt,
                        "has_front_matter": has})
        print(f"    {'⚠ 带文件头' if has else '✅ 干净'}  [{(r[2] or '')[:22]}] {row[0]} → {txt[:70]}")
    print(f"\n    ⇒ 抽到的 {len(samples)} 部里，带文件头的 = {bad}")

    OUT.write_text(json.dumps({
        "why": "复核法规重入：条数是否与真实吻合 + 正文是否还带文件头",
        "totals": total, "law_docs": len(rows),
        "count_check": hits, "not_found": miss,
        "exact": exact, "within3": near,
        "front_matter": {"checked": len(samples), "with_front_matter": bad, "samples": samples},
        "boundary": ["条数对照的真实值来自公开事实；只读副本，未写任何东西。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
