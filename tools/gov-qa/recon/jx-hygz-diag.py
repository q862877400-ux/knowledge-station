"""江西 hygz 丢弃原因 + zxft 栏目结构（2026-10-09）。

背景：jx-zf 落盘 388（wxszj 259 + hygz 129），hygz 上游 total=430
⇒ 301 条被 `_one()` 丢掉。本脚本逐条复算 `_one()` 的判定，给出**丢弃原因分布**，
并 dump zxft（total=102，适配器未接）的结构，判断它是不是问答。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter
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
OUT = HERE / "jx-hygz-diag.txt"


def fetch_page(cli, channel: str, page: int, size: int = 50) -> list[dict]:
    data = {"current": page, "pageSize": size,
            "channelCode": [channel], "webSiteCode": ["jxsrmzf"]}
    r = cli.post(HOST + "/queryList", data=data,
                 headers={"User-Agent": UA, "Referer": HOST + "/"})
    r.raise_for_status()
    return ((r.json().get("data") or {}).get("results")) or []


def why(src: dict) -> tuple[str, dict]:
    """复算 jx_zf._one 的每一步，返回 (原因, 详情)。"""
    md = {}
    raw = src.get("metadata")
    if isinstance(raw, str) and raw.strip():
        try:
            md = json.loads(raw)
        except Exception:                                               # noqa: BLE001
            md = {}
    content = jx_zf._text((src.get("content") or {}).get("content")
                          if isinstance(src.get("content"), dict) else src.get("content"))
    title = jx_zf._text(src.get("title"))
    answer = jx_zf._text(md.get("field_1596"))
    m = jx_zf.QA_SPLIT.search(content)
    info = {"title": title[:40], "clen": len(content),
            "has_问": "问" in content, "has_答": "答" in content,
            "qa_match": bool(m), "md_keys": sorted(md.keys())}
    if m:
        q = (m.group(1).strip() or title)
        a = (m.group(2).strip() or answer)
        info["qlen"], info["alen"] = len(q), len(a)
        if not a:
            return "空答复", info
        if len(q) < 4:
            return "问题<4字", info
        if len(a) < 10:
            return "答复<10字", info
        return "OK", info
    if not answer:
        return "无问无答（正文既无『问…答…』也无 field_1596）", info
    info["alen"] = len(answer)
    return ("OK" if len(answer) >= 10 and len(content) >= 4 else "答复<10字"), info


def main() -> int:
    log = open(OUT, "w", encoding="utf-8")

    def say(s: str = "") -> None:
        print(s)
        log.write(s + "\n")

    with httpx.Client(timeout=40, follow_redirects=True, trust_env=False) as cli:
        reasons = Counter()
        samples: dict[str, list[str]] = {}
        total_items = 0
        for page in range(1, 10):
            items = fetch_page(cli, "hygz", page)
            if not items:
                break
            total_items += len(items)
            for it in items:
                src = it.get("source") or {}
                r, info = why(src)
                reasons[r] += 1
                if r != "OK" and len(samples.setdefault(r, [])) < 4:
                    samples[r].append(json.dumps(info, ensure_ascii=False))
            say(f"  hygz 第 {page} 页 {len(items)} 条，累计 {total_items}")
            if len(items) < 50:
                break
            time.sleep(1.6)

        say("")
        say("=" * 78)
        say(f"【hygz 丢弃原因分布】共扫 {total_items} 条")
        say("=" * 78)
        for r, n in reasons.most_common():
            say(f"  {n:5d}  {r}")
        say("")
        for r, ex in samples.items():
            say(f"--- 样本：{r} ---")
            for e in ex:
                say("   " + e)
        time.sleep(1.6)

        # ---- zxft 结构 ---------------------------------------------------
        say("")
        say("=" * 78)
        say("【zxft（在线访谈）结构】total=102")
        say("=" * 78)
        items = fetch_page(cli, "zxft", 1)
        say(f"本页 {len(items)} 条")
        for it in items[:4]:
            src = it.get("source") or {}
            md = src.get("metadata")
            try:
                md = json.loads(md) if isinstance(md, str) else (md or {})
            except Exception:                                           # noqa: BLE001
                md = {}
            c = src.get("content")
            body = (c.get("content") if isinstance(c, dict) else c) or ""
            say("-" * 70)
            say(f"id={src.get('id')} title={(src.get('title') or '')[:60]}")
            say(f"metadata keys={sorted(md.keys())}")
            for k in sorted(md.keys()):
                v = md[k]
                say(f"   md[{k}] = {(v[:100] if isinstance(v, str) else v)}")
            say(f"content len={len(body)}")
            say(f"   head={body[:300]!r}")
        # 统计整页有没有「问/答」
        q = sum(1 for it in items if "问" in str((it.get('source') or {}).get('content')))
        a = sum(1 for it in items if "答" in str((it.get('source') or {}).get('content')))
        say(f"本页含『问』{q} 条，含『答』{a} 条（共 {len(items)}）")

    log.close()
    print(f"\n→ {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
