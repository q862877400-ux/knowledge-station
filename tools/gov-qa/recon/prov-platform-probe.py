"""侦察：省级门户「一片式」互动平台探测（湖南 hd.hunan.gov.cn 模式能否复制）。

## 为什么要探
湖南的突破不是"多找一个站"，而是发现**全省厅局共用一个平台、只差一个 deptId**
⇒ 一次铺开 33 个厅局、653 → 4351 条。内蒙/黑龙江目前只有「省门户一条线」
（67 / 36 条），要拉到同一量级，必须找同款"一片式"平台。

## 本脚本做什么
对候选省级门户的互动栏目页，抓 HTML + 同目录 JS，正则找三类指纹：
 ① 平台域名（hunan 的 `hd.hunan.gov.cn/communication/api-mailbox` 这类）；
 ② 接口路径关键字（list / query / ajax / api / mailbox / search）；
 ③ 部门 id 变量（`deptId` / `siteId` / `channelId` / `orgId` / `sysid`）。
纯只读、不改任何东西；结果写 JSON 供人工判读。

用法：
  python recon/prov-platform-probe.py                 # 内置候选清单
  python recon/prov-platform-probe.py nmg hlj         # 只探指定 key
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx

HERE = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

#: key → (名称, 探哪些页面)。页面按顺序抓，命中 JS 再抓同目录 JS。
TARGETS = {
    "nmg": ("内蒙古", [
        "https://www.nmg.gov.cn/zmhd/fkhy_1/index_13317.html",
        "https://www.nmg.gov.cn/zmhd/",
    ]),
    "hlj": ("黑龙江", [
        "https://www.hlj.gov.cn/hlj/c115707/wycx.shtml",
        "https://www.hlj.gov.cn/hlj/c115777/dep_list.shtml",
        "https://www.hlj.gov.cn/hlj/c108467/zmhd.shtml",
    ]),
    "js": ("江苏", [
        "https://www.jiangsu.gov.cn/col/col81602/index.html",
    ]),
    "jx": ("江西", [
        "https://www.jiangxi.gov.cn/jxsrmzf/hdjl/pc/list.html",
        "https://www.jiangxi.gov.cn/jxsrmzf/zxzx/pc/list.html",
    ]),
    "fj": ("福建", [
        "https://www.fujian.gov.cn/hdjl/zxts/wycx/",
        "https://www.fujian.gov.cn/hdjl/zxts/",
    ]),
    "yn": ("云南", [
        "https://www.yn.gov.cn/hdjl/wlwz/wlwzwyzx/",
        "https://www.yn.gov.cn/hdjl/",
    ]),
    "hn": ("河南", [
        "https://www.henan.gov.cn/hdjl/wszx/",
        "https://www.henan.gov.cn/hdjl/hdjl/",
    ]),
    "cq": ("重庆", [
        "https://www.cq.gov.cn/hdjl/cqhlwdc/lyxd1/",
    ]),
    "gs": ("甘肃", [
        "https://www.gansu.gov.cn/",
        "http://www.gansu.gov.cn/",
    ]),
}

#: 平台/接口指纹（命中即记）
PAT = {
    "api_path": re.compile(r"""["'](https?://[^"']*?/(?:api|ajax|front|list|query|search|mailbox|communication)[^"']*?)["']""", re.I),
    "rel_api": re.compile(r"""["'](/[^"']*?(?:api|ajax|list|query|search|mailbox|communication)[^"']*?)["']""", re.I),
    "js_src": re.compile(r"""<script[^>]+src=["']([^"']+\.js[^"']*)["']""", re.I),
    "deptvar": re.compile(r"""(?:var\s+)?(deptId|siteId|siteNo|channelId|orgId|sysid|siteUrl|group_id)\s*[:=]\s*["']?([A-Za-z0-9_\-]{2,64})""", re.I),
    "hunan_like": re.compile(r"hd\.hunan\.gov\.cn|mailList2ie|api-mailbox", re.I),
    "was5": re.compile(r"was5|channelid=\d+", re.I),
    "igi": re.compile(r"/IGI/|openGovmsgbox", re.I),
    "jact": re.compile(r"/jact/front/", re.I),
}
#: 抓 JS 的上限与单文件大小上限（别把整包 bundle 全灌进来）
MAX_JS = 6
MAX_JS_BYTES = 400_000


def fetch(c: httpx.Client, url: str) -> tuple[int, str]:
    try:
        r = c.get(url, headers={"User-Agent": UA, "Referer": url},
                  follow_redirects=True)
        return r.status_code, r.text
    except Exception as e:                                              # noqa: BLE001
        return 0, f"__ERR__ {type(e).__name__}: {e}"


def scan(text: str) -> dict:
    out: dict[str, list[str]] = {}
    for name, rx in PAT.items():
        hits = []
        for m in rx.finditer(text):
            g = m.group(0) if name in ("hunan_like", "was5", "igi", "jact") else (
                m.group(2) if name == "deptvar" else m.group(1))
            s = g.strip()
            if s and s not in hits:
                hits.append(s)
        if hits:
            out[name] = hits[:30]
    return out


def main() -> int:
    want = sys.argv[1:] or list(TARGETS)
    result: dict = {}
    with httpx.Client(timeout=25, trust_env=False) as c:
        for key in want:
            if key not in TARGETS:
                print(f"未知 key：{key}", flush=True)
                continue
            label, pages = TARGETS[key]
            print(f"\n===== [{key}] {label} =====", flush=True)
            entry: dict = {"label": label, "pages": {}, "js": {}}
            js_urls: list[str] = []
            for p in pages:
                code, html = fetch(c, p)
                print(f"  {code:>4} {p} ({len(html)}B)", flush=True)
                if code != 200:
                    entry["pages"][p] = {"status": code, "note": html[:160]}
                    continue
                hit = scan(html)
                entry["pages"][p] = {"status": code, "bytes": len(html), "hits": hit,
                                     "title": (re.search(r"<title>(.*?)</title>", html,
                                                         re.S | re.I) or [None, ""])[1].strip()[:80]}
                for u in hit.get("js_src", []):
                    full = urljoin(p, u)
                    if full not in js_urls:
                        js_urls.append(full)
                if hit:
                    print(f"      命中：{ {k: (v[:3] if isinstance(v, list) else v) for k, v in hit.items()} }",
                          flush=True)
                time.sleep(1.5)

            for u in js_urls[:MAX_JS]:
                code, txt = fetch(c, u)
                if code != 200 or len(txt) > MAX_JS_BYTES:
                    print(f"  js {code} {u} ({len(txt)}B, 跳过>){MAX_JS_BYTES})", flush=True)
                    continue
                hit = scan(txt)
                if hit:
                    entry["js"][u] = hit
                    print(f"  js {u}", flush=True)
                    print(f"      命中：{ {k: v[:4] for k, v in hit.items()} }", flush=True)
                time.sleep(1.5)
            result[key] = entry

    out = HERE / "prov-platform-probe.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[probe] 已写 {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
