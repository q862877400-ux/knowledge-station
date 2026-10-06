"""部委互动问答 · **第 ② 步：把"在库"的部分做成考卷**（真问题 + 官方金标）。

## 为什么这个考卷比现有的强
现有 171 条考卷是**"看着条文反推问法"**造出来的 —— 仓里自己记着它是循环的、乐观的，
而且 gold **未经确认**。本脚本用**部委官方答复**当依据：
 · **问题**：真人真问（不做任何改写）；
 · **金标**：官方答复**点名的文件 + 条号** ⇒ **有官方依据，不是我们猜的**。

## 两档金标（如实分开，不混口径）
 · **T1 条级**：答复点名「文件 + 第X条」，且两者在我们库里都能定位 ⇒ **精确金标**；
 · **T2 标准级**：答复点名了在库的文件，但没给条号 ⇒ 金标到**标准**一级，
   只用来量"该标准有没有进前 N 名"，**不冒充条级**。

## 边界（写进产物）
 · 答复原话可能指的是一份**我们库里没有**的文件 ⇒ 这类进"补料清单"，**不进考卷**；
 · 答复是**参考性意见建议，不具有法定效力**（应急管理部留言须知原话）⇒ 金标是"官方这么答"，
   **不等于"法条唯一正解"**；
 · 抓取只读外部网页；真库只读。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\06-build-real-bench.py --pages 10
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
OUT_JSONL = HERE / "benchmark-real-v1.jsonl"
OUT_SUM = HERE / "benchmark-real-v1-summary.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
BASE = "https://www.mem.gov.cn/hd/gzly/hdhdly/"
ENTRY_RE = re.compile(r"\.\./lyhf/\d{6}/t\d{8}_\d+\.shtml")
DOC_RE = re.compile(r"《([^》]{3,60})》")
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
          "十": 10, "百": 100, "零": 0}


def cn2int(s: str) -> int | None:
    """把「十」「二十」「三十五」「一百零二」这类中文数字转成 int。"""
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total, cur = 0, 0
    for ch in s:
        v = CN_NUM.get(ch)
        if v is None:
            return None
        if v == 10:
            cur = (cur or 1) * 10
        elif v == 100:
            total += (cur or 1) * 100
            cur = 0
        else:
            cur = v
    return total + cur


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=10, help="抓多少页留言列表（每页 6 条）")
    args = ap.parse_args()
    os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

    import httpx
    from bs4 import BeautifulSoup

    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    # 库里标准名 → standard_no（用于把答复点名的文件落到具体标准上）
    std_rows = conn.execute("SELECT standard_no, standard_name FROM doc_meta").fetchall()
    lib = {}
    for no, nm in std_rows:
        if nm:
            lib[re.sub(r"[\s（）()《》]", "", nm)] = no

    # ⚠ 更正（2026-10-07，我自己踩的坑）：库里的 `clause_number` 存的是**中文数字**（`第十条`），
    #   而我第一版把它转成 `10` 去查 ⇒ **一条都对不上**，于是 T1（条级金标）报了 0。
    #   现在先把每个标准的条款号映射成「整数 → 库里原样写法」，再拿答复里的"第X条"去对。
    def clause_map(std_no: str) -> dict[int, str]:
        m = {}
        for (num,) in conn.execute(
                "SELECT cr.clause_number FROM clause_revision cr"
                " JOIN doc_meta dm ON dm.doc_id=cr.doc_id WHERE dm.standard_no=?", (std_no,)):
            # ⚠ 更正 2（我自己踩的）：库里是 `第二十一条`，第一版只去掉了「条」**没去「第」**
            #   ⇒ cn2int("第二十一") 遇到「第」直接返回 None ⇒ 条号永远对不上。
            v = cn2int(re.sub(r"[第条\s]", "", str(num or "")))
            if v:
                m.setdefault(v, num)
        return m

    _cmap: dict[str, dict[int, str]] = {}

    #: 这些词出现在库里文档名里 ⇒ 它**不是生效文件**（是征求意见稿/通知/公告的壳），
    #: 不能拿它当"官方点名的那个文件"
    NOT_OPERATIVE = ("征求意见", "通知", "公告", "公示", "解读")

    def find_std(docname: str) -> tuple[str | None, bool]:
        """→ (standard_no, 是否是"非生效文件")."""
        k = re.sub(r"[\s（）()《》]", "", docname)
        if k in lib:
            no = lib[k]
            weak = any(w in k for w in NOT_OPERATIVE)
            return no, weak
        for nm, no in lib.items():
            if len(k) >= 8 and (k in nm or nm in k):
                weak = any(w in nm for w in NOT_OPERATIVE)
                return no, weak
        return None, False

    links: list[str] = []
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        urls = [BASE] + [urljoin(BASE, f"index_{i}.shtml") for i in range(1, args.pages + 1)]
        for u in urls:
            try:
                t = cli.get(u).text
                for f in ENTRY_RE.findall(t):
                    if f not in links:
                        links.append(f)
            except Exception as e:                                      # noqa: BLE001
                print(f"[bench] 列表 {u} 失败 {type(e).__name__}", flush=True)
            time.sleep(1.2)
        print(f"[bench] 共 {len(links)} 条留言，逐条抓正文…", flush=True)

        raw = []
        for i, p in enumerate(links, 1):
            try:
                r = cli.get(urljoin(BASE, p))
                r.encoding = r.encoding or "utf-8"
                raw.append({"url": urljoin(BASE, p),
                            "text": BeautifulSoup(r.text, "html.parser").get_text("\n", strip=True)})
            except Exception as e:                                      # noqa: BLE001
                print(f"[bench] {i} 失败 {type(e).__name__}", flush=True)
            if i % 10 == 0:
                print(f"[bench] {i}/{len(links)}", flush=True)
            time.sleep(1.0)

    items, skipped = [], []
    for it in raw:
        t = it["text"]
        m_q = re.search(r"咨询[：:]\s*(.{10,800}?)(?:回复|答复)[：:]", t, re.S)
        m_a = re.search(r"(?:回复|答复)[：:]\s*(.{10,2000})", t, re.S)
        q = re.sub(r"\s+", " ", m_q.group(1)).strip() if m_q else ""
        a = re.sub(r"\s+", " ", m_a.group(1)).strip() if m_a else ""
        if not q or not a:
            skipped.append({"url": it["url"], "why": "解析不出问或答"})
            continue
        docs = [d.strip() for d in DOC_RE.findall(a)]
        pair = [(d, *find_std(d)) for d in docs]
        in_lib = [(d, no, weak) for d, no, weak in pair if no]
        # 第X条
        clause_nums = [cn2int(m) for m in re.findall(r"第([一二三四五六七八九十百零\d]{1,4})条", a)]
        clause_nums = [n for n in clause_nums if n]
        tiers = []
        for d, no, weak in in_lib:
            # T1：这个标准 + 答复给的任一条号，在库里都存在（**按库里原样的中文写法对**）
            cm = _cmap.setdefault(no, clause_map(no))
            for n in clause_nums:
                if n in cm:
                    hit = conn.execute(
                        "SELECT cr.clause_revision_id FROM clause_revision cr"
                        " JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
                        " WHERE dm.standard_no=? AND cr.clause_number=?", (no, cm[n])).fetchone()
                    if hit:
                        tiers.append({"tier": "T1", "doc": d, "standard_no": no, "weak_source": weak,
                                      "clause_number_in_library": cm[n],
                                      "cited_as": f"第{n}条", "gold_cr_id": hit[0]})
                        break
            else:
                tiers.append({"tier": "T2", "doc": d, "standard_no": no, "weak_source": weak,
                              "note": ("答复点名的这份文件在库里**只有征求意见稿/通知的壳**，不是生效文本"
                                       if weak else "答复点名了该文件但没给（或对不上）条号 ⇒ 只到标准级")})
        if tiers:
            items.append({"id": f"mem_{len(items)+1:03d}", "query": q, "url": it["url"],
                          "official_answer": a[:1200],
                          "cited_docs": docs, "gold": tiers,
                          "confirmed_by": "部委官方答复（参考性意见，不具法定效力）"})
        else:
            skipped.append({"url": it["url"], "why": "答复点名的文件都不在库（进补料清单）",
                            "query": q[:120], "cited_docs": docs})

    OUT_JSONL.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items),
                         encoding="utf-8")
    t1 = [x for x in items if any(g["tier"] == "T1" for g in x["gold"])]
    t2only = [x for x in items if not any(g["tier"] == "T1" for g in x["gold"])]
    # 补料清单：答复点名但不在库的文件
    missing = {}
    for it in raw:
        a = re.sub(r"\s+", " ", it["text"])
        for d in DOC_RE.findall(a):
            if not find_std(d.strip()):
                missing[d.strip()] = missing.get(d.strip(), 0) + 1
    summary = {
        "why": "业主指示第②步：把部委互动问答里『在库』的部分做成考卷（真问题 + 官方金标）",
        "source": "应急管理部 公众留言回复",
        "n_scraped_pages": args.pages,
        "n_entries": len(raw),
        "n_benchmark_items": len(items),
        "tiers": {"T1_条级金标": len(t1), "T2_仅标准级": len(t2only)},
        "n_skipped": len(skipped),
        "missing_docs_inventory": dict(sorted(missing.items(), key=lambda kv: -kv[1])[:40]),
        "boundary": [
            "答复是**参考性意见建议，不具有法定效力**（留言须知原话）⇒ 金标含义是『官方这么答』，"
            "不冒充『法条唯一正解』。",
            "T2 只到标准级，**不冒充条级**。",
            "来源只有应急管理部一家（其它部委入口另测）。",
        ],
        "skipped_sample": skipped[:10],
    }
    OUT_SUM.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("missing_docs_inventory", "skipped_sample")},
                     ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT_JSONL}\n已写 {OUT_SUM}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
