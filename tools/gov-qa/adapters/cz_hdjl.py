"""适配器：**池州市·市长信箱·留言选登**（`/InFeedback/`，安徽第 2 个可采市级源）。

## 站点事实（2026-10-10 实测）

- 列表 `https://www.chizhou.gov.cn/InFeedback/showList/2/page_1.html`
  **服务端渲染**，每页 10 条，详情链接 `/InFeedback/show/<id>.html`
- **分页**：页面里有 `<pagination currentpage="1" pagesize="10"
  pagecount="13" total="128"></pagination>` ⇒ **13 页 / 128 条**，
  URL 形态 `.../page_<N>.html`（**N 从 1 起**，与焦作的"从 0 起"不同）
- 详情 **服务端渲染**，结构（实测）：
  ```html
  <h1 class="u-lgtit …">商转公问题咨询</h1>
  <div class="message_con clearfix …">
    <div class="message_title … lx_title"><span>留言</span></div>
    <div class="message_nr_text …"><p>我想办理商转公，需要什么办理条件？</p></div>
    <div class="message_info"><span>留言类型：咨询</span><span>留言时间：2025-11-11 11:29</span></div>
  </div>
  <div class="message_con …">
    <div class="message_title … hf_title"><span>回复</span></div>
    <div class="message_nr_text …"><p>网友您好：…</p></div>
  </div>
  ```

## 质量（铁律第 6 条）

抽 1 条：答复 **600+ 字**，含具体办法名与**服务电话**（`0566-3220093`）
⇒ **非空且是优质考卷料**。

## ⚠ 分页形态**不能照抄别市**

| 市 | 分页形态 |
|---|---|
| 焦作 `jz-zxhf` | `index.html` / `index_1.html`（**页号从 0 起**）|
| 池州 `cz-hdjl` | `page_1.html` / `page_2.html`（**页号从 1 起**）|
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "cz-hdjl",
    "name": "池州市·市长信箱·留言选登",
    "kind": "static",
    "level": "city",
    "region": "池州市",
    "entry": "https://www.chizhou.gov.cn/InFeedback/showList/2/page_1.html",
    "status": "ok",
    "note": "服务端渲染 /InFeedback/showList/2/page_N.html（N 从 1 起）；"
            "详情 /InFeedback/show/<id>.html；实测 pagecount=13 total=128",
}

BASE = "https://www.chizhou.gov.cn"
LIST_TPL = BASE + "/InFeedback/showList/2/page_{page}.html"
DETAIL_TPL = BASE + "/InFeedback/show/{mid}.html"
PAUSE = 0.8
MAX_PAGES = 60

_TAG = re.compile(r"</?[A-Za-z][^>]*>")
_COMMENT = re.compile(r"<!--.*?-->|<![^>]*>", re.S)
_STRAY = re.compile(r"</[^<>]{0,80}?>")
_BR = re.compile(r"(?i)<br\s*/?>")
_P = re.compile(r"(?i)</p>")
_WS = re.compile(r"[ \t\r\f\v]+")


def _clean(s) -> str:
    if not s:
        return ""
    s = _COMMENT.sub(" ", str(s))
    s = _BR.sub("\n", s)
    s = _P.sub("\n", s)
    s = _TAG.sub("", s)
    s = _STRAY.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\xa0", " ")
    s = _WS.sub(" ", s)
    return re.sub(r"\n{2,}", "\n", s).strip()


def _real(v) -> str:
    s = _clean(v)
    return "" if s.strip().lower() in ("null", "none", "undefined") else s


def _parse_list(html: str) -> list:
    """列表页 → `[{id, title, url}]`（去重、保序）。"""
    out, seen = [], set()
    # ⚠ 正则有**三个**捕获组（path / id / title）—— 别只解两个
    #   （实测踩过：`ValueError: too many values to unpack (expected 2)`）。
    for path, mid, raw in re.findall(
            r'<a[^>]+href="(/InFeedback/show/(\d+)\.html)"[^>]*>(.*?)</a>',
            html, re.S):
        if mid in seen:
            continue
        seen.add(mid)
        t = _real(raw)
        if not t or len(t) < 4:
            continue
        out.append({"id": mid, "title": t, "url": BASE + path})
    return out


def _parse_total(html: str) -> dict:
    """从 `<pagination … pagecount="13" total="128">` 取总数与页数。"""
    m = re.search(r'<pagination\b([^>]*)>', html)
    if not m:
        return {}
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
    out = {}
    for k in ("pagecount", "total", "pagesize"):
        if attrs.get(k, "").isdigit():
            out[k] = int(attrs[k])
    return out


def _parse_detail(html: str) -> dict:
    """详情页 → `{question, answer, asked_at, answered_at, msg_type, title}`。

    结构（实测）：两个 `message_con` 块 —— 第一个是**留言**、第二个是**回复**。

    ⚠ 我第一版用「切到下一个 `message_con` 或三个 `</div>`」的正则切块 ——
    **脆**（测试里同样的 HTML 就切不出第二块 ⇒ 答复恒为空）。
    ⇒ 改为**按 `message_con` 的位置切**：取每个块的起点，块体是
    「起点 → 下一个起点（或文末）」，再在块里找 `message_nr_text` 与 `<span>`。
    """
    out = {"question": "", "answer": "", "asked_at": None,
           "answered_at": None, "msg_type": None, "title": None}
    m = re.search(r'<h1[^>]*class="[^"]*u-lgtit[^"]*"[^>]*>(.*?)</h1>', html, re.S)
    if m:
        out["title"] = _real(m.group(1))

    # 按 `message_con` 的**位置**切块（不靠闭合标签配对）
    starts = [mm.start() for mm in re.finditer(r'<div class="message_con\b', html)]
    blocks = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(html)
        blocks.append(html[s:e])

    # 判断哪个块是「回复」：看块里有没有 `hf_title` 或标题文字「回复/答复」
    def _is_reply(b: str) -> bool:
        return bool(re.search(r'hf_title', b)) or bool(
            re.search(r'<span>\s*(?:回复|答复)\s*</span>', b))

    for b in blocks[:2]:
        body = re.search(r'<div class="message_nr_text[^"]*">(.*?)</div>\s*</div>',
                         b, re.S) or re.search(
            r'<div class="message_nr_text[^"]*">(.*?)</div>', b, re.S)
        text = _real(body.group(1)) if body else ""
        if _is_reply(b):
            if not out["answer"]:
                out["answer"] = text
        elif not out["question"]:
            out["question"] = text
        for s in re.findall(r"<span>([^<]*)</span>", b):
            s = _real(s)
            if "留言时间" in s or "来信时间" in s:
                out["asked_at"] = _real(s.split("：", 1)[-1]) or None
            elif "回复时间" in s or "答复时间" in s:
                out["answered_at"] = _real(s.split("：", 1)[-1]) or None
            elif "留言类型" in s or "信件类型" in s:
                out["msg_type"] = _real(s.split("：", 1)[-1]) or None
    # 兜底：从整页文本里找时间/类型
    flat = _clean(html)
    if not out["asked_at"]:
        m2 = re.search(r"留言时间[：: ]{0,3}(\d{4}-\d{2}-\d{2}[ \d:]*)", flat)
        out["asked_at"] = m2.group(1).strip() if m2 else None
    if not out["answered_at"]:
        m2 = re.search(r"回复时间[：: ]{0,3}(\d{4}-\d{2}-\d{2}[ \d:]*)", flat)
        out["answered_at"] = m2.group(1).strip() if m2 else None
    if not out["msg_type"]:
        m2 = re.search(r"留言类型[：: ]{0,3}([^\s<]{1,10})", flat)
        out["msg_type"] = m2.group(1) if m2 else None
    return out


def harvest(fetch, *, limit: int | None = None, max_pages: int = MAX_PAGES) -> list[dict]:
    """翻列表（服务端渲染）+ 逐条取详情。

    ⚠⚠ **逐条取详情必须打进度点**（本模块为此踩过 5 次坑）。
    """
    out: list[dict] = []
    seen: set[str] = set()
    n_detail = n_fail = 0
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_TPL.format(page=page))
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页失败 {type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r,'status_code','?')}（停）")
            break
        items = _parse_list(r.text)
        if page == 1:
            meta = _parse_total(r.text)
            if meta:
                print(f"    [{SITE['key']}] 站点自报 pagecount={meta.get('pagecount')} "
                      f"total={meta.get('total')}", flush=True)
        print(f"    [{SITE['key']}] 列表第 {page} 页：{len(items)} 条", flush=True)
        if not items:
            break
        for it in items:
            if limit and len(out) >= limit:
                break
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            det = {}
            try:
                d = fetch(it["url"])
                if getattr(d, "status_code", 0) == 200:
                    det = _parse_detail(d.text)
            except Exception:                                           # noqa: BLE001
                det = {}
            n_detail += 1
            ans = det.get("answer") or ""
            if not ans:
                n_fail += 1
                if n_detail % 10 == 0:
                    print(f"    [{SITE['key']}] 明细进度 {n_detail}"
                          f"（无答复 {n_fail}）", flush=True)
                time.sleep(PAUSE)
                continue
            if n_detail % 10 == 0:
                print(f"    [{SITE['key']}] 明细进度 {n_detail}"
                      f"（无答复 {n_fail}）", flush=True)
            out.append({
                "source": SITE["key"],
                "id": it["id"],
                "url": it["url"],
                "question": det.get("question") or it["title"],
                "answer": ans,
                "asked_at": det.get("asked_at"),
                "answered_at": det.get("answered_at"),
                "dept": None,
                "channel": "留言选登",
                "extra": {
                    "title": det.get("title") or it["title"],
                    "msg_type": det.get("msg_type"),
                    "platform": "池州市政府门户（InFeedback 服务端渲染）",
                },
            })
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条；明细取 {n_detail} 条，其中无答复 {n_fail} 条")
    return out
