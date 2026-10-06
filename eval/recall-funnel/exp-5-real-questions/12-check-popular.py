"""核实热门法律项目**到底装了什么** —— 顶层目录、README、数据体积。

业主 2026-10-07："你说出来的这几个项目都星星很少，有没有比较热门的"。
按星数搜到后，本脚本逐个点开看内容（不靠简介）。

⚠ 搜索接口未带认证时有 10 次/分钟限速，上一轮有 3 个关键词吃到 403 —— 本轮补跑。

只读 API；不下载数据。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\12-check-popular.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "popular-law-repos-detail.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = {"User-Agent": "Mozilla/5.0"}

#: 按星数排序后，真正与"法律法规/判决数据"相关的
TARGETS = [
    ("RanKKI/LawRefBook", "中华人民共和国法律手册"),
    ("ImCa0/just-laws", "中国法律文库"),
    ("PKU-YuanGroup/ChatLaw", "中文法律大模型（北大）"),
    ("pengxiao-song/LaWGPT", "中文法律 LLaMA"),
    ("AndrewZhe/lawyer-llama", "中文法律 LLaMA"),
    ("zhang17173/Event-Extraction", "裁判文书事件抽取（含数据）"),
]
#: 上轮 403 的关键词，补跑
RETRY_QUERIES = ["法规 数据库", "legal judgment china", "law database china"]


def main() -> int:
    import httpx
    out = {"why": "业主打回星数太少 ⇒ 按星数搜到热门项目后，逐个点开看内容（不靠简介）",
           "targets": {}, "retry_search": {}}
    with httpx.Client(timeout=30, headers=UA, follow_redirects=True, trust_env=False) as cli:
        for repo, label in TARGETS:
            info = {"label": label}
            r = cli.get(f"https://api.github.com/repos/{repo}")
            if r.status_code == 200:
                d = r.json()
                info.update({"stars": d.get("stargazers_count"),
                             "license": (d.get("license") or {}).get("spdx_id"),
                             "size_kb": d.get("size"), "pushed_at": d.get("pushed_at"),
                             "desc": d.get("description")})
            top = cli.get(f"https://api.github.com/repos/{repo}/contents/")
            if top.status_code == 200:
                items = top.json()
                info["top_level"] = [{"name": x["name"], "type": x["type"],
                                      "mb": round((x.get("size") or 0) / 1e6, 2)} for x in items[:18]]
                # 找疑似数据目录并展开一层
                for x in items:
                    if x["type"] == "dir" and x["name"].lower() in (
                            "data", "content", "contents", "corpus", "dataset", "datasets",
                            "preview content", "laws", "json", "src"):
                        sub = cli.get(f"https://api.github.com/repos/{repo}/contents/{x['name']}")
                        if sub.status_code == 200:
                            kids = sub.json()
                            files = sum(1 for k in kids if k["type"] == "file")
                            dirs = [k["name"] for k in kids if k["type"] == "dir"]
                            info.setdefault("data_dirs", {})[x["name"]] = {
                                "files": files, "dirs": dirs[:10],
                                "mb": round(sum((k.get("size") or 0) for k in kids if k["type"] == "file") / 1e6, 2),
                                "sample": [k["name"] for k in kids[:6]],
                            }
            out["targets"][repo] = info
            print(f"[{repo}] ★{info.get('stars')} {info.get('license')} "
                  f"{info.get('size_kb')}KB pushed={str(info.get('pushed_at'))[:10]}", flush=True)
            for k, v in (info.get("data_dirs") or {}).items():
                print(f"      {k}/: {v['files']} 文件 + {len(v['dirs'])} 子目录, {v['mb']}MB, "
                      f"样例={v['sample']}", flush=True)

        for q in RETRY_QUERIES:
            try:
                r = cli.get("https://api.github.com/search/repositories",
                            params={"q": q, "sort": "stars", "order": "desc", "per_page": 8})
                if r.status_code == 200:
                    out["retry_search"][q] = [
                        {"full_name": i["full_name"], "stars": i["stargazers_count"],
                         "license": (i.get("license") or {}).get("spdx_id"),
                         "desc": (i.get("description") or "")[:110]}
                        for i in r.json().get("items", [])]
                    print(f"[retry] {q!r} → {len(out['retry_search'][q])} 条", flush=True)
                else:
                    print(f"[retry] {q!r} → HTTP {r.status_code}（限速）", flush=True)
            except Exception as e:                                          # noqa: BLE001
                print(f"[retry] {q!r} 失败 {type(e).__name__}", flush=True)
            time.sleep(7)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
