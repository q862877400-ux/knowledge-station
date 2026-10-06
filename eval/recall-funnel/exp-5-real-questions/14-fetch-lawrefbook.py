"""第 ① 步：把 LawRefBook 的法规数据**下下来**，看清结构。

业主 2026-10-07 指示："要" —— 下载它、与真库里那 386 篇法律/条例比对，出一张"缺哪些"清单。

 · 下载 `laws.zip`（约 8.26MB）与 `laws.meta` 到 `var/tmp/lawrefbook/`（**仓外临时目录，已 gitignore**）；
 · 只**看结构**（zip 里有哪些文件、什么格式、多少件），不改任何仓内数据、不碰真库。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\14-fetch-lawrefbook.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "lawrefbook-structure.json"
DEST = ROOT / "var" / "tmp" / "lawrefbook"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = {"User-Agent": "Mozilla/5.0"}


def main() -> int:
    import httpx
    DEST.mkdir(parents=True, exist_ok=True)
    got = {}
    with httpx.Client(timeout=120, headers=UA, follow_redirects=True, trust_env=False) as cli:
        for name in ("laws.zip", "laws.meta"):
            url = f"https://raw.githubusercontent.com/RanKKI/LawRefBook/master/{name}"
            try:
                r = cli.get(url)
                if r.status_code == 200:
                    (DEST / name).write_bytes(r.content)
                    got[name] = len(r.content)
                    print(f"[dl] {name} = {len(r.content)/1e6:.2f} MB", flush=True)
                else:
                    print(f"[dl] {name} → HTTP {r.status_code}", flush=True)
            except Exception as e:                                          # noqa: BLE001
                print(f"[dl] {name} 失败 {type(e).__name__}: {e}", flush=True)

    out = {"source": "RanKKI/LawRefBook (2458★)", "downloaded": got,
           "dest": str(DEST), "license_note": "仓库 SPDX=NOASSERTION；README 主张依《著作权法》第五条属公有领域"}

    zp = DEST / "laws.zip"
    if zp.exists():
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            print(f"[zip] 共 {len(names)} 项", flush=True)
            # 结构统计
            exts = {}
            for n in names:
                exts[Path(n).suffix.lower() or "(无后缀)"] = exts.get(Path(n).suffix.lower() or "(无后缀)", 0) + 1
            out["zip_entries"] = len(names)
            out["zip_exts"] = exts
            out["zip_sample"] = names[:20]
            print(f"[zip] 扩展名分布 = {exts}", flush=True)
            for n in names[:12]:
                print(f"      {n}", flush=True)
            # 抽第一个文件看格式
            first = next((n for n in names if not n.endswith("/")), None)
            if first:
                raw = z.read(first)
                try:
                    txt = raw.decode("utf-8")
                except UnicodeDecodeError:
                    txt = raw.decode("utf-8", "ignore")
                out["first_file"] = {"name": first, "chars": len(txt), "head": txt[:700]}
                print(f"\n[zip] 首个文件 {first} 前 700 字：\n{txt[:700]}", flush=True)

    if (DEST / "laws.meta").exists():
        t = (DEST / "laws.meta").read_text(encoding="utf-8", errors="ignore")
        out["laws_meta_head"] = t[:500]
        print(f"\n[laws.meta] 前 500 字：\n{t[:500]}", flush=True)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
