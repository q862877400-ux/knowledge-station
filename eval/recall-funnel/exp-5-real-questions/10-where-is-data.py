"""把"数据到底在不在仓库里"**点开看** —— 逐个目录列清单，不靠 README 说法。

业主 2026-10-07 追问："这些项目难道不是把现有数据直接挂上的？还是只给了工具、真实数据没给？"
本脚本用 GitHub 公开 API 逐层展开目录 + 查 releases（发布附件里可能挂大文件），给出**实证**。

只读 API；不下载数据。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\10-where-is-data.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "where-is-the-data.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = {"User-Agent": "Mozilla/5.0"}

#: (仓库, 要展开的数据目录)
TARGETS = [
    ("gzx5418/lvyan-lawtext", "content"),
    ("thu-lawyer/china-law-mcp", "data"),
    ("Li2zon3/law-crawler-unified", None),
    ("cncases/cases", None),
]


def main() -> int:
    import httpx
    out = {"why": "业主要问清楚：这些开源项目是『挂了数据』还是『只给工具』", "repos": {}}
    with httpx.Client(timeout=30, headers=UA, follow_redirects=True, trust_env=False) as cli:

        def listdir(repo: str, path: str = "") -> list:
            r = cli.get(f"https://api.github.com/repos/{repo}/contents/{path}")
            return r.json() if r.status_code == 200 else []

        for repo, datadir in TARGETS:
            info = {}
            if datadir:
                top = listdir(repo, datadir)
                # 递归展开两层，数文件、累加大小
                files, size, subdirs = 0, 0, []
                for x in top:
                    if x["type"] == "dir":
                        subdirs.append(x["name"])
                        for y in listdir(repo, f"{datadir}/{x['name']}"):
                            if y["type"] == "file":
                                files += 1
                                size += y.get("size") or 0
                            elif y["type"] == "dir":
                                for z in listdir(repo, f"{datadir}/{x['name']}/{y['name']}"):
                                    if z["type"] == "file":
                                        files += 1
                                        size += z.get("size") or 0
                    elif x["type"] == "file":
                        files += 1
                        size += x.get("size") or 0
                info["datadir"] = datadir
                info["subdirs"] = subdirs[:20]
                info["n_files_2levels"] = files
                info["total_mb_2levels"] = round(size / 1e6, 2)
                info["sample_top"] = [{"name": x["name"], "type": x["type"],
                                       "kb": round((x.get("size") or 0) / 1024, 1)} for x in top[:8]]

            # releases（大文件常挂在这里）
            r = cli.get(f"https://api.github.com/repos/{repo}/releases")
            rel = r.json() if r.status_code == 200 else []
            info["n_releases"] = len(rel) if isinstance(rel, list) else None
            info["release_assets"] = [
                {"tag": x.get("tag_name"), "name": a.get("name"),
                 "mb": round((a.get("size") or 0) / 1e6, 1)}
                for x in (rel if isinstance(rel, list) else [])[:3] for a in x.get("assets", [])[:6]
            ]
            out["repos"][repo] = info
            print(f"[{repo}] datadir={datadir} 文件数(2层)={info.get('n_files_2levels')} "
                  f"合计={info.get('total_mb_2levels')}MB releases={info.get('n_releases')}", flush=True)
            for s in info.get("sample_top", []):
                print(f"      {s['type']:4s} {s['kb']:>9}KB  {s['name']}", flush=True)
            for a in info.get("release_assets", [])[:4]:
                print(f"      release {a['tag']}: {a['name']}  {a['mb']}MB", flush=True)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
