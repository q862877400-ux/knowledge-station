"""TRS WAS5 检索中间件 · 共用采集逻辑（部级/省级站通用基座）。

## 接口形态（生态环境部实测，2026-10-07；TRS WAS5 是全国政务站常见中间件）
```
GET {base}/was5/web/search
    ?channelid=<频道号>&orderby=-DOCRELTIME&keyword=&page=N&perpage=M
→ JSON {"code":0,"recordCount":N,"pageSize":M,"currentPage":P,
        "items":[{"hfdw":"…","doccontent":"…","lxrq":"…","doctitle":"…",
                  "hfrq":"…","docpuburl":"…","recid":"…"}]}
```

## 给站点适配器的约定
每个省站适配器只写 `SITE` 字典与频道清单，然后：
```python
from adapters._was5_common import harvest_was5

def harvest(fetch, *, limit=None):
    return harvest_was5(fetch, SITE=SITE, API=API, CHANNELS=CHANNELS,
                        REFERER=SITE["entry"], limit=limit)
```

## 防御性字段映射（省站字段名可能略有出入）
字段名 `doctitle/doccontent/docpuburl/recid/hfdw/lxrq/hfrq` 是 TRS 约定，
但**不许**假设省站 100% 一致 —— 每个字段给一组候选键名依次兜底，
命中不了的**把原始 item 整个放进 `extra`**（一个字段都不丢，事后可救）。

## 坑（别重踩，见 README 坑 3）
不带 `channelid`（或带错）时接口返回 ~711 字节空页 —— **这是"参数不对"，不是"没有接口"**。
"""
from __future__ import annotations

import json
import time

PERPAGE = 100
PAUSE = 3.0                    # 接口很轻，但保持礼貌

#: 每个统一字段 → 候选键名（依次取第一个非空）
FIELD_CANDIDATES = {
    "id": ("recid", "docpuburl", "url", "id"),
    "url": ("docpuburl", "url", "docpuburl".upper()),
    "question": ("doctitle", "title", "question", "bt"),
    "answer": ("doccontent", "content", "answer", "reply", "hf"),
    "asked_at": ("lxrq", "asktime", "cjsj"),
    "answered_at": ("hfrq", "replytime", "hfsj"),
    "dept": ("hfdw", "dept", "bm", "hfbm"),
}


def _pick(item: dict, keys: tuple[str, ...]):
    for k in keys:
        v = item.get(k)
        if v not in (None, ""):
            return v
    return None


def harvest_was5(fetch, *, SITE: dict, API: str, CHANNELS: list[tuple[str, str]],
                 REFERER: str, limit: int | None = None,
                 perpage: int = PERPAGE, pause: float = PAUSE) -> list[dict]:
    """按统一记录格式返回该站全部频道的问答。

    ⚠ `fetch` 必须能带 `params=` 与 `headers=`（httpx.Client.get 的签名）。
    `CHANNELS` 是 `(channelid, 栏目名)` 列表 —— 加频道加一行即可。
    """
    out: list[dict] = []
    known = set(FIELD_CANDIDATES) | set(
        k for keys in FIELD_CANDIDATES.values() for k in keys)
    for ch, ch_name in CHANNELS:
        page, total = 1, None
        while True:
            r = fetch(API, params={"channelid": ch, "orderby": "-DOCRELTIME",
                                   "keyword": "", "page": str(page),
                                   "perpage": str(perpage)},
                      headers={"Referer": REFERER})
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] {ch_name} 第 {page} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）")
                break
            try:
                j = r.json()
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] {ch_name} 第 {page} 页不是 JSON"
                      f"（{type(e).__name__}，len={len(r.text or '')}，停）")
                break
            items = j.get("items") or []
            if total is None:
                total = j.get("recordCount")
                print(f"    [{SITE['key']}] {ch_name}（channelid={ch}）"
                      f"recordCount={total}")
            if not items:
                break
            for it in items:
                # 原始 item 里统一字段之外的原样进 extra（别丢站点特有字段）
                extra = {k: v for k, v in it.items() if k not in known}
                out.append({
                    "source": SITE["key"],
                    "id": str(_pick(it, FIELD_CANDIDATES["id"]) or ""),
                    "url": _pick(it, FIELD_CANDIDATES["url"]),
                    "question": _pick(it, FIELD_CANDIDATES["question"]),
                    "answer": _pick(it, FIELD_CANDIDATES["answer"]),
                    "asked_at": _pick(it, FIELD_CANDIDATES["asked_at"]),
                    "answered_at": _pick(it, FIELD_CANDIDATES["answered_at"]),
                    "dept": _pick(it, FIELD_CANDIDATES["dept"]),
                    "channel": ch_name,
                    "extra": extra,
                })
            if limit and len(out) >= limit:
                return out[:limit]
            if len(items) < perpage:
                break
            page += 1
            time.sleep(pause)
    return out


if __name__ == "__main__":  # pragma: no cover - 冒烟：直接对着生态环境部验基座
    import os
    os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
    import httpx
    with httpx.Client(timeout=40, follow_redirects=True, trust_env=False) as cli:
        rows = harvest_was5(
            cli.get,
            SITE={"key": "mee-smoke"},
            API="https://www.mee.gov.cn/was5/web/search",
            CHANNELS=[("232534", "常见问题")],
            REFERER="https://www.mee.gov.cn/hdjl/", limit=3)
    print(json.dumps(rows, ensure_ascii=False, indent=1)[:2000])
