"""适配器：**云南省网上信访平台 · 案例选登**（网络问政公开问答）。

## 形态判断（2026-10-08 实探，证据 recon/jx-yn-hunt.txt）
云南**门户 www.yn.gov.cn 是 CMS**，其搜索已外包给第三方（`/searchfs/index_826.html`
→ frameset 指向 `https://sheng.so-gov.cn/`），页面里**并无 WAS5 检索入口**：
旧记的 `/was5/web/search?channelid=639/3820` 返回 711B 的 `TRSWAS5.1` 404 空页，
639/3820 只是 CMS 栏目号 —— **WAS5 这条线不通**（门户已无可用问答检索频道）。

真正可采的公开问答在**信访域名** `xfservice.yn.gov.cn`（与 `www.yn.gov.cn` 不同站）：
 · 门户「网络问政/我要咨询」页实为 iframe 提交表单（`/userhome/12345/submit`）+ 信访链接；
 · 信访站的 Vue SPA（`/wsxf/...`）网关对**非白名单路径**一律回
   `401 {"code":"400","message":"无效请求头"}`（伪路径同样 401，故不能据此判端点存在）；
   其 `Authorization` 头是登录后 JWT（`tokenHead+token`），公开抓取拿不到 —— 该线不通。
 · 但信访站有一套**免鉴权白名单接口** `/api/website/v1/newsRends/*`，其中「案例选登」
   栏目即公开问答：`GET {host}/api/website/v1/newsRends/pageList
        ?current=<页>&pageSize=<条>&type=case_selection&newsTypeId=1`
   → `{success,total,list:[{id,title,releaseDate,source,hit,content,...}]}`，**实测 total=66**。
   正文 `content` 已含**全文**（提问「…网民反映：」+ 答复「…回复：」），
   与详情接口 `/api/website/v1/newsRends/query/<id>` 返回的 content 完全一致（1269B 相等），
   故**列表即可入库，无需再逐条抓明细**（更省请求、更礼貌）。

⇒ **接口型可用**（免鉴权、200、真实问答 66 条）；问答正文形如
   `{日期}网民反映：{问题} {日期}{单位}回复：{答复}`，答复单位多含市局/支队/公司。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "yn-xf",
    "name": "云南省网上信访平台·案例选登",
    "kind": "api",
    "level": "province",
    "entry": "https://xfservice.yn.gov.cn/alxd/",
    "status": "ok",
    "note": "免鉴权白名单接口 newsRends/pageList?type=case_selection，total=66；正文含问+答全文",
}

HOST = "https://xfservice.yn.gov.cn"
LIST_URL = HOST + "/api/website/v1/newsRends/pageList"
#: 公开问答栏目：案例选登（=网络问政问答公开稿，来源多为「人民网—领导留言板」）
CASE_TYPE = "case_selection"
NEWS_TYPE_ID = 1
PAGE_SIZE = 50
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
ASK_RE = re.compile(r"网民反映\s*[：:]")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
#: 答复起始标记（三种写法都实测出现）：
#:   ①「回复：/答复：/回复;」 ②「官方回复」 ③「{日期}{单位}：」（无「回复」二字）
OFFICIAL_RE = re.compile(r"官方回复")
REPLY_RE = re.compile(r"(?:回复|答复)\s*[：:;；]")
UNIT_DATE_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s*"
    r"([^\s：:]{2,40}?(?:委员会|办公室|办事处|支队|集团|政府|公司|中心|医院|街道|局|委|厅|部|段|所|队|处|科))"
    r"\s*[：:]"
)
#: 「官方回复」后紧跟的单位名（形如「官方回复 昆明市文化和旅游局 网民同志：您好！」）
DEPT_HEAD_RE = re.compile(
    r"\s*([^\s：:]{2,40}(?:委员会|办公室|办事处|支队|集团|政府|公司|中心|医院|街道|局|委|厅|部))"
)


def _text(html: str | None) -> str:
    raw = (html or "").replace("&nbsp;", " ").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", raw))).strip()


def _split_qa(text: str) -> tuple[str, str, str | None, str | None, str | None]:
    """把 `{日期}网民反映：{问} {日期}{单位}回复：{答}` 拆成 (问, 答, 问日, 答日, 单位)。

    兼容三种答复标记（见上）。缺标记时答为空（调用方按 Q&A 要求丢弃该条）。
    """
    ma = ASK_RE.search(text)
    qstart = ma.end() if ma else 0
    asked_at = None
    if ma:
        dm = DATE_RE.search(text[:ma.start()])
        asked_at = dm.group() if dm else None

    # 在问题起点之后，找最早的答复标记
    cands = []
    for rx in (OFFICIAL_RE, REPLY_RE, UNIT_DATE_RE):
        m = rx.search(text, qstart)
        if m:
            cands.append((m.start(), rx, m))
    if not cands:
        return text[qstart:].strip(), "", asked_at, None, None
    _, rx, m = min(cands, key=lambda c: c[0])

    answer = text[m.end():].strip()
    answered_at = None
    dept = None
    if rx is UNIT_DATE_RE:
        answered_at = m.group(1)
        dept = m.group(2)
        head = text[qstart:m.start()].strip()
    else:
        pre = text[qstart:m.start()]
        dates = list(DATE_RE.finditer(pre))
        if dates:
            last = dates[-1]
            answered_at = last.group()
            dept = pre[last.end():].strip() or None
            head = pre[:last.start()].strip()
        else:
            head = pre.strip()
        if rx is OFFICIAL_RE and not dept:
            dm2 = DEPT_HEAD_RE.match(answer)
            dept = dm2.group(1) if dm2 else None

    question = head
    # head 里若还残留「网民反映：」之前的前缀日期，去掉
    ma2 = ASK_RE.search(head)
    if ma2:
        question = head[ma2.end():].strip()
    return question, answer, asked_at, answered_at, dept


def _one(item: dict) -> dict | None:
    text = _text(item.get("content"))
    question, answer, asked_at, answered_at, dept = _split_qa(text)
    title = _text(item.get("title"))
    if not question:
        question = title
    if not question or len(question) < 4:
        return None
    if not answer or len(answer) < 10:
        return None
    rid = str(item.get("id"))
    return {
        "source": SITE["key"],
        "id": rid,
        "url": f"{HOST}/alxd/detail.html?id={rid}",
        "question": question[:400],
        "answer": answer,
        "asked_at": asked_at or item.get("releaseDate"),
        "answered_at": answered_at,
        "dept": dept,
        "channel": "案例选登（网络问政公开问答）",
        "extra": {
            "title": title,
            "src": _text(item.get("source")),
            "hit": item.get("hit"),
            "release_date": item.get("releaseDate"),
            "answer_kind": "办理答复（信访/网络问政公开稿，常点名单位与依据）",
        },
    }


def harvest(fetch, *, limit: int | None = None, max_pages: int = 20) -> list[dict]:
    """翻页取「案例选登」公开问答（列表已含全文，无需再抓明细）。"""
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            return out[:limit]
        params = {"current": page, "pageSize": PAGE_SIZE,
                  "type": CASE_TYPE, "newsTypeId": NEWS_TYPE_ID}
        r = fetch(LIST_URL, params=params)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            body = r.json()
            data = body.get("data") or {}
            items = data.get("list") or []
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        if not items:
            break
        fresh = 0
        for it in items:
            rid = str(it.get("id"))
            if rid in seen:
                continue
            seen.add(rid)
            rec = _one(it)
            if rec:
                out.append(rec)
                fresh += 1
            if limit and len(out) >= limit:
                return out[:limit]
        print(f"    [{SITE['key']}] 第 {page} 页：{len(items)} 条，入库 {fresh}")
        if len(items) < PAGE_SIZE:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条（栏目自报 66）")
    return out
