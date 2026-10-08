"""适配器：**住房和城乡建设部·政务咨询（留言选登）**（jpaas 静态构建接口）。

## 站点事实（2026-10-09 实测，证据 recon/nat-mohurd-*）
 · 栏目页 `https://www.mohurd.gov.cn/hudong/zwzx/index.html`（互动 → 政务咨询）。
 · 列表是 **jpaas-publish-server 的「单元构建」接口**（GET，免登录）：
   `GET https://www.mohurd.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit
        ?parseType=bulidstatic&webId=86ca573ec4df405db627fdc2493677f3
        &tplSetId=fc259c381af3496d85e61997ea7771cb&pageType=column
        &tagId=内容列表&editType=null&pageId=QydOZ61q6LsvHnuSdeecT
        &paramJson={"pageNo":<页>,"pageSize":<每页>,"loadEnabled":true,"search":"{}"}`
   → JSON `{"success":true,"data":{"html":"<div class=\"questionList-item\">…</div>…",
          …`pageNo`,`count` 分页信息在 html 里的 `queryData` 中}`
   ⚠ **分页必须靠 `paramJson`**（顶层 `pageNo`/`rows` 参数会被忽略；`paramJson` 是 JSON 字符串）。
   ⚠ `tagId=内容列表` 是中文，URL 编码交给 httpx 的 params。
 · **提问与答复在同一段 HTML 内联**（`.questionList-item`）：提问在 `.question-title` 后的 `<p>`，
   答复在 `.answer-box` 内 `<p>`；提问/答复日期在 `.info-date` / `.answer-date`。
 · 实测 count=672（`pageSize=20` ⇒ 34 页）。答复常引《文件》/GB（如「参照我部 2023 年 4 月 11 日政务咨询答复」）。
"""
from __future__ import annotations

import hashlib
import json
import re
import time

SITE = {
    "key": "nat-mohurd",
    "name": "住房和城乡建设部·政务咨询",
    "kind": "api",
    "level": "national",
    "entry": "https://www.mohurd.gov.cn/hudong/zwzx/index.html",
    "status": "ok",
    "note": "jpaas build/unit 接口；paramJson 控分页；问+答同页内联；count≈672",
}

API = "https://www.mohurd.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit"
REFERER = "https://www.mohurd.gov.cn/hudong/zwzx/index.html"
WEB_ID = "86ca573ec4df405db627fdc2493677f3"
TPL_SET_ID = "fc259c381af3496d85e61997ea7771cb"
PAGE_ID = "QydOZ61q6LsvHnuSdeecT"
TAG_ID = "内容列表"
PAGE_SIZE = 20
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", re.S | re.I)
ITEM_SPLIT = re.compile(r'<div[^>]*class="[^"]*questionList-item[^"]*"[^>]*>', re.I)
#: 提问正文：question-title 之后的第一个 <p>（内部还套一层 <p style=…>）
Q_RE = re.compile(r'class="[^"]*question-title[^"]*"[^>]*>.*?</p>\s*<p>\s*<p[^>]*>(.*?)</p>', re.S | re.I)
#: 提问日期：question-info 里第一个 info-date（非 answer-date）
ASK_RE = re.compile(r'class="[^"]*info-date[^"]*"[^>]*>\s*([\d\-./年月日]+)\s*</span>', re.I)
#: 答复日期
ANS_DATE_RE = re.compile(r'class="[^"]*answer-date[^"]*"[^>]*>\s*([\d\-./年月日]+)\s*</span>', re.I)
#: 答复正文：answer-box 内 answer-date 之后、</div> 后的 <p>
ANS_RE = re.compile(r'class="[^"]*answer-box[^"]*"[^>]*>(.*?)</div>\s*</div>', re.S | re.I)
ANS_P_RE = re.compile(r'<p[^>]*>(.*?)</p>', re.S | re.I)
USER_RE = re.compile(r'class="[^"]*info-user[^"]*"[^>]*>(.*?)</p>', re.S | re.I)
COUNT_RE = re.compile(r"'count'\s*:\s*'(\d+)'")
PAGE_RE = re.compile(r"'pageNo'\s*:\s*'(\d+)'")


def _text(html: str | None) -> str:
    if not html:
        return ""
    t = SCRIPT_RE.sub(" ", html)
    t = TAG_RE.sub(" ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", t).strip()


def _parse_items(html: str, page: int) -> list[dict]:
    """把一页 list HTML 拆成记录。"""
    out: list[dict] = []
    parts = ITEM_SPLIT.split(html)[1:]          # 第 0 段是表头
    for idx, seg in enumerate(parts):
        mq = Q_RE.search(seg)
        question = _text(mq.group(1)) if mq else ""
        # 答复：answer-box 段里取除「回复：」外的 <p>
        ma = ANS_RE.search(seg)
        answer = ""
        if ma:
            ps = [_text(p) for p in ANS_P_RE.findall(ma.group(1))]
            ps = [p for p in ps if p and p not in ("回复：", "回复")]
            answer = " ".join(ps).strip()
        if len(answer) < 10:
            continue
        m_ask = ASK_RE.search(seg)
        m_ans = ANS_DATE_RE.search(seg)
        asked_at = m_ask.group(1).strip() if m_ask else None
        answered_at = m_ans.group(1).strip() if m_ans else None
        mu = USER_RE.search(seg)
        user = _text(mu.group(1)) if mu else ""
        # 站内无稳定 id ⇒ 用「提问+日期」做稳定指纹（同一条重跑不变，便于去重）
        fp = hashlib.md5(f"{question}|{asked_at}".encode("utf-8")).hexdigest()[:16]
        out.append({
            "source": SITE["key"],
            "id": fp,
            "url": SITE["entry"],
            "question": question,
            "answer": answer,
            "asked_at": asked_at,
            "answered_at": answered_at,
            "dept": None,
            "channel": "政务咨询·留言选登",
            "extra": {
                "user": user,
                "page": page,
                "seq": idx,
                "platform": "jpaas-publish-server",
            },
        })
    return out


def _fetch_page(fetch, page: int, page_size: int) -> tuple[str, int | None, int | None]:
    param_json = json.dumps({"pageNo": page, "pageSize": page_size,
                             "loadEnabled": True, "search": "{}"}, ensure_ascii=False)
    r = fetch(API, params={
        "parseType": "bulidstatic", "webId": WEB_ID, "tplSetId": TPL_SET_ID,
        "pageType": "column", "tagId": TAG_ID, "editType": "null",
        "pageId": PAGE_ID, "paramJson": param_json,
    }, headers={"Referer": REFERER})
    if getattr(r, "status_code", 0) != 200:
        raise RuntimeError(f"HTTP {getattr(r, 'status_code', '?')}")
    html = (r.json().get("data") or {}).get("html") or ""
    mc = COUNT_RE.search(html)
    mp = PAGE_RE.search(html)
    return html, (int(mc.group(1)) if mc else None), (int(mp.group(1)) if mp else None)


def harvest(fetch, *, limit: int | None = None, page_size: int = PAGE_SIZE) -> list[dict]:
    """翻页取住建部政务咨询（问题 + 答复原文）。"""
    out: list[dict] = []
    page = 1
    total = None
    while True:
        try:
            html, total, _ = _fetch_page(fetch, page, page_size)
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页失败 {type(e).__name__}: {e}（停）")
            break
        if total is not None and page == 1:
            print(f"    [{SITE['key']}] count={total}")
        rows = _parse_items(html, page)
        print(f"    [{SITE['key']}] 第 {page} 页：解析 {len(rows)} 条")
        if not rows:
            break
        out.extend(rows)
        if limit and len(out) >= limit:
            return out[:limit]
        if total is not None and page * page_size >= int(total):
            break
        page += 1
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
