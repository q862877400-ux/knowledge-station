"""江西数融站群 —— 省直部门站点（webSiteCode）× 候选栏目（channelCode）探测。

背景：`recon/jx-config.js` 的 `aggregationWebsiteCod` 列了 **34 个省直部门站点代号**
（如 `jxjyw`=省教育厅、`jxssthjt`=省生态环境厅…），但各站互动栏目代号未知。
jx-zf 只接了省政府站（jxsrmzf）的 wxszj/hygz 两栏。

本脚本：对每个 webSiteCode 试一组通用栏目代号，只报 total>0 的命中。
只探测、只打印（落 recon/jx-dept-probe.json），**不落盘语料、不改共享文件**。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))

import httpx  # noqa: E402

HOST = "https://www.jiangxi.gov.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAUSE = 1.5
OUT = HERE / "jx-dept-probe.json"

#: 通用互动栏目代号候选（含 jxsrmzf 已证实有效的 wxszj/hygz，及 zxft 等）
CHANNELS = ["wxszj", "hygz", "zxft", "hdjl", "wszx", "zxxx", "zmhd", "zjdc",
            "yjzj", "gzly", "lyxd", "zxly", "tsjb", "wtzx", "zxzx", "zjzj",
            "xxzx", "zxts", "hydt", "jygz", "ldxx", "sjxx", "qyxx", "zjhd"]


def load_depts() -> list[dict]:
    cfg = (HERE / "jx-config.js").read_text(encoding="utf-8", errors="replace")
    out = []
    for m in re.finditer(r"websiteCod\s*:\s*'([^']+)'.*?domain\s*:\s*'([^']+)'"
                         r".*?websiteName\s*:\s*'([^']+)'", cfg, re.S):
        out.append({"code": m.group(1), "domain": m.group(2), "name": m.group(3)})
    return out


def query(cli: httpx.Client, web_site: str, channel: str) -> tuple[int | None, int]:
    data = {"current": 1, "pageSize": 5,
            "channelCode": [channel], "webSiteCode": [web_site]}
    try:
        r = cli.post(HOST + "/queryList", data=data,
                     headers={"User-Agent": UA, "Referer": HOST + "/"})
    except Exception as e:                                              # noqa: BLE001
        return None, -1
    if r.status_code != 200:
        return None, r.status_code
    try:
        inner = (r.json().get("data") or {})
    except Exception:                                                   # noqa: BLE001
        return None, -2
    return inner.get("total"), 200


def main() -> int:
    depts = load_depts()
    print(f"部门站点 {len(depts)} 个 × 候选栏目 {len(CHANNELS)} 个 "
          f"= {len(depts) * len(CHANNELS)} 次请求，停顿 {PAUSE}s", flush=True)
    result: dict[str, dict] = {}
    with httpx.Client(timeout=30, follow_redirects=True, trust_env=False) as cli:
        for i, d in enumerate(depts, 1):
            hits: dict[str, int] = {}
            for ch in CHANNELS:
                t, st = query(cli, d["code"], ch)
                if st not in (200, -1, -2):
                    print(f"⚠ {d['name']} HTTP {st} ⇒ 停该站", flush=True)
                    break
                if isinstance(t, int) and t > 0:
                    hits[ch] = t
                time.sleep(PAUSE)
            result[d["code"]] = {"name": d["name"], "domain": d["domain"],
                                 "hits": hits}
            tag = "★ " + ", ".join(f"{k}={v}" for k, v in hits.items()) if hits else "  （无）"
            print(f"[{i}/{len(depts)}] {d['name']:20s} {tag}", flush=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(1 for v in result.values() if v["hits"])
    print(f"\n命中站点 {n}/{len(depts)} → {OUT.name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
