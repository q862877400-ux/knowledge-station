"""核实这几个开源法律库：**数据是不是真的拿得到**（不只看 README 的说法）。

只读 GitHub 公开 API / raw 文件；不下载大文件、不写入仓库。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\09-verify-law-repos.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "law-repos-verified.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = {"User-Agent": "Mozilla/5.0"}

REPOS = {
    "Li2zon3/law-crawler-unified": "爬虫（国家法律法规库/规章库/条约库）",
    "gzx5418/lvyan-lawtext": "数据仓库（法律/司法解释 markdown）",
    "thu-lawyer/china-law-mcp": "条目库 + 引用核验（SQLite 随仓库）",
    "cncases/cases": "裁判文书本地搜索（数据走 BT）",
}


def main() -> int:
    import httpx
    out = {"why": "业主要找『把法律法规与判决全扒下来公开下载』的开源项目；本脚本核实数据是否真能拿到",
           "repos": {}}
    with httpx.Client(timeout=30, headers=UA, follow_redirects=True, trust_env=False) as cli:
        for repo, desc in REPOS.items():
            info = {"desc": desc}
            try:
                r = cli.get(f"https://api.github.com/repos/{repo}")
                if r.status_code == 200:
                    d = r.json()
                    info.update({"license": (d.get("license") or {}).get("spdx_id"),
                                 "stars": d.get("stargazers_count"),
                                 "size_kb": d.get("size"),
                                 "pushed_at": d.get("pushed_at"),
                                 "archived": d.get("archived"),
                                 "language": d.get("language")})
                else:
                    info["api_status"] = r.status_code
            except Exception as e:                                          # noqa: BLE001
                info["api_error"] = f"{type(e).__name__}: {e}"

            # 顶层文件清单：看"数据在不在仓库里"
            try:
                r = cli.get(f"https://api.github.com/repos/{repo}/contents/")
                if r.status_code == 200:
                    items = r.json()
                    info["top_level"] = [{"name": x["name"], "type": x["type"],
                                          "size_kb": round((x.get("size") or 0) / 1024, 1)}
                                         for x in items[:16]]
            except Exception as e:                                          # noqa: BLE001
                info["contents_error"] = f"{type(e).__name__}"
            out["repos"][repo] = info
            print(f"[{repo}] license={info.get('license')} stars={info.get('stars')} "
                  f"size={info.get('size_kb')}KB pushed={info.get('pushed_at')}", flush=True)
            for x in info.get("top_level", [])[:10]:
                print(f"      {x['type']:4s} {x['size_kb']:>9}KB  {x['name']}", flush=True)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
