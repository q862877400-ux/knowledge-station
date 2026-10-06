"""第 ① 步（重试版）：把 `laws.zip` 下下来 —— **三个通道轮着试**。

上一版在 `raw.githubusercontent` 上被服务端断连（`RemoteProtocolError`）。
`laws.meta` 已证实文件存在：`filesize 8068`(KB) ≈ 8MB，hash `3357c47a…`，update 1745038962。

三条通道（谁通用谁）：
 ① `https://cdn.jsdelivr.net/gh/RanKKI/LawRefBook@master/laws.zip`（CDN，通常最稳）
 ② `https://api.github.com/repos/RanKKI/LawRefBook/contents/laws.zip` + `Accept: …raw`（走 api 域）
 ③ `https://raw.githubusercontent.com/RanKKI/LawRefBook/master/laws.zip`（原始，已知会抖）

落到 `var/tmp/lawrefbook/`（仓外临时目录，已 gitignore）；**不改仓内数据、不碰真库**。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\15-fetch-zip-retry.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "lawrefbook-structure.json"
DEST = ROOT / "var" / "tmp" / "lawrefbook"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = {"User-Agent": "Mozilla/5.0"}

CHANNELS = [
    ("jsdelivr", "https://cdn.jsdelivr.net/gh/RanKKI/LawRefBook@master/laws.zip", {}),
    ("api-raw", "https://api.github.com/repos/RanKKI/LawRefBook/contents/laws.zip",
     {"Accept": "application/vnd.github.raw"}),
    ("raw", "https://raw.githubusercontent.com/RanKKI/LawRefBook/master/laws.zip", {}),
]


def main() -> int:
    import httpx
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / "laws.zip"
    why = None
    with httpx.Client(timeout=180, headers=UA, follow_redirects=True, trust_env=False) as cli:
        for label, url, hdr in CHANNELS:
            for attempt in (1, 2):
                try:
                    r = cli.get(url, headers={**UA, **hdr})
                    if r.status_code == 200 and len(r.content) > 1_000_000:
                        target.write_bytes(r.content)
                        sha = hashlib.sha256(r.content).hexdigest()
                        print(f"[dl] ✓ 通道 {label}（第 {attempt} 次）= {len(r.content)/1e6:.2f} MB  sha256={sha[:16]}…",
                              flush=True)
                        why = None
                        break
                    print(f"[dl] 通道 {label} → HTTP {r.status_code}, {len(r.content)} 字节", flush=True)
                except Exception as e:                                      # noqa: BLE001
                    why = f"{label}: {type(e).__name__}: {e}"
                    print(f"[dl] 通道 {label} 第 {attempt} 次失败：{type(e).__name__}", flush=True)
                time.sleep(2)
            if why is None:
                break

    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    out["download"] = {"ok": why is None, "error": why,
                       "bytes": target.stat().st_size if target.exists() else 0,
                       "sha256": hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None}
    if target.exists():
        with zipfile.ZipFile(target) as z:
            names = z.namelist()
            exts: dict[str, int] = {}
            for n in names:
                e = Path(n).suffix.lower() or "(无后缀)"
                exts[e] = exts.get(e, 0) + 1
            out["zip_entries"] = len(names)
            out["zip_exts"] = exts
            out["zip_sample"] = names[:25]
            print(f"[zip] 共 {len(names)} 项；扩展名 = {exts}", flush=True)
            for n in names[:15]:
                print("      ", n, flush=True)
            first = next((n for n in names if not n.endswith("/")), None)
            if first:
                txt = z.read(first).decode("utf-8", "ignore")
                out["first_file"] = {"name": first, "chars": len(txt), "head": txt[:800]}
                print(f"\n[zip] 首个文件 {first}（{len(txt)} 字）前 800 字：\n{txt[:800]}", flush=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0 if why is None else 1


if __name__ == "__main__":
    sys.exit(main())
