"""追查两个"热门且可能有全量数据"的项目：LawRefBook(2458★) 与 just-laws(781★, MIT)。

发现（前一轮）：星最多的几个其实是**大模型项目**，`data/` 只是 demo：
 · ChatLaw 7615★ → `data/` 仅 0.07MB
 · LaWGPT  6057★ → `data/` 只有一个 `.gitkeep`（空的）
本脚本追两个**可能真装全量法规**的：LawRefBook（顶层有 `.gitmodules`）、just-laws（MIT、近期更新）。

⚠ 上一版在 raw.githubusercontent 上吃到 `RemoteProtocolError`（服务端断连）⇒ 本版每个请求都容错 + 重试 + 双分支名。

只读 API。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\13-chase-two.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "chase-two-repos.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = {"User-Agent": "Mozilla/5.0"}


def main() -> int:
    import httpx
    out = {"why": "追查是否有『热门 + 真装全量法规数据』的项目"}

    def get(cli, url, tries=3, **kw):
        for i in range(tries):
            try:
                return cli.get(url, **kw)
            except Exception as e:                                          # noqa: BLE001
                if i == tries - 1:
                    return {"_error": f"{type(e).__name__}: {e}", "status_code": 0}
                time.sleep(1.5 * (i + 1))
        return {"_error": "unreachable", "status_code": 0}

    with httpx.Client(timeout=30, headers=UA, follow_redirects=True, trust_env=False) as cli:
        print("=== RanKKI/LawRefBook (2458★) ===", flush=True)
        for br in ("main", "master"):
            r = get(cli, f"https://raw.githubusercontent.com/RanKKI/LawRefBook/{br}/.gitmodules")
            if getattr(r, "status_code", 0) == 200:
                out["LawRefBook_gitmodules"] = r.text
                print(f"  .gitmodules ({br}):\n{r.text[:500]}", flush=True)
                break
        else:
            print("  .gitmodules 没取到", flush=True)

        # 用 API 列顶层（API 比 raw 稳）
        r = get(cli, "https://api.github.com/repos/RanKKI/LawRefBook/contents/")
        if getattr(r, "status_code", 0) == 200:
            top = [{"name": x["name"], "type": x["type"],
                    "mb": round((x.get("size") or 0) / 1e6, 2)} for x in r.json()]
            out["LawRefBook_top"] = top
            print("  顶层：", [(x["name"], x["type"], x["mb"]) for x in top], flush=True)

        print("\n=== ImCa0/just-laws (781★, MIT) ===", flush=True)
        for path in ("data", "data/criminal-offenses", "data/laws", "src"):
            r = get(cli, f"https://api.github.com/repos/ImCa0/just-laws/contents/{path}")
            if getattr(r, "status_code", 0) != 200:
                continue
            kids = r.json()
            if not isinstance(kids, list):
                continue
            files = [k for k in kids if k["type"] == "file"]
            dirs = [k["name"] for k in kids if k["type"] == "dir"]
            mb = round(sum((k.get("size") or 0) for k in files) / 1e6, 2)
            print(f"  {path}/: {len(files)} 文件 + {len(dirs)} 子目录 ({mb}MB) 子目录={dirs[:12]}", flush=True)
            out.setdefault("just_laws", {})[path] = {
                "sample_files": [k["name"] for k in files[:8]], "dirs": dirs[:12], "mb": mb}
            if dirs:
                deep = get(cli, f"https://api.github.com/repos/ImCa0/just-laws/contents/{path}/{dirs[0]}")
                if getattr(deep, "status_code", 0) == 200 and isinstance(deep.json(), list):
                    names = [k["name"] for k in deep.json()[:8]]
                    print(f"      → {path}/{dirs[0]}/ 里: {names}", flush=True)
                    out["just_laws"][f"{path}/{dirs[0]}"] = names
            time.sleep(0.8)

        # README（用 API 取，避免 raw 断连）
        for repo in ("RanKKI/LawRefBook", "ImCa0/just-laws"):
            r = get(cli, f"https://api.github.com/repos/{repo}/readme",
                    headers={**UA, "Accept": "application/vnd.github.raw"})
            if getattr(r, "status_code", 0) == 200 and isinstance(getattr(r, "text", None), str):
                head = r.text[:900]
                out[f"{repo}_readme_head"] = head
                print(f"\n--- {repo} README 前 12 行 ---", flush=True)
                for line in head.splitlines()[:12]:
                    if line.strip():
                        print("   ", line.strip()[:130], flush=True)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
