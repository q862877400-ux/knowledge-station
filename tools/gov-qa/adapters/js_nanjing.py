"""适配器：**南京市·政民互动·政府信箱·案例公开（szxx SPA prod-api/wsxf/algk）**。

## 站点事实（2026-10-09 实测，证据 recon/city-js-probe22~26.txt）
 · 门户 `www.nanjing.gov.cn` 的政府信箱是独立 Vue SPA：
   `https://szxx.nanjing.gov.cn:32767/zhengfuxinxiang/huifuxuandeng?orgid=<区划>&type=sszxx`。
 · SPA 的 axios `baseURL="/prod-api/"`（反查 app.js 得到），业务接口在 `/prod-api/wsxf/…`。
 · ★ **可用公开接口（无需令牌）**：`GET /prod-api/wsxf/algk/listPage`
     params: `orgid`(行政区划码，如 320113 玄武区) `type`(sszxx) `pageNum` `pageSize`
   → JSON：`{"total":91,"rows":[{…}],"code":200,"msg":"查询成功"}`
   条目字段（关键）：
     `gkbt` 公开标题、`gkxfnr` 公开信访内容（问题正文）、`gkdfnr` **公开答复内容（答复全文）**、
     `hfdw` 回复单位、`xfrq` 信访日期、`hfrq` 回复日期、`xfjbh` 信访件编号、`id` 数字主键、
     `nrflmc` 内容分类（如「教育_其他_其他」）、`jgid` 机构代码。
   ★ **列表即含问题 + 答复全文**（无需明细）⇒ 采集快。
 · ⚠ `huifuxuandeng`（回复选登）与 `xfj/listPage` 等接口需 `JSWSXF-Token`（返回
   `{"code":401,"msg":"令牌不能为空"}`），未登录不可用；故本适配器走公开的 `algk/listPage`（案例公开）。
 · ⚠ 行政区划码 `orgid`：默认 320113（玄武区，市本级信箱聚合）；不同区码返回不同集合。
 · 样例：`SZ3201202608131745308`「建议新区政府…增设校车」→ 江北新区教育局答复（全文）。
"""
from __future__ import annotations

import time

SITE = {
    "key": "js-nanjing",
    "name": "南京市·政民互动·政府信箱·案例公开",
    "kind": "api",
    "level": "city",
    "entry": "https://szxx.nanjing.gov.cn:32767/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx",
    "status": "ok",
    "note": "GET /prod-api/wsxf/algk/listPage?orgid&type&pageNum&pageSize；**列表自带问题+答复全文**；total≈91",
}

BASE = "https://szxx.nanjing.gov.cn:32767"
LIST_URL = BASE + "/prod-api/wsxf/algk/listPage"
REFERER = SITE["entry"]
ORGID = "320113"       # 玄武区（市本级聚合）
TYPE = "sszxx"
PAUSE = 1.5
PAGE_SIZE = 20


def _day(v) -> str | None:
    v = (v or "").strip() if isinstance(v, str) else v
    return v or None


def harvest(fetch, *, limit: int | None = None, max_pages: int = 100) -> list[dict]:
    """翻页取南京政府信箱案例公开（列表自带问题 + 答复全文）。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_URL, params={
                "orgid": ORGID, "type": TYPE, "pageNum": page, "pageSize": PAGE_SIZE,
            }, headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            d = r.json() or {}
        except Exception:                                                   # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        rows = d.get("rows") or []
        if total is None:
            total = d.get("total")
            print(f"    [{SITE['key']}] 信件总数 total={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("xfjbh") or it.get("id") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            answer = (it.get("gkdfnr") or "").strip()
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("gkbt") or "").strip()
            content = (it.get("gkxfnr") or "").strip()
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": SITE["entry"],
                "question": question,
                "answer": answer,
                "asked_at": _day(it.get("xfrq")),
                "answered_at": _day(it.get("hfrq")),
                "dept": (it.get("hfdw") or "").strip() or None,
                "channel": "政民互动·政府信箱·案例公开",
                "extra": {
                    "title": title,
                    "classify": it.get("nrflmc"),
                    "xfjbh": it.get("xfjbh"),
                    "jgid": it.get("jgid"),
                    "orgid": ORGID,
                    "platform": "南京 szxx SPA prod-api/wsxf/algk（列表自带答复）",
                },
            })
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
