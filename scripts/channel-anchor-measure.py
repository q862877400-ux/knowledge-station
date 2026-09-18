"""渠道锚点实测器（§11.0 R6）：给一条渠道**量**出可直接粘贴的探针目标。

## 它存在的理由（一次真实的翻车）
R6a 批量配探针时，我先把 `<title>` 做了"实体解码 + 空白折叠"再当锚点——于是
`全部文件&nbsp;广东省人民政府门户网站` 被写成 `全部文件 广东省人民政府门户网站`，
**正文里根本没有这个串** ⇒ 3 条渠道被误判成"可疑"。
根因不是判据错，而是**锚点不是正文的逐字子串**。所以本脚本把那条纪律做成可执行的：

    锚点必须是**原样正文**的子串（不做实体解码、不折叠空白）——检索前先自检。

## 用法
    .venv\\Scripts\\python.exe scripts\\channel-anchor-measure.py <channel_id> [<channel_id> ...]

对每条：抓一次页面 → 从 `<title>` 里取"最长的不含空白的片段"（≥6 字）当候选 →
**逐字校验它真的在正文里** → 打印成 JSON 片段（含 evidence：时间/出口/字节/链接数/title 原文）。
JSON 接口（正文以 `{`/`[` 开头）不猜锚点，只打印头部让人挑字段名。
**它只打印，不写文件**——写进 `channel_probes.json` 仍要人过一眼（防"把猜洗成实测"）。
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 控制台是 GBK，这里统一成 UTF-8

from src.core.storage import channel_repo as cr  # noqa: E402
from src.core.update import channel_probe as cp  # noqa: E402
from src.core.update.channels.base import default_transport  # noqa: E402

TIMEOUT = 15.0
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def anchor_from_html(raw: str) -> tuple[str, str]:
    """从**原样正文**里取锚点候选：`<title>` 中最长的不含空白片段（≥6 字）。

    返回 `(anchor, 说明)`；取不到就返回 `("", 原因)`。
    """
    m = _TITLE_RE.search(raw)
    if not m:
        return "", "正文里没有 <title>"
    title_raw = m.group(1)                      # ⚠ 原样，不解码、不折叠
    tokens = [t for t in re.split(r"\s+", title_raw) if len(t) >= 6]
    if not tokens:
        return "", f"<title> 里没有 ≥6 字的连续片段：{title_raw[:60]!r}"
    anchor = max(tokens, key=len)
    if anchor not in raw:                       # ⚠ 这就是那次翻车的自检
        return "", f"候选 {anchor!r} 不是正文的逐字子串（别做实体解码/空白折叠）"
    return anchor, f"title 原样={title_raw[:70]!r}"


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    rows = {r["channel_id"]: r for r in cr.list_channels()}
    if argv[0] == "--repair":
        # 修"锚点不是逐字子串"这一类：只挑上次被判 probe_no_anchor 的渠道重量一遍。
        # `--repair <code>` 也可挑别的错误码（如 no_anchor_configured = 只探了连通性、还缺锚点）。
        code = argv[1] if len(argv) > 1 else "probe_no_anchor"
        argv = [r["channel_id"] for r in rows.values() if r.get("last_error_code") == code]
        print(f"--repair {code}：台账里 {len(argv)} 条，逐条重量")
    targets = cp.load_targets()
    transport = default_transport()
    for cid in argv:
        row = rows.get(cid)
        if row is None:
            print(f"⚠ {cid} 不在台账里")
            continue
        old = targets.get(cid) or {}
        url = old.get("url") or row.get("url") or ""
        print(f"\n=== {cid}  {row['name']}")
        print(f"    url: {url[:110]}")
        if not url.startswith("http"):
            print("    ⚠ 台账里的 url 字段不是可直接抓的 http 地址（端点描述）——手工设计")
            continue
        try:
            status, _headers, text, raw_bytes = transport.fetch_page(url, timeout=TIMEOUT)
        except Exception as e:  # noqa: BLE001
            print(f"    取不到：{type(e).__name__}: {e}")
            continue
        links = cp._count_links(text)
        print(f"    HTTP {status} · {len(raw_bytes)} bytes · 链接 {links} · "
              f"出口={'env-proxy' if os.environ.get('HTTPS_PROXY') else 'direct'}")
        if text.lstrip()[:1] in "{[":
            print(f"    JSON 正文头部：{text[:220]!r}")
            print("    ⇒ 锚点请从上面的字段名里挑（要挑该接口特有的，别挑 code/msg 这种通用键）")
            continue
        anchor, why = anchor_from_html(text)
        if not anchor:
            print(f"    没有可用的文本锚点：{why}")
            print(f"    建议：只配 min_links（实测链接数 {links}）；正文头部：{text[:200]!r}")
            continue
        entry = {"url": url, "expect": anchor}
        if links:
            entry["min_links"] = 1
        entry["evidence"] = (
            f"实测 {datetime.now().strftime('%Y-%m-%d %H:%M')}：HTTP {status} / "
            f"{len(raw_bytes)} bytes / {links} 链接 / 锚点逐字校验通过（{why}）")
        print("    ✅ 可直接粘贴的目标：")
        print(json.dumps({cid: entry}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
