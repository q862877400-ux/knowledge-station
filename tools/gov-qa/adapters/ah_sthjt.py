"""适配器：**安徽省生态环境厅 · 问答知识库**（列表翻页 + 静态明细）。

## 站点形态（2026-10-07 实探，证据 recon/ah-column-notes.txt / ah-detail-debug.txt）
 · 列表页 `https://sthjt.ah.gov.cn/content/column/26703211`
   —— **翻页用查询串**：`?wenda_keywords=&pageSize=&categoryId=&organDn=&pageIndex=N`
   （源码：`Ls.pagination(... location.href = '/content/column/26703211?...&pageIndex=' + pageIndex)`）；
 · 列表条目：`<a href="https://sthjt.ah.gov.cn/zmhd/wdzsk/<id>.html" title="问题">…</a>`
   + `<span class="right date">YYYY-MM-DD</span>`；
 · 明细页清洗后：`标题 发表时间：… 来源：厅长信箱（安徽省生态环境厅） 问 【问题】 答 【答复】 打印本页 …`
   —— **用单字标记 `问`/`答` 切分**（实测有效，站上没有「解答内容」之类长标记）；
 · 栏目自报规模：综合政务 130 条 + 生态保护 15 条 = **145 条问题**。

## 说明
答复是**带依据的办理答复**（常点名《分类管理名录》等文件），比四川的 FAQ 简答更接近考卷口径；
`extra.answer_kind` 标注为「办理答复（知识库）」以便下游区分。
"""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin

SITE = {
    "key": "ah-st",
    "name": "安徽省生态环境厅·问答知识库",
    "kind": "static",
    "level": "province",
    "entry": "https://sthjt.ah.gov.cn/content/column/26703211",
    "status": "ok",
    "note": "列表按 pageIndex 翻页（约 145 条）+ 静态明细（问/答 单字标记）",
}

BASE = "https://sthjt.ah.gov.cn"
LIST_URL = BASE + "/content/column/26703211"
PAUSE = 1.0

ITEM_RE = re.compile(
    r'<a href="(https://sthjt\.ah\.gov\.cn/zmhd/wdzsk/\d+\.html)"[^>]*title="([^"]*)"',
    re.I)
DATE_RE = re.compile(r'<span class="right date">\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', re.I)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
PUB_RE = re.compile(r"发表时间[：:]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}(?:\s+[0-9:]{4,5})?)")
SRC_RE = re.compile(r"来源[：:]\s*([^ ]{2,40})")
TITLE_TAG_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
#: 两种模板实测（2026-10-07）：
#:  ① `问 【问题】 答 【答复】`（老条目）
#:  ② `问 答 【答复】`（新条目——**问题只在标题里**，问后为空）
#: 故「问」与「答」之间的内容设为可选，为空时回退到标题。
QA_RE = re.compile(r"\s问\s*(.*?)\s*答\s+(.*?)(?:打印本页|主办单位|网站地图|$)", re.S)
FOOT_CUT = re.compile(r"(打印本页|主办单位|网站地图|备案编号)")


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _parse_detail(html: str, fallback_title: str | None = None) -> dict | None:
    text = _text(html)
    # ⚠ 导航里含「问答知识库」字样，其中就有「问」「答」两个字——直接在全文上匹配会锚错，
    #   导致问题串进导航文字（实测出现过「问知识库 问答知识库 请问…」）。
    #   正文从「来源：」之后开始，故先截到那里再解析。
    idx = text.rfind("来源：")
    body = text[idx:] if idx >= 0 else text
    m = QA_RE.search(body)
    if not m:
        return None
    question = FOOT_CUT.split(m.group(1))[0].strip()
    answer = FOOT_CUT.split(m.group(2))[0].strip()
    if not question:
        # 模板②：问题不在正文里，取列表标题 / <title>（去掉「_安徽省生态环境厅」后缀）
        tm = TITLE_TAG_RE.search(html)
        cand = (fallback_title or "").strip() or (
            _text(tm.group(1)).split("_")[0] if tm else "")
        question = cand
    if len(question) < 4 or len(answer) < 10:
        return None
    pub = PUB_RE.search(text)
    src = SRC_RE.search(text)
    return {"question": question[:300], "answer": answer,
            "asked_at": pub.group(1) if pub else None,
            "source_note": src.group(1).strip() if src else None}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 40) -> list[dict]:
    """按分类（默认 / 综合政务 401 / 生态保护 411）翻页取列表，再逐条取明细（按 id 去重）。

    ⚠ 默认列表实测只到 86 条，而栏目自报总数 145（综合政务 401=130 + 生态保护 411=15）
    ⇒ 必须**按分类再翻一遍**才能补齐（源码 `searchClass(this,1,'401','401')`）。
    """
    out: list[dict] = []
    seen: set[str] = set()
    #: (categoryCode, 说明)
    cats: list[tuple[str, str]] = [("", "默认"), ("401", "综合政务"), ("411", "生态保护")]
    for code, label in cats:
        for page in range(1, max_pages + 1):
            if limit and len(out) >= limit:
                return out[:limit]
            url = (f"{LIST_URL}?wenda_keywords=&pageSize=&categoryId={code}"
                   f"&categoryCode={code}&organDn=&pageIndex={page}")
            r = fetch(url)
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] {label} 列表第 {page} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）")
                break
            html = r.text or ""
            items = ITEM_RE.findall(html)
            dates = DATE_RE.findall(html)
            fresh = [(u, t) for u, t in items if u not in seen]
            if not fresh:
                break
            print(f"    [{SITE['key']}] {label} 第 {page} 页：条目 {len(items)}，新增 {len(fresh)}")
            for idx, (u, title) in enumerate(fresh):
                if limit and len(out) >= limit:
                    return out[:limit]
                seen.add(u)
                time.sleep(PAUSE)
                d = fetch(u)
                if getattr(d, "status_code", 0) != 200:
                    continue
                rec = None
                try:
                    rec = _parse_detail(d.text or "", title)
                except Exception as e:                                      # noqa: BLE001
                    print(f"    [{SITE['key']}] 解析失败 {u[-16:]} {type(e).__name__}")
                if not rec:
                    continue
                pub = dates[idx] if idx < len(dates) else None
                uid = u.rsplit("/", 1)[-1].replace(".html", "")
                out.append({
                    "source": SITE["key"],
                    "id": uid,
                    "url": u,
                    "question": rec["question"] or title,
                    "answer": rec["answer"],
                    "asked_at": rec["asked_at"] or pub,
                    "answered_at": None,
                    "dept": "安徽省生态环境厅",
                    "channel": "互动交流·问答知识库",
                    "extra": {"list_url": LIST_URL,
                              "category": label,
                              "answer_kind": "办理答复（知识库，常点名依据）",
                              "source_note": rec.get("source_note")},
                })
    print(f"    [{SITE['key']}] 收 {len(out)} 条（按 id 去重；栏目自报 145）")
    return out
