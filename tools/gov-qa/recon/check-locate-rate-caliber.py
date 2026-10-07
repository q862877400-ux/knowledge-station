"""核 `locate-rate.json` 的口径：**A=3,868 这个数有多少是靠"宽松兜底"来的？**

## 为什么要核
`measure-locate-rate.py` 的 `find_std()` 是**精确命中 → 宽松兜底（≥8 字允许包含匹配）**两级。
上一版我正是被"包含匹配"骗过（把司法解释当成了民法典本体）。
⇒ **必须把两级分开统计，并抽样看兜底级的假阳性。**

## 做法
完全复刻它的 `norm` 与两级 `find_std`，**逐通道条目**统计：
 · 精确命中多少条；
 · **只靠兜底命中的多少条（这部分是风险区）**；
 · 抽样 30 条兜底命中，人读对不对得上。

只读。输出 `tools/gov-qa/recon/locate-rate-caliber-check.json`。
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "tools" / "gov-qa" / "data"
OUT = ROOT / "tools" / "gov-qa" / "recon" / "locate-rate-caliber-check.json"

# 与 measure-locate-rate.py 逐字一致
DOC_RE = re.compile(r"《([^《》]{4,60})》")
STD_RE = re.compile(r"(GB(?:/T)?\s?\d{3,5}(?:\.\d+)?\s?[-—]\s?\d{4}|"
                    r"[A-Z]{2,4}(?:/T)?\s?\d{3,5}(?:\.\d+)?\s?[-—]\s?\d{4})")


def norm(s: str) -> str:
    return re.sub(r"[\s（）()《》]", "", s or "")


def load_lib(db: Path) -> dict[str, str]:
    c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    out = {}
    for no, nm in c.execute("SELECT standard_no, standard_name FROM doc_meta"):
        if nm:
            out[norm(nm)] = no
    c.close()
    return out


def find_std2(lib: dict[str, str], name: str) -> tuple[str | None, str]:
    """返回 (命中号, 哪一级)：exact / loose / miss。"""
    k = norm(name)
    if k in lib:
        return lib[k], "exact"
    for nm, no in lib.items():
        if len(k) >= 8 and (k in nm or nm in k):
            return no, "loose"
    return None, "miss"


def main() -> int:
    db = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
    lib = load_lib(db)
    print(f"[cc] 库 {len(lib)} 个标准名（只读）")

    stat = {"items": 0, "cited_all": 0, "exact": 0, "loose": 0, "miss": 0}
    A_exact = A_loose = 0
    A_onlyloose = 0
    samples: list[dict] = []
    for f in sorted(DATA.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            stat["items"] += 1
            ans = r.get("answer") or ""
            names = DOC_RE.findall(ans) + STD_RE.findall(ans)
            has_exact = has_loose = False
            for nm in names:
                stat["cited_all"] += 1
                no, lvl = find_std2(lib, nm)
                stat[lvl] += 1
                if lvl == "exact":
                    has_exact = True
                elif lvl == "loose":
                    has_loose = True
                    if len(samples) < 30:
                        samples.append({"name": nm, "lib_no": no, "src": f.stem})
            if has_exact:
                A_exact += 1
            elif has_loose:
                A_loose += 1
                A_onlyloose += 1
    n = stat["items"]
    print(f"\n[cc] 提问 {n} 条 ｜ 抽出点名 {stat['cited_all']} 个")
    print(f"[cc] 匹配分级：精确 {stat['exact']} ｜ 宽松兜底 {stat['loose']} ｜ 未命中 {stat['miss']}")
    print(f"[cc] 条目级：**至少一个精确命中** {A_exact} ｜ **只靠宽松兜底** {A_onlyloose}")
    print(f"\n[cc] ⇒ 原报告的 A=3868 里，**纯靠兜底**的有 {A_onlyloose} 条 "
          f"（占 {A_onlyloose / max(1, A_exact + A_onlyloose):.1%}）")
    print(f"[cc] ⇒ **去掉兜底后**的 A（保守值）= {A_exact}")
    print("\n[cc] 兜底命中抽样 30 条（人读对不对得上）：")
    for s in samples:
        print(f"    「{s['name'][:40]}」 → {s['lib_no']}   [{s['src']}]")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "why": "核 locate-rate 的 A=3868 有多少靠宽松兜底（≥8字包含匹配）",
        "items": n, "cited_all": stat["cited_all"],
        "match_level": {"exact": stat["exact"], "loose": stat["loose"], "miss": stat["miss"]},
        "A_has_exact": A_exact, "A_only_loose": A_onlyloose,
        "A_report_value": 3868, "A_conservative": A_exact,
        "samples_loose": samples,
        "boundary": ["口径=从答复正则抽《》文件名与标准号；抽不到不等于没依据",
                     "只读；未改任何生产件"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
