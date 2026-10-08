"""江西省直部门站点命中栏目 —— **结构核验**（2026-10-09）。

`jx-dept-probe.py` 扫出 16 个站点有 total>0 的栏目，但**栏目名不等于问答**：
`zxft`（在线访谈）在省政府站已证实是访谈预告/实录散文（50 条里仅 2 条含「答」）。
⇒ 逐栏目 dump 首条结构 + 全页「问/答」计数，判定它到底是不是**问答对**。

只读，不落盘语料。输出 recon/jx-dept-sample.txt
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "adapters"))

import httpx  # noqa: E402
import jx_zf  # noqa: E402

HOST = "https://www.jiangxi.gov.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
OUT = HERE / "jx-dept-sample.txt"

#: (webSiteCode, channelCode, 站点名) —— 取命中量大的 + 名字像信箱/留言的
TARGETS = [
    ("jxszrzyt", "hydt", "省自然资源厅"),
    ("jxswsjkwyh", "hydt", "省卫健委"),
    ("jxsnynct", "yjzj", "省农业农村厅"),
    ("jxsrlzyhshbzt", "yjzj", "省人社厅"),
    ("jxsgat", "zxft", "省公安厅"),
    ("jxszfhcxjst", "zxft", "省住建厅"),
    ("amr", "zxft", "省市监局"),
    ("jxssjt", "sjxx", "省审计厅"),
    ("jxsgzw", "lyxd", "省国资委"),
    ("jxsgzw", "yjzj", "省国资委"),
    ("jxsczt", "hdjl", "省财政厅"),
    ("jxsgyhxxht", "ldxx", "省工信厅"),
    ("jxsmzzjswj", "sjxx", "省民宗局"),
    ("jxstyj", "yjzj", "省体育局"),
]


def page(cli, code: str, ch: str, n: int = 1, size: int = 20) -> list[dict]:
    data = {"current": n, "pageSize": size,
            "channelCode": [ch], "webSiteCode": [code]}
    r = cli.post(HOST + "/queryList", data=data,
                 headers={"User-Agent": UA, "Referer": HOST + "/"})
    if r.status_code != 200:
        return []
    return ((r.json().get("data") or {}).get("results")) or []


def main() -> int:
    log = open(OUT, "w", encoding="utf-8")

    def say(s: str = "") -> None:
        print(s)
        log.write(s + "\n")

    with httpx.Client(timeout=40, follow_redirects=True, trust_env=False) as cli:
        for code, ch, name in TARGETS:
            items = page(cli, code, ch)
            say("=" * 78)
            say(f"【{name} / {code} / channelCode={ch}】本页 {len(items)} 条")
            say("=" * 78)
            if not items:
                say("  （取不到）")
                time.sleep(1.6)
                continue
            # 全页判定
            n_qa = n_ask = n_ans = 0
            for it in items:
                src = it.get("source") or {}
                c = src.get("content")
                body = jx_zf._text(c.get("content") if isinstance(c, dict) else c)
                if jx_zf.QA_SPLIT.search(body):
                    n_qa += 1
                if "问" in body:
                    n_ask += 1
                if "答" in body:
                    n_ans += 1
            say(f"  全页：含『问：…答：…』配对 {n_qa} / 含『问』{n_ask} / "
                f"含『答』{n_ans}（共 {len(items)}）")
            for it in items[:3]:
                src = it.get("source") or {}
                md = src.get("metadata")
                try:
                    md = json.loads(md) if isinstance(md, str) and md.strip() else (md or {})
                except Exception:                                       # noqa: BLE001
                    md = {}
                c = src.get("content")
                body = jx_zf._text(c.get("content") if isinstance(c, dict) else c)
                say("  " + "-" * 72)
                say(f"  id={src.get('id')} title={(src.get('title') or '')[:70]}")
                say(f"  metadata keys={sorted(md.keys())}")
                for k in sorted(md.keys())[:8]:
                    v = md[k]
                    say(f"     md[{k}] = {(v[:90] if isinstance(v, str) else v)}")
                say(f"  content len={len(body)}  head={body[:220]!r}")
            time.sleep(1.6)

    log.close()
    print(f"\n→ {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
