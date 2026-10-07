"""IGI 平台公共基座（`/IGI/nbhd/openGovmsgbox.do`）——**多省共用**的留言信箱开放接口。

## 平台识别（2026-10-07）
同一套接口在至少两省出现：
 · 吉林：`https://haiyun.jl.gov.cn/IGI`（siteId=117, appId=96, groupId=172），
   详情 `method=viewGovmsgbox&siteId=117&metadataId=<id>`；
 · 贵州：`https://sthj.guizhou.gov.cn/IGI`（siteId=501471, appId=590）。
⇒ 记入台账「**发现通用平台**」，加省只需补 (base, siteId, appId, groupId) 三个值。

## 通用调用契约
 · 列表：`GET {base}/nbhd/openGovmsgbox.do?method=listGovmsgboxs
   &siteId=&order=1&appId=&groupId=&pageIndex=N&pageSize=M`
 · 明细：`GET {base}/nbhd/openGovmsgbox.do?method=viewGovmsgbox&siteId=&metadataId=<id>`
 · ⚠ **必须带 Referer**（指向该厅站点的信箱页），否则服务端 403。
 · 记录字段：`TITLE / CONTENT / HTMLCONTENT / SUBMITTIME / REPLYTIME / REPLYDEPT /
   METADATAID / ISREPLY / PROVINCE / CITY / AREA / REGION / QUERYNUMBER / GOVMSGBOXTYPE`
   —— **含省/市/区三级归属**（本模块唯一的县级归属来源）。
"""
from __future__ import annotations

import re
import time

LIST_TPL = ("{base}/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
            "&siteId={sid}&order=1&appId={aid}&pageIndex={p}&pageSize={n}")
LIST_TPL_GROUP = (LIST_TPL + "&groupId={gid}")
DETAIL_TPL = ("{base}/nbhd/openGovmsgbox.do?method=viewGovmsgbox"
              "&siteId={sid}&metadataId={mid}")
PAUSE = 1.2
PAGE_SIZE = 20
TAG_RE = re.compile(r"<[^>]+>")


def clean(html: str | None) -> str:
    """去标签 + 压空白（答复正文是 HTML 片段）。"""
    if not html:
        return ""
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()


def ts(ms) -> str | None:
    """毫秒时间戳 → `YYYY-MM-DD HH:MM:SS`；非法/0 返回 None。"""
    try:
        v = int(ms)
    except (TypeError, ValueError):
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v / 1000)) if v > 0 else None


def harvest_igi(fetch, *, SITE: dict, base: str, site_id: str, app_id: str,
                group_id: str | None, referer: str,
                limit: int | None = None, max_pages: int = 30) -> list[dict]:
    """翻页取列表（仅已答复），逐条取明细拿答复正文，返回统一记录。"""
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        if group_id:
            url = LIST_TPL_GROUP.format(base=base, sid=site_id, aid=app_id,
                                        gid=group_id, p=page, n=PAGE_SIZE)
        else:
            url = LIST_TPL.format(base=base, sid=site_id, aid=app_id,
                                  p=page, n=PAGE_SIZE)
        r = fetch(url, headers={"Referer": referer})
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            rows = (r.json().get("datas") or {}).get("data") or []
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        if not rows:
            break
        answered = [x for x in rows if int(x.get("ISREPLY") or 0) == 1]
        print(f"    [{SITE['key']}] 第 {page} 页：{len(rows)} 条（已答复 {len(answered)}）")
        for it in answered:
            if limit and len(out) >= limit:
                break
            mid = it.get("METADATAID")
            answer = ""
            if mid:
                time.sleep(PAUSE)
                d = fetch(DETAIL_TPL.format(base=base, sid=site_id, mid=mid),
                          headers={"Referer": referer})
                if getattr(d, "status_code", 0) == 200:
                    try:
                        replies = (d.json().get("datas") or {}).get("REPLYS") or []
                        answer = clean(" ".join(
                            (x or {}).get("REPLYHTMLCONTENT") or "" for x in replies))
                    except Exception as e:                                  # noqa: BLE001
                        print(f"    [{SITE['key']}] 明细 {mid} 解析失败 {type(e).__name__}")
            if len(answer) < 10:
                continue
            extra = {
                "title": clean(it.get("TITLE")),
                "query_number": it.get("QUERYNUMBER"),
                "msg_type": it.get("GOVMSGBOXTYPE"),
                "province": it.get("PROVINCE"),
                "city": it.get("CITY"),
                "area": it.get("AREA"),
                "region": it.get("REGION"),
                "platform": "IGI",
                "answer_kind": "办理答复（厅长信箱，常引条款/标准号）",
            }
            chain = [x for x in (extra["province"], extra["city"], extra["area"]) if x]
            if chain:
                extra["pForumNames"] = chain
            out.append({
                "source": SITE["key"],
                "id": str(mid),
                "url": SITE["entry"] + f"?id={mid}",
                "question": clean(it.get("CONTENT")) or clean(it.get("HTMLCONTENT"))
                            or extra["title"],
                "answer": answer,
                "asked_at": ts(it.get("SUBMITTIME") or it.get("CRTIME")),
                "answered_at": ts(it.get("REPLYTIME") or it.get("FINISHTIME")),
                "dept": clean(it.get("REPLYDEPT") or it.get("DEALDEPTNAME")),
                "channel": "厅长信箱·信件公示",
                "extra": extra,
            })
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
