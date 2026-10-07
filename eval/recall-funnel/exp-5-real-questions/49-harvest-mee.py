"""部委问答扩采 · 第 6 步：**把生态环境部「常见问题」158 条取下来并量两个比例**。

## 依据（上一步实测）
 `https://www.mee.gov.cn/was5/web/search?channelid=232534&perpage=100&page=N` 返回结构化 JSON，
 `recordCount = 158`；字段 = `doctitle / doccontent / lxrq / hfrq / docpuburl / hfdw / recid`。
 **没有"依据文件名"字段** ⇒ 得从**答复正文** `doccontent` 里抽《…》与标准号。

## 量什么（与应急管理部那次同口径，便于合并）
 · **a 可定位率**：答复里**点名了文件或标准号**的比例（决定它能不能当金标线索）；
 · **其中还带「第X条」条号**的比例（更硬）；
 · **c 在库率**：点名的文件**在我们生产库里能不能查到**（能 ⇒ 可当考卷；不能 ⇒ 补料清单）。

## 礼貌抓取
 158 条 / 每页 100 ⇒ **只 2 次请求**，间隔 3 秒。只读，不写库。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\49-harvest-mee.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "harvest-mee-faq.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
URL = "https://www.mee.gov.cn/was5/web/search"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

DOC_RE = re.compile(r"《([^》]{3,60})》")
STD_RE = re.compile(r"(GB(?:/T|/Z)?\s?\d{3,5}(?:\.\d+)?\s?[—\-]\s?\d{2,4})")
CLAUSE_RE = re.compile(r"第[一二三四五六七八九十百零\d]{1,4}条")


def norm(s: str) -> str:
    return re.sub(r"[\s（）()《》]", "", s or "")


def main() -> int:
    import httpx
    items = []
    with httpx.Client(timeout=40, headers={"User-Agent": UA, "Referer": "https://www.mee.gov.cn/hdjl/"},
                      follow_redirects=True, trust_env=False) as cli:
        for page in (1, 2):
            r = cli.get(URL, params={"channelid": "232534", "orderby": "-DOCRELTIME",
                                     "keyword": "", "page": str(page), "perpage": "100"})
            j = r.json()
            got = j.get("items") or []
            print(f"[h] 第 {page} 页 HTTP {r.status_code}  拿到 {len(got)} 条  "
                  f"（recordCount={j.get('recordCount')}）", flush=True)
            items.extend(got)
            if len(got) < 100:
                break
            time.sleep(3)
    # 去重
    seen, uniq = set(), []
    for it in items:
        k = it.get("recid") or it.get("docpuburl")
        if k and k not in seen:
            seen.add(k)
            uniq.append(it)
    print(f"[h] 去重后 {len(uniq)} 条", flush=True)

    # 库里标准名/标准号索引（判在库率）
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    lib = {}
    for no, nm in c.execute("SELECT standard_no, standard_name FROM doc_meta"):
        if nm:
            lib[norm(nm)] = no
    c.close()

    def find_std(name: str):
        k = norm(name)
        if k in lib:
            return lib[k]
        for nm, no in lib.items():
            if len(k) >= 8 and (k in nm or nm in k):
                return no
        return None

    NOT_OPER = ("征求意见", "通知", "公告", "公示", "解读")
    rows, a_ok, a_clause, cited_all, cited_in = 0, 0, 0, 0, 0
    for it in uniq:
        ans = it.get("doccontent") or ""
        docs = [d for d in DOC_RE.findall(ans)]
        stds = STD_RE.findall(ans)
        hit = None
        for d in docs:
            no = find_std(d)
            cited_all += 1
            if no:
                cited_in += 1
                hit = hit or {"kind": "doc", "name": d, "lib_no": no,
                              "weak": any(w in d for w in NOT_OPER)}
        for s in stds:
            no = find_std(s)
            cited_all += 1
            if no:
                cited_in += 1
                hit = hit or {"kind": "std", "name": s, "lib_no": no, "weak": False}
        has_doc = bool(docs or stds)
        has_clause = bool(CLAUSE_RE.search(ans))
        a_ok += has_doc
        a_clause += has_doc and has_clause
        rows += 1
        it["_docs"] = docs[:4]
        it["_hit"] = hit

    n = max(1, rows)
    res = {
        "why": "生态环境部「常见问题」158 条的扩采与两个比例（与应急管理部同口径）",
        "source": "www.mee.gov.cn/was5/web/search?channelid=232534",
        "n_items": rows,
        "a_可定位率": {"点名了文件或标准号的": f"{a_ok}/{n}",
                       "其中还出现『第X条』条号的": f"{a_clause}/{n}"},
        "c_在库率": {"答复点名的文件/标准总数": cited_all,
                     "在我们库里能对上的": f"{cited_in}/{cited_all}" if cited_all else "0/0"},
        "samples": [{"title": (it.get("doctitle") or "")[:60],
                     "docs": it.get("_docs"), "hit": it.get("_hit"),
                     "ans": (it.get("doccontent") or "")[:110]} for it in uniq[:8]],
        "boundary": ["环境部回复常是政策性表述，未必点名条文；本统计按《…》与标准号正则抽取。",
                     "只读；未写库。礼貌抓取（2 次请求）。"],
    }
    OUT.write_text(json.dumps({**res, "items": uniq[:60]}, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print(json.dumps(res, ensure_ascii=False, indent=1)[:1800])
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
