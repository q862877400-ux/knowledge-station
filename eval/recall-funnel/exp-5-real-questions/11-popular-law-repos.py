"""按**星数**搜 GitHub —— 找到真正热门的中国法律法规/判决数据集项目。

## 为什么换方法（业主 2026-10-07 打回）
我先前用网页搜索找到的四个项目星数很低（8 / 0 / 2 / 1128）。
网页搜索给的是"被搜到的"，不是"最热门的"。**改成直接打 GitHub 官方搜索接口并 `sort=stars`。**

输出：跨多个关键词去重后的**按星数排序**清单，含 许可证 / 大小 / 最近更新 / 简介，
并标注"数据在仓库里 / 只给工具"（后者靠顶层目录名猜，会写明是猜的）。

只读 API；不下载数据。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\11-popular-law-repos.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "popular-law-repos.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = {"User-Agent": "Mozilla/5.0"}

QUERIES = [
    "法律法规", "中国法律", "法律 数据集", "裁判文书", "法律条文",
    "民法典", "判决书", "司法解释", "chinese law", "china law dataset",
    "法规 数据库", "legal judgment china",
]


def main() -> int:
    import httpx
    seen: dict[str, dict] = {}
    with httpx.Client(timeout=30, headers=UA, follow_redirects=True, trust_env=False) as cli:
        for q in QUERIES:
            try:
                r = cli.get("https://api.github.com/search/repositories",
                            params={"q": q, "sort": "stars", "order": "desc", "per_page": 15})
                if r.status_code != 200:
                    print(f"[search] {q!r} → HTTP {r.status_code}", flush=True)
                    time.sleep(2)
                    continue
                items = r.json().get("items", [])
                print(f"[search] {q!r} → {len(items)} 条", flush=True)
                for it in items:
                    full = it["full_name"]
                    if full in seen:
                        continue
                    seen[full] = {
                        "full_name": full,
                        "stars": it.get("stargazers_count"),
                        "license": (it.get("license") or {}).get("spdx_id"),
                        "size_kb": it.get("size"),
                        "pushed_at": it.get("pushed_at"),
                        "archived": it.get("archived"),
                        "language": it.get("language"),
                        "desc": (it.get("description") or "")[:150],
                        "found_by": [q],
                    }
                time.sleep(2)          # 搜索接口限速：不加认证 10 次/分钟
            except Exception as e:                                          # noqa: BLE001
                print(f"[search] {q!r} 失败 {type(e).__name__}", flush=True)

    ranked = sorted(seen.values(), key=lambda x: -(x["stars"] or 0))
    # 只对前 12 名展开顶层目录，看"数据在不在仓库里"
    with httpx.Client(timeout=30, headers=UA, follow_redirects=True, trust_env=False) as cli:
        for x in ranked[:12]:
            try:
                r = cli.get(f"https://api.github.com/repos/{x['full_name']}/contents/")
                if r.status_code == 200:
                    names = [i["name"] for i in r.json()][:14]
                    x["top_level"] = names
                    dataish = {"data", "content", "contents", "corpus", "dataset", "datasets",
                               "json", "sqlite", "db", "txt", "raw"}
                    x["data_in_repo_guess"] = bool(dataish & {n.lower() for n in names})
            except Exception as e:                                          # noqa: BLE001
                x["contents_error"] = type(e).__name__
            time.sleep(1.0)

    OUT.write_text(json.dumps({
        "why": "业主打回：先前找到的项目星数低；本清单按 GitHub 官方搜索接口 sort=stars 取，跨 12 个关键词去重",
        "note": "`data_in_repo_guess` 是**按顶层目录名猜的**，不是实证（实证见 where-is-the-data.json）",
        "n_repos": len(ranked), "repos": ranked,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n共 {len(ranked)} 个去重项目。按星数前 20：\n")
    for x in ranked[:20]:
        print(f"  ★{x['stars']:>6}  {x['full_name']:<46} {str(x['license']):<12} "
              f"{x['size_kb']:>8}KB  {str(x['pushed_at'])[:10]}")
        print(f"          {x['desc'][:110]}")
        if x.get("top_level"):
            print(f"          顶层: {', '.join(x['top_level'][:10])}"
                  f"  {'【疑似含数据】' if x.get('data_in_repo_guess') else ''}")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
