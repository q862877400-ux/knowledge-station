"""适配器：**甘孜州·政民互动·12345 信件公开（interact-service）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe21.txt）
 · 互动栏目：`https://www.gzz.gov.cn/hdjl`（政民互动），页面内嵌 Vue 调：
   · 列表：`POST /interact-service/c/is12345LetterOpen/findList`
       body(JSON): `{current:1, size:10}`
     → `{"code":0,"msg":"操作成功","data":{"total":14,"size":10,"pages":2,"current":1,
        "records":[{wybs, fwgdbh, fwgdbt, djsj, bjsj, handlingSituation}]}}`
   · 详情：`POST /interact-service/c/is12345LetterOpen/selectOne`
       body(JSON): `{fwgdbh:<id>}`
     → `{"code":0,"data":{wybs, fwgdbh, fwgdbt(标题), sqnr(诉求内容), djsj(登记时间),
        bldw(办理单位), blqk(办理情况=答复全文), dfsj(答复时间)}}`
   ★ 答复全文在 `data.blqk`；问题正文在 `data.sqnr`；单位 `data.bldw`。
 · 样例：`fwgdbh=TFTB9951330026081900394`「甲根坝镇观景垭口」→ 康定市答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-ganzi",
    "name": "甘孜州·政民互动·12345 信件公开",
    "kind": "api",
    "level": "city",
    "entry": "https://www.gzz.gov.cn/hdjl",
    "status": "ok",
    "note": "POST /interact-service/c/is12345LetterOpen/findList（列表 total≈14）+ POST …/selectOne（答复 blqk）",
}

BASE = "https://www.gzz.gov.cn"
LIST_URL = BASE + "/interact-service/c/is12345LetterOpen/findList"
DETAIL_URL = BASE + "/interact-service/c/is12345LetterOpen/selectOne"
REFERER = SITE["entry"]
PAUSE = 1.0
PAGE_SIZE = 20

_TAG = re.compile(r"<[^>]+>")


def _clean(s) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(s))
    s = re.sub(r"(?i)</p>", "\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    return s.strip()


def harvest(fetch, *, limit: int | None = None, max_pages: int = 100) -> list[dict]:
    """翻页取甘孜 12345 信件公开；列表不含答复，逐条取详情。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch.post(LIST_URL, json={"current": page, "size": PAGE_SIZE},
                           headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            d = (r.json() or {}).get("data") or {}
        except Exception:                                                   # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        rows = d.get("records") or []
        if total is None:
            total = d.get("total")
            print(f"    [{SITE['key']}] 信件总数 total={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("fwgdbh") or it.get("wybs") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            try:
                dr = fetch.post(DETAIL_URL, json={"fwgdbh": sid},
                                headers={"Referer": REFERER})
                dd = (dr.json() or {}).get("data") or {}
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                continue
            answer = _clean(dd.get("blqk"))
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (dd.get("fwgdbt") or it.get("fwgdbt") or "").strip()
            content = _clean(dd.get("sqnr"))
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": SITE["entry"],
                "question": question,
                "answer": answer,
                "asked_at": (dd.get("djsj") or it.get("djsj") or None),
                "answered_at": (dd.get("dfsj") or it.get("bjsj") or None),
                "dept": (dd.get("bldw") or "").strip() or None,
                "channel": "政民互动·12345 信件公开",
                "extra": {
                    "title": title,
                    "handling_situation": it.get("handlingSituation"),
                    "platform": "甘孜州 interact-service is12345LetterOpen",
                },
            })
            time.sleep(PAUSE)
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
