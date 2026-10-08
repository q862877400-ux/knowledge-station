"""适配器：**安徽省直部门 · 共享问答知识库**（全省站群聚合，跨厅局）。

## 形态判断（2026-10-08 实探，证据 recon/ah-ln-hunt.txt）
安徽省级部门站是**集约化站群 CMS**（页面 `data-setting` 里 `platformCode:'anhui_szbm_*'`），
**全部厅局共用一个「答问知识库」label**：
 · 列表：`GET {任一厅域名}/site/label/8888?labelName=knowledgeBaseList&action=page
        &pageSize=200&pageIndex=N` —— **返回的是跨厅局聚合**（条目 href 指向不同厅域名），
        实测 `pageSize=200` 有效、`pageIndex` 翻页有效，**共 2282 条**（12 页）；
 · 明细：各厅自己的 `https://<dept>.ah.gov.cn/<hdjl|hdhy|zmhd|gzcy>/dwzsk/<id>.html`，
        模板统一为 `问 【问题】 答 【答复】`（老模板）；个别条目答复是附件（「点击查看」）会被跳过。

⇒ **不是"每厅一个薄适配器"**，而是**一条接口覆盖全省所有厅局**（同湖南统一平台的性质）。
故本适配器即安徽全省问答知识库，无需按厅局复制。
"""
from __future__ import annotations

import re
import time
from urllib.parse import urlparse

SITE = {
    "key": "ah-kb",
    "name": "安徽省直部门·共享问答知识库",
    "kind": "api",
    "level": "province",
    "entry": ("https://sthjt.ah.gov.cn/site/label/8888"
              "?labelName=knowledgeBaseList&action=page&pageSize=200&pageIndex=1"),
    "status": "ok",
    "note": "全省站群共享知识库（label 8888），跨厅局聚合 2282 条；pageIndex 翻页，明细为各厅 /dwzsk/<id>.html",
}

#: 列表宿主：任一厅域名都行（实测 sthjt/jtt/lyj 均可；www.ah.gov.cn 返回 0）
LIST_HOST = "https://sthjt.ah.gov.cn"
LIST_URL = LIST_HOST + "/site/label/8888"
LIST_QUERY = ("labelName=knowledgeBaseList&action=page&result=&isDate=true"
              "&dateFormat=yyyy-MM-dd&isLine=false&categoryCode=&organDn=&wenda_keywords=")
PAGE_SIZE = 200
PAUSE = 1.0

LI_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.S)
URL_RE = re.compile(r'<a href="(https?://[^"]+)"[^>]*title="([^"]*)"')
DATE_RE = re.compile(r'class="right date">\s*([0-9]{2}-[0-9]{2})')
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
TITLE_TAG_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
QA_RE = re.compile(r"\s问\s*(.*?)\s*答\s+(.*?)(?:打印本页|联系我们|主办单位|网站地图|$)", re.S)
FOOT_CUT = re.compile(r"(打印本页|联系我们|主办单位|网站地图|备案编号|皖ICP)")
PUB_RE = re.compile(r"发布时间[：:]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}(?:\s+[0-9:]{4,5})?)")
SRC_RE = re.compile(r"来源[：:]\s*([^ ]{2,40})")


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _parse_items(html: str) -> list[tuple[str, str, str | None]]:
    """从列表片段抠 (明细URL, 标题, 日期)。"""
    out = []
    for blk in LI_RE.findall(html):
        m = URL_RE.search(blk)
        if not m:
            continue
        dm = DATE_RE.search(blk)
        out.append((m.group(1), _text(m.group(2)), dm.group(1) if dm else None))
    return out


def _parse_detail(html: str, fallback_title: str) -> dict | None:
    text = _text(html)
    # 导航里含「答问知识库」字样，直接在全文匹配会锚错；正文从「来源：」之后开始。
    idx = text.rfind("来源：")
    body = text[idx:] if idx >= 0 else text
    m = QA_RE.search(body) or QA_RE.search(text)
    if not m:
        return None
    question = FOOT_CUT.split(m.group(1))[0].strip()
    answer = FOOT_CUT.split(m.group(2))[0].strip()
    if not question:
        tm = TITLE_TAG_RE.search(html)
        question = (fallback_title or "").strip() or (
            _text(tm.group(1)).split("_")[0] if tm else "")
    if len(question) < 4 or len(answer) < 10:
        return None
    pub = PUB_RE.search(text)
    src = SRC_RE.search(text)
    return {"question": question[:300], "answer": answer,
            "asked_at": pub.group(1) if pub else None,
            "source_note": src.group(1).strip() if src else None}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 20) -> list[dict]:
    """按 pageIndex 翻页取全省共享知识库列表，再逐条取各厅明细（按 id 去重）。"""
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        url = f"{LIST_URL}?{LIST_QUERY}&pageSize={PAGE_SIZE}&pageIndex={page}"
        r = fetch(url)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        items = _parse_items(r.text or "")
        fresh = [(u, t, d) for u, t, d in items if u not in seen]
        if not fresh:
            break
        print(f"    [{SITE['key']}] 第 {page} 页：条目 {len(items)}，新增 {len(fresh)}")
        for u, title, date in fresh:
            if limit and len(out) >= limit:
                return out[:limit]
            seen.add(u)
            time.sleep(PAUSE)
            d = fetch(u)
            if getattr(d, "status_code", 0) != 200:
                continue
            try:
                rec = _parse_detail(d.text or "", title)
            except Exception as e:                                      # noqa: BLE001
                print(f"    [{SITE['key']}] 解析失败 {u[-20:]} {type(e).__name__}")
                continue
            if not rec:
                continue
            host = urlparse(u).netloc
            uid = u.rsplit("/", 1)[-1].replace(".html", "")
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": u,
                "question": rec["question"] or title,
                "answer": rec["answer"],
                "asked_at": rec["asked_at"] or date,
                "answered_at": None,
                "dept": rec.get("source_note") or host,
                "channel": "互动交流·答问知识库（全省共享）",
                "extra": {"dept_host": host,
                          "list_url": LIST_URL,
                          "answer_kind": "办理答复（知识库，常点名依据）",
                          "source_note": rec.get("source_note")},
            })
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条（按 id 去重；栏目自报 2282）")
    return out
