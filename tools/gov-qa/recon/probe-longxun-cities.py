r"""探针：龙讯科技 CMS 的市 —— 提取 label 参数并**实测**列表接口。

## 背景（「找到一个 = 找到一片」的第二次尝试）

`recon/mw-summary.py` 汇总出：**安徽 14 个市里 10 个用龙讯 CMS**
（河南 1、湖南 1 也有）—— 是继「广东 hdjlpt」之后第二大的同省同中间件簇。

**已有模板** `adapters/gs_longnan.py`（陇南·市长信箱，415 条）：

```
GET {HOST}/site/label/{labelId}?labelName=messageBoardPageList
    &pageIndex={p}&pageSize={n}&siteId={siteId}&columnId={columnId}
    &action=singleList&isJson=true
→ JSON {"page": {"data": [...], "total": N, "pageIndex": ...}}
```

⇒ 只要从每个市的门户页里**抠出 `labelId / siteId / columnId / labelName`**，
就能批量接入。

## 抠法

龙讯把配置写成 **JS 对象字面量**（键不带引号）塞在 `data-setting="…"` 里，例如
`{labelName:'messageBoardInfoList',id:'6787581,6787571',siteId: 6787231,num:6,…}`。
⇒ 用正则取 `labelName` / `id` / `siteId` / `columnId`（**不是 JSON，不能 json.loads**）。

## 判定（GOAL.md #6）

接口必须返回 `page.total > 0` **且**取一条确认 `replyContent` 正文非空。

⚠ 输出由 Python 自己写文件（`--out`）。只读，不落盘到 data/。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

HERE = Path(__file__).resolve().parent
MW = HERE / "city-middleware.json"

H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

SETTING_RE = re.compile(r'data-setting="([^"]{10,600})"')
TAG_RE = re.compile(r"<[^>]+>")


def _num(blob: str, key: str) -> str:
    m = re.search(rf"{key}\s*:\s*['\"]?([0-9]+)", blob)
    return m.group(1) if m else ""


def _strv(blob: str, key: str) -> str:
    m = re.search(rf"{key}\s*:\s*['\"]([A-Za-z_]+)['\"]", blob)
    return m.group(1) if m else ""


def _text(f: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", f or "")).strip()


def probe(c: httpx.Client, city: str, info: dict) -> dict:
    base = (info.get("base") or "").rstrip("/")
    hd = info.get("hd") or base
    out = {"city": city, "province": info.get("province", ""), "base": base,
           "hd": hd, "label": "", "site": "", "column": "", "label_name": "",
           "http": 0, "total": None, "reply": 0, "sample": "", "note": ""}
    try:
        r = c.get(hd, timeout=20)
    except Exception as e:                                            # noqa: BLE001
        out["note"] = f"页面 {type(e).__name__}"
        return out
    t = r.text or ""
    # 找出「留言板」相关的 data-setting（优先 labelName 含 messageBoard 的）
    best = ""
    for blob in SETTING_RE.findall(t):
        ln = _strv(blob, "labelName")
        if "messageBoard" in ln or "mailbox" in ln.lower() or "letter" in ln.lower():
            best = blob
            break
    if not best:
        for blob in SETTING_RE.findall(t):
            if _num(blob, "siteId") and _num(blob, "id"):
                best = blob
                break
    if not best:
        out["note"] = "页面里没有可用的 data-setting"
        return out

    out["label_name"] = _strv(best, "labelName") or "messageBoardPageList"
    ids = re.findall(r"(?:^|[\s,{])id\s*:\s*['\"]?([0-9,]+)", best)
    out["label"] = (ids[0].split(",")[0] if ids else "")
    out["site"] = _num(best, "siteId")
    out["column"] = _num(best, "columnId")
    if not out["label"] or not out["site"]:
        out["note"] = f"抠不出 label/siteId（blob={best[:120]}）"
        return out

    url = (f"{base}/site/label/{out['label']}?labelName={out['label_name']}"
           f"&pageIndex=1&pageSize=14&siteId={out['site']}"
           + (f"&columnId={out['column']}" if out["column"] else "")
           + "&action=singleList&isJson=true")
    try:
        rr = c.get(url, timeout=20, headers={"Referer": hd})
    except Exception as e:                                            # noqa: BLE001
        out["note"] = f"接口 {type(e).__name__}"
        return out
    out["http"] = rr.status_code
    if rr.status_code != 200:
        out["note"] = f"接口 HTTP {rr.status_code}"
        return out
    try:
        j = rr.json()
    except Exception:                                                 # noqa: BLE001
        out["note"] = f"非 JSON：{_text(rr.text)[:60]}"
        return out
    page = (j or {}).get("page") or {}
    rows = page.get("data") or []
    out["total"] = page.get("total")
    for it in rows:
        rep = _text(" ".join((x or {}).get("replyContent") or ""
                             for x in (it.get("replyVOList") or [])))
        if len(rep) >= 10:
            out["reply"] = len(rep)
            out["sample"] = rep[:100]
            break
    if out["total"] and not out["reply"]:
        out["note"] = "有 total 但列表答复为空（空壳）"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mw", default=str(MW))
    ap.add_argument("--match", default="龙讯", help="只测 middleware 含该串的市")
    ap.add_argument("--province", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    mw = json.loads(Path(args.mw).read_text(encoding="utf-8"))
    cands = [(c, v) for c, v in sorted(mw.items())
             if args.match in "+".join(v.get("middleware") or [])
             and (not args.province or v.get("province") == args.province)]

    L: list[str] = [f"候选（{args.match}）{len(cands)} 个市"]
    ok = 0
    with httpx.Client(headers=H, follow_redirects=True, trust_env=False,
                      verify=False) as c:
        for city, info in cands:
            r = probe(c, city, info)
            good = bool(r["reply"])
            ok += 1 if good else 0
            L.append(f"  {r['province']:8s} {city:10s} label={r['label']:10s} "
                     f"site={r['site']:9s} col={r['column']:9s} "
                     f"HTTP={r['http']} total={r['total']} reply={r['reply']} "
                     f"{'✅' if good else '❌'} {r['note']}")
            if good:
                L.append(f"        {r['label_name']}  {r['sample']}")
    L.append(f"\n⇒ **真能采的市：{ok}/{len(cands)}**")

    text = "\n".join(L) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"written: {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
