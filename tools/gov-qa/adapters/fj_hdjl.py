"""适配器：**福建省人民政府门户 · 互动交流（12345 诉求公开 / 信件选登）**。

## 站点形态（2026-10-08 实探，证据 recon/fj-list.html / fj-12345list.html / fj-12345detail.html）
 · 入口栏目 `/hdjl/zxts/`（咨询投诉）→ 信件选登 `/hdjl/zxts/wycx/`；
   **列表与明细都是 avalon JS 渲染**，静态 HTML 里只有模板（`ms-text="el.…"`），
   真正数据在 `/apigateway/12345v3/sqeventreport/` 下的 JSON 接口（**别照静态页写正则**）。
 · 列表接口（实测 200，total=**143**，10 条/页，翻页参数 `current`）：
   `GET /apigateway/12345v3/sqeventreport/sqDetailPublic
        ?areacode=350000&isContainsLower=1&current=<页码>`
   请求头需带 `encryptType: sm4`（+ Referer）。
   → JSON `{code:"200", content:{eventInfo:{total, size, records:[{uid, caseTitle, caseDesc,
     incidentTime, position, billno, areacode}]}}}`（**caseDesc=诉求全文**）。
 · 明细（答复）接口（实测 200）：
   `GET /apigateway/12345v3/sqeventreport/getSqDetail2?uid=<uid>`（同样 `encryptType: sm4`）
   → JSON `content.taskInfo[0]` 的 `handledesc`=**答复原文**、`orgname`=回复单位、`handletime`=回复时间。
   （另有 `getSqDetailBasic?uid=` 返回诉求人/地址等，本适配器不取。）
 · 静态明细页 `/hdjl/zxts/wycx/index0329.htm?id=<uid>` 仅供人看，采集走接口。

## 说明
答复是**办理答复**（如「福建省住房和城乡建设厅」就职称评审论文期刊认定给出明确口径），
带单位与时间 ⇒ 可当考卷口径。`answer` 取 `handledesc` 原文，不清洗。
"""
from __future__ import annotations

import time

SITE = {
    "key": "fj-hdjl",
    "name": "福建省人民政府·互动交流（12345诉求公开）",
    "kind": "api",
    "level": "province",
    "entry": "https://www.fj.gov.cn/hdjl/zxts/wycx/12345list.htm",
    "status": "ok",
    "note": "列表 sqDetailPublic(current 翻页, total≈143) + 明细 getSqDetail2(handledesc=答复)；头需 encryptType:sm4",
}

BASE = "https://www.fj.gov.cn"
LIST_API = BASE + "/apigateway/12345v3/sqeventreport/sqDetailPublic"
DETAIL_API = BASE + "/apigateway/12345v3/sqeventreport/getSqDetail2"
DETAIL_PAGE = BASE + "/hdjl/zxts/wycx/index0329.htm?id={uid}"
HEADERS = {"encryptType": "sm4",
           "Referer": BASE + "/hdjl/zxts/wycx/12345list.htm"}
PAUSE = 1.5


def _reply(fetch, uid: str) -> dict:
    """取一条明细的答复三要素；失败返回空 dict。"""
    r = fetch(DETAIL_API, params={"uid": uid}, headers=HEADERS)
    if getattr(r, "status_code", 0) != 200:
        return {}
    try:
        ti = ((r.json().get("content") or {}).get("taskInfo") or [])
    except Exception:                                                       # noqa: BLE001
        return {}
    if not ti:
        return {}
    t0 = ti[0]
    return {"answer": t0.get("handledesc"),
            "dept": t0.get("orgname"),
            "answered_at": t0.get("handletime")}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 40) -> list[dict]:
    """按 `current` 翻列表，再逐条取答复（按 uid 去重）。"""
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        r = fetch(LIST_API,
                  params={"areacode": "350000", "isContainsLower": "1", "current": str(page)},
                  headers=HEADERS)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            ev = ((r.json().get("content") or {}).get("eventInfo") or {})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页 JSON 异常 {type(e).__name__}（停）")
            break
        recs = ev.get("records") or []
        if not recs:
            break
        fresh = [it for it in recs if str(it.get("uid")) not in seen]
        print(f"    [{SITE['key']}] 第 {page} 页：条目 {len(recs)}，新增 {len(fresh)}"
              f"（total={ev.get('total')}）")
        if not fresh:
            break
        for it in fresh:
            if limit and len(out) >= limit:
                return out[:limit]
            uid = str(it.get("uid") or "")
            if not uid:
                continue
            seen.add(uid)
            time.sleep(PAUSE)
            rep = _reply(fetch, uid)
            if not rep.get("answer"):
                continue
            question = (it.get("caseDesc") or "").strip() or (it.get("caseTitle") or "").strip()
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": DETAIL_PAGE.format(uid=uid),
                "question": question,
                "answer": rep["answer"],
                "asked_at": it.get("incidentTime"),
                "answered_at": rep.get("answered_at"),
                "dept": rep.get("dept"),
                "channel": "互动交流·信件选登（12345诉求公开）",
                "extra": {"case_title": it.get("caseTitle"),
                          "billno": it.get("billno"),
                          "position": it.get("position"),
                          "areacode": it.get("areacode"),
                          "list_api": LIST_API,
                          "answer_kind": "12345办理答复"},
            })
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条（按 uid 去重；列表 total≈143）")
    return out
