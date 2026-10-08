"""适配器：**济南市·互动交流·回应关切（jpaas-jact 网关，JSON 接口）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city-probe4.txt + 逐接口实测）
 · 门户 `www.jinan.gov.cn` 互动交流「回应关切」→
   `http://www.jinan.gov.cn/api-gateway/jpaas-jact-web-server/front/mail-pub-list.do?...`
 · 该页是**空壳**，列表由 layui 经 `/jact_files/pagemodel/default-template/page.js` 拉取：
   · 列表（**JSON**）`GET {base}/find-mail-pub-list`
       `?pageNum=N&pageSize=M&platformUid=<pid>&submitTargetIds=<ids>&govOpen=1`
       → `{"code":0,"data":[{"iid","title","transactNo","submitDate"(ms),"submitTargetName",…}],"count":250}`
   · 明细（**HTML**）`GET {base}/mail-pub-detail?iid=<iid>`
       标签/值为相邻 `<td>`：`标 题： / 内 容： / 提交时间： / 答复部门： / 答复日期： / 答复内容：`
 · base = `http://www.jinan.gov.cn/api-gateway/jpaas-jact-web-server/front`
   （page.js 逻辑：URL 含 `api-gateway` 则前缀 `/api-gateway/jpaas-jact-web-server/front/`）。
 · 实测 `count=250`；样例「关于2026年无线电能力验证举办」→「济南市工业和信息化局」答复。
 · **BASE 用 http**（https 亦通，统一用 http）。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sd-jinan",
    "name": "济南市·互动交流·回应关切（jact网关）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.jinan.gov.cn/col/col26/index.html",
    "status": "ok",
    "note": "jpaas-jact 网关（http），列表 JSON find-mail-pub-list，count=250；明细 mail-pub-detail",
}

BASE = "http://www.jinan.gov.cn/api-gateway/jpaas-jact-web-server/front"
PLATFORM_UID = "HTMi0SM6aXpdnEJDZH931"
#: 「回应关切」聚合的部门信箱 id（取自首页链接 submitTargetIds）
SUBMIT_TARGET_IDS = (
    "0114,0171,0115,0116,0117,0118,0119,0120,0121,0123,0124,0126,0127,0128,0130,0132,"
    "0134,0135,0140,0141,0144,0146,0148,0151,0156,0133,0159,0160,0163,0161,0137,0166,"
    "0138,0149,0513,2203,2414,2422,0515,2479,2583,0145,622fntKBvD,sk7AtT5lCN,0147,"
    "1BF7PVWSQb,0152,0324,1921"
)
REFERER = "http://www.jinan.gov.cn/col/col26/index.html"
PAGE_SIZE = 19
PAUSE = 1.5
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")

#: 明细页标签（去空格后比较，页面里是「标 题：」这种带空格的写法）
LABELS = ("标题", "内容", "提交时间", "答复部门", "答复日期", "答复内容", "答复附件")


def _clean(s: str | None) -> str:
    if not s:
        return ""
    return _html.unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", s))).strip()


def _detail(fetch, iid: str) -> dict:
    r = fetch(f"{BASE}/mail-pub-detail?iid={iid}", headers={"Referer": REFERER})
    if getattr(r, "status_code", 0) != 200:
        return {}
    cells = [_clean(x) for x in TD_RE.findall(r.text or "")]
    out: dict[str, str] = {}
    for i, c in enumerate(cells):
        key = c.replace(" ", "").rstrip("：:")     # 「标 题：」→「标题」；值保持原样
        if key in LABELS and i + 1 < len(cells):
            out[key] = cells[i + 1]
    return out


def harvest(fetch, *, limit: int | None = None, max_pages: int = 60) -> list[dict]:
    """翻页取济南「回应关切」列表，逐条取明细拿答复正文。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        url = (f"{BASE}/find-mail-pub-list?pageNum={page}&pageSize={PAGE_SIZE}"
               f"&platformUid={PLATFORM_UID}&submitTargetIds={SUBMIT_TARGET_IDS}&govOpen=1")
        r = fetch(url, headers={"Referer": REFERER})
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            body = r.json()
            items = body.get("data") or []
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        if total is None:
            total = body.get("count")
            print(f"    [{SITE['key']}] {BASE} count={total}")
        fresh = [it for it in items if str(it.get("iid")) not in seen]
        print(f"    [{SITE['key']}] 第 {page} 页：{len(items)} 条，新增 {len(fresh)}")
        if not fresh:
            break
        for it in fresh:
            if limit and len(out) >= limit:
                return out
            iid = str(it.get("iid") or "")
            if not iid:
                continue
            seen.add(iid)
            time.sleep(PAUSE)
            f = _detail(fetch, iid)
            answer = f.get("答复内容", "").strip()
            if not answer:
                continue
            title = f.get("标题") or it.get("title") or ""
            cont = f.get("内容", "")
            question = title if not cont else f"{title}\n{cont}"
            out.append({
                "source": SITE["key"],
                "id": iid,
                "url": f"{BASE}/mail-pub-detail?iid={iid}",
                "question": question,
                "answer": answer,
                "asked_at": f.get("提交时间") or None,
                "answered_at": f.get("答复日期") or None,
                "dept": f.get("答复部门") or it.get("submitTargetName") or None,
                "channel": "互动交流·回应关切",
                "extra": {
                    "transact_no": it.get("transactNo"),
                    "platform_uid": PLATFORM_UID,
                    "answer_kind": "办理答复（jact 网关，多为办事指引/政策口径）",
                },
            })
        if len(items) < PAGE_SIZE:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条（站内自报 {total}）")
    return out
