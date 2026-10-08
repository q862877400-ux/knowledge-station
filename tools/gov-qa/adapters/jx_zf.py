"""适配器：**江西省人民政府 · 数融互动**（我向省长建言 + 政策问答库）。

## 形态判断（2026-10-08 实探，证据 recon/jx-yn-hunt.txt）
江西省级部门站是**数融站群 CMS**（同一套引擎，各站以 `websiteCode` 区分；
`config.js` 里 `aggregationWebsiteCod` 列了 34 个省直部门域名）。
互动数据的接口**藏在打包 JS 里**，从 `pc2024/js/config.js` + `commonApi.js` 抠出：

 · 列表/详情：`POST {host}/queryList`（数融稿件检索）
     form 参数：`current`（页码）、`pageSize`、`channelCode`（栏目代号）、`webSiteCode`（站点代号）
     响应：`{data:{total,results:[{source:{id,title,pubDate,content:{content},metadata,urls}}]}}`
 · 按 id 取单篇：`GET {host}/getManuscriptById?id=<id>`（同上结构；列表已带全文，通常不必再调）

两个**问答栏目**（webSiteCode=jxsrmzf，即省政府站）：
 · `wxszj` 「我向省长建言」259 条：问题在 `content.content`，**答复在 `metadata.field_1596`**，
   回复单位 `field_1662`，提问/答复日期 `field_1594/1595`（答复常由多个厅局分别作出）；
 · `hygz` 「政策问答库」430 条：`content.content` 内联 `问：… 答：…`（答复常点名依据）。

⇒ **接口型可用**；且是**统一平台**（换 `webSiteCode`/`channelCode` 可扩其它厅站，见证据文件）。
"""
from __future__ import annotations

import json
import re
import time

SITE = {
    "key": "jx-zf",
    "name": "江西省人民政府·数融互动",
    "kind": "api",
    "level": "province",
    "entry": "https://www.jiangxi.gov.cn/jxsrmzf/hdjl/pc/list.html",
    "status": "ok",
    "note": "数融站群：POST /queryList（channelCode+webSiteCode）；wxszj 259 + hygz 430",
}

HOST = "https://www.jiangxi.gov.cn"
LIST_URL = HOST + "/queryList"
WEB_SITE = "jxsrmzf"
#: (channelCode, 栏目名)
CHANNELS = [("wxszj", "我向省长建言"), ("hygz", "政策问答库")]
PAGE_SIZE = 50
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
QA_SPLIT = re.compile(r"问\s*[：:]\s*(.*?)\s*答\s*[：:]\s*(.*)", re.S)


def _text(h: str | None) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", h or "")).strip()


def _one(source: dict, channel_label: str) -> dict | None:
    md = {}
    raw_md = source.get("metadata")
    if isinstance(raw_md, str) and raw_md.strip():
        try:
            md = json.loads(raw_md)
        except Exception:                                          # noqa: BLE001
            md = {}
    content = ""
    c = source.get("content")
    if isinstance(c, dict):
        content = _text(c.get("content"))
    elif isinstance(c, str):
        content = _text(c)
    title = _text(source.get("title"))
    answer = _text(md.get("field_1596"))          # wxszj：答复在元数据
    question = content
    # hygz：正文内联「问：…答：…」
    m = QA_SPLIT.search(content)
    if m:
        question = m.group(1).strip() or title
        if not answer:
            answer = m.group(2).strip()
    if not answer:
        return None
    if not question:
        question = title
    if len(question) < 4 or len(answer) < 10:
        return None
    urls = source.get("urls")
    try:
        url = (json.loads(urls) or {}).get("pc") if urls else None
    except Exception:                                              # noqa: BLE001
        url = None
    if url and url.startswith("/"):
        url = HOST + url
    return {
        "source": SITE["key"],
        "id": str(source.get("id")),
        "url": url or SITE["entry"],
        "question": question[:400],
        "answer": answer,
        "asked_at": md.get("field_1594") or source.get("pubDate"),
        "answered_at": md.get("field_1595"),
        "dept": _text(md.get("field_1662")) or None,
        "channel": channel_label,
        "extra": {
            "title": title,
            "channel_code": source.get("channelCode"),
            "website_code": source.get("websiteCode"),
            "answer_kind": "办理答复（建言/政策问答，常点名依据）",
        },
    }


def harvest(fetch, *, limit: int | None = None, max_pages: int = 20) -> list[dict]:
    """按栏目翻页取数融互动问答（列表已带全文，无需再抓明细）。"""
    out: list[dict] = []
    seen: set[str] = set()
    for code, label in CHANNELS:
        for page in range(1, max_pages + 1):
            if limit and len(out) >= limit:
                return out[:limit]
            data = {"current": page, "pageSize": PAGE_SIZE,
                    "channelCode": [code], "webSiteCode": [WEB_SITE]}
            r = fetch.post(LIST_URL, data=data)
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] {label} 第 {page} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）")
                break
            try:
                res = (r.json().get("data") or {}).get("results") or []
            except Exception as e:                                  # noqa: BLE001
                print(f"    [{SITE['key']}] {label} 第 {page} 页解析失败 {type(e).__name__}（停）")
                break
            if not res:
                break
            fresh = 0
            for it in res:
                src = it.get("source") or {}
                sid = str(src.get("id"))
                if sid in seen:
                    continue
                seen.add(sid)
                rec = _one(src, label)
                if rec:
                    out.append(rec)
                    fresh += 1
                if limit and len(out) >= limit:
                    return out[:limit]
            print(f"    [{SITE['key']}] {label} 第 {page} 页：{len(res)} 条，新增 {fresh}")
            if len(res) < PAGE_SIZE:
                break
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
