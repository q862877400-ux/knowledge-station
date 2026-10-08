"""浙江「民呼我为统一平台」**地市级**共用引擎（`zxts.zjzwfw.gov.cn`）。

## 为什么另起一个模块
`adapters/zj_mhww.py` 是**省本级**（`code=330000`，totalItem≈49218）的适配器，
已登记、已落盘，**不动它**。本模块复用它的**字体反爬解码**（`_decode`，glyph 名即真字），
只把 `code` 换成地市行政区划码，逐市采集。

## ★ code 语义（2026-10-09 实测，证据 recon/city-js-zj-zjmhww-probe.txt）
`code` 是**精确行政区划码**（**不是层级聚合**）：
 · `code=""`      → 全国/全平台 908369 条；
 · `code=330000`  → **浙江省本级**（省级部门直接办理）49218 条；
 · `code=330100`  → **杭州市** 61768 条；
 · `code=339999` / `code=110000`（非法/外省）→ **0 条**。
⇒ 各市数据**互不重叠**（首条 storeid 两两不同），地市码即该市来信。

## 接口（与省本级完全同构）
 · 列表 `POST {BASE}/zlh/zsapi/xfpt/OTMelbwjyz/OTMjkerj`
     body `{"code":"<市码>","bt":"","bldw":"","pageNum":<n>,"pageSize":<m>}`（pageSize≤100）
 · 明细 `GET  {BASE}/zlh/zsapi/xfpt/OTMelbwjyz/OTMrwgaxid?storeId=<id>`
     → `dfyj`=答复、`nr`=问题正文、`dfdw`=答复单位、`fysj`=反映、`dfsj`=答复时间。
 · 文字字段可能被 `#<fid>otltag…` 字体混淆，`_decode` 按 fontId 下 woff 还原；明文原样放行。

## 实测各市 totalItem（2026-10-09，以接口为准）
杭州 61768 / 宁波 13284 / 温州 8721 / 嘉兴 5875 / 湖州 2135 / 绍兴 5843 /
金华 5962 / 衢州 3289 / 舟山 1857 / 台州 2737 / 丽水 2938。

## 可反复跑
列表只按页码翻、无游标 ⇒ 开跑先读本适配器 `data/<key>-*.jsonl` 已有 id 并跳过其明细，
`limit` 语义 = **本轮新增条数**，反复跑逐轮推进（与 zj_mhww 同款设计）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from adapters.zj_mhww import (DETAIL_URL, HEADERS, LIST_URL, PAGE_SIZE,  # noqa: F401
                              PAUSE, _decode)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def existing_ids(site_key: str) -> set[str]:
    """读 `data/<site_key>-*.jsonl` 已有 id（供**续采**，避免第二轮恒 0 新增）。"""
    ids: set[str] = set()
    try:
        for p in DATA_DIR.glob(f"{site_key}-*.jsonl"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    sid = str(json.loads(line).get("id") or "").strip()
                    if sid:
                        ids.add(sid)
    except Exception:                                                       # noqa: BLE001
        pass
    return ids


def harvest_area(fetch, *, SITE: dict, area: str, limit: int | None = None,
                 max_records: int = 500, page_size: int = PAGE_SIZE) -> list[dict]:
    """采某地市「民呼我为·办理公开」（问题 + 答复原文，字体混淆自动还原）。

    `area` 为该市行政区划码（如杭州 330100）。`limit` 未给时用 `max_records` 兜底
    （与省本级 `zj_mhww` 同款安全阀；反复跑可逐轮推进）。`fetch` 见 harvest.py 的 _Fetcher。
    """
    out: list[dict] = []
    seen = existing_ids(SITE["key"])
    known = len(seen)
    cap = limit if limit else max_records
    if known:
        print(f"    [{SITE['key']}] 已落盘 {known} 条，本轮跳过其明细，目标新增 {cap} 条")
    total = None
    page = 1
    while True:
        if len(out) >= cap:
            break
        try:
            r = fetch.post(LIST_URL, json={"code": area, "bt": "", "bldw": "",
                                           "pageNum": page, "pageSize": page_size},
                           headers=HEADERS)
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        data = (r.json() or {}).get("data") or {}
        rows = data.get("list") or []
        if total is None:
            total = data.get("totalItem")
            print(f"    [{SITE['key']}] {SITE.get('name', '')} code={area} totalItem={total}")
        if not rows:
            break
        fresh = 0
        for it in rows:
            if len(out) >= cap:
                break
            sid = str(it.get("storeid") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            time.sleep(PAUSE)
            try:
                dr = fetch(DETAIL_URL, params={"storeId": sid}, headers=HEADERS)
                dd = (dr.json() or {}).get("data") or {}
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {sid}：{type(e).__name__}（跳过）")
                continue
            question = _decode(fetch, dd.get("nr")) or _decode(fetch, dd.get("bt"))
            answer = _decode(fetch, dd.get("dfyj"))
            if len(answer) < 10 or len(question) < 4:
                continue
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": f"{SITE['entry'].split('#')[0]}"
                       f"#/home/index/search-detail?storeId={sid}",
                "question": question[:400],
                "answer": answer,
                "asked_at": _decode(fetch, dd.get("fysj")) or None,
                "answered_at": _decode(fetch, dd.get("dfsj")) or None,
                "dept": _decode(fetch, dd.get("dfdw")) or None,
                "channel": "民呼我为·办理公开",
                "extra": {
                    "title": _decode(fetch, dd.get("bt")),
                    "storeid": sid,
                    "area_code": area,
                    "xfmd": it.get("xfmd"),
                    "sjly": _decode(fetch, dd.get("sjly")),
                    "platform": "浙江民呼我为统一平台",
                    "answer_kind": "办理答复（民呼我为办结件公示）",
                },
            })
            fresh += 1
        print(f"    [{SITE['key']}] 列表第 {page} 页：{len(rows)} 条，新增 {fresh}")
        if total and page * page_size >= int(total):
            break
        page += 1
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
