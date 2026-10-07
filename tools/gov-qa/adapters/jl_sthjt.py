"""适配器：**吉林省生态环境厅 · 厅长信箱（留言选登）**——省/市/区**三级归属**的问答源。

## 接口（2026-10-07 逆向，证据 recon/jl-lyxd-api.txt / jl-ajax-full.js / jl-api-call.py）
站点把数据放在省级海云平台（`contextPath = https://haiyun.jl.gov.cn/IGI`），
列表页的 `ajax_index_cmy_20211110.js` 明写了两个公开方法：
 · **列表**：`GET /IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs
   &siteId=117&order=1&appId=96&groupId=172&pageIndex=N&pageSize=M`
   —— 返回 `datas.data[]`，含 `TITLE / CONTENT / SUBMITTIME / REPLYDEPT / METADATAID /
   ISREPLY / PROVINCE / CITY / AREA / REGION`；
 · **明细**：`GET /IGI/nbhd/openGovmsgbox.do?method=viewGovmsgbox&siteId=117&metadataId=<id>`
   —— 返回 `datas.REPLYS[].REPLYHTMLCONTENT`（**官方答复正文**）。

⚠ **必须带 `Referer: https://sthjt.jl.gov.cn/...`**，否则 403（实测：无 Referer 403 JSON，
带 Referer 200）。

## 价值
· **三级归属**：接口直接给 `PROVINCE / CITY / AREA`（实测「吉林省 / 延边朝鲜族自治州 / 延吉市」）
  —— 留言板只到省市两级，这里是**目前唯一能拿到县/区三级归属的通道**；
· 答复是**办理答复**（含具体条款、标准号，如 GB 22337-2008），考卷价值高。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "jl-st",
    "name": "吉林省生态环境厅·厅长信箱",
    "kind": "api",
    "level": "province",
    "entry": "https://sthjt.jl.gov.cn/zmhd/tzxx/lyxd/",
    "status": "ok",
    "note": "海云平台开放接口（listGovmsgboxs + viewGovmsgbox）；带省/市/区三级归属；须带 Referer",
}

BASE = "https://haiyun.jl.gov.cn/IGI"
SITE_ID = "117"
APP_ID = "96"
GROUP_ID = "172"
REFERER = "https://sthjt.jl.gov.cn/zmhd/tzxx/lyxd/"
LIST_TPL = (BASE + "/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
            "&siteId={sid}&order=1&appId={aid}&groupId={gid}&pageIndex={p}&pageSize={n}")
DETAIL_TPL = (BASE + "/nbhd/openGovmsgbox.do?method=viewGovmsgbox"
              "&siteId={sid}&metadataId={mid}")
PAUSE = 1.2
PAGE_SIZE = 20

TAG_RE = re.compile(r"<[^>]+>")


def _clean(html: str | None) -> str:
    if not html:
        return ""
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()


def _ts(ms) -> str | None:
    try:
        v = int(ms)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v / 1000))


def harvest(fetch, *, limit: int | None = None, max_pages: int = 30) -> list[dict]:
    """翻页取列表（只要已答复的），再逐条取明细拿答复正文。"""
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        url = LIST_TPL.format(sid=SITE_ID, aid=APP_ID, gid=GROUP_ID, p=page, n=PAGE_SIZE)
        r = fetch(url, headers={"Referer": REFERER})
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
                d = fetch(DETAIL_TPL.format(sid=SITE_ID, mid=mid),
                          headers={"Referer": REFERER})
                if getattr(d, "status_code", 0) == 200:
                    try:
                        replies = (d.json().get("datas") or {}).get("REPLYS") or []
                        answer = _clean(" ".join(
                            (x or {}).get("REPLYHTMLCONTENT") or "" for x in replies))
                    except Exception as e:                                  # noqa: BLE001
                        print(f"    [{SITE['key']}] 明细 {mid} 解析失败 {type(e).__name__}")
            if len(answer) < 10:
                continue
            question = _clean(it.get("CONTENT")) or _clean(it.get("HTMLCONTENT"))
            extra = {
                "title": _clean(it.get("TITLE")),
                "query_number": it.get("QUERYNUMBER"),
                "msg_type": it.get("GOVMSGBOXTYPE"),
                "province": it.get("PROVINCE"),
                "city": it.get("CITY"),
                "area": it.get("AREA"),
                "region": it.get("REGION"),
                "answer_kind": "办理答复（厅长信箱，常引条款/标准号）",
            }
            out.append({
                "source": SITE["key"],
                "id": str(mid),
                "url": f"https://sthjt.jl.gov.cn/zmhd/tzxx/lyxd/lyxdct.html?id={mid}&siteId={SITE_ID}",
                "question": question or extra["title"],
                "answer": answer,
                "asked_at": _ts(it.get("SUBMITTIME") or it.get("CRTIME")),
                "answered_at": _ts(it.get("REPLYTIME") or it.get("FINISHTIME")),
                "dept": _clean(it.get("REPLYDEPT") or it.get("DEALDEPTNAME")),
                "channel": "厅长信箱·留言选登",
                "extra": extra,
            })
            # 三级归属也写进 pForumNames，统一各通道的归属读取方式
            chain = [x for x in (extra["province"], extra["city"], extra["area"]) if x]
            if chain:
                out[-1]["extra"]["pForumNames"] = chain
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
