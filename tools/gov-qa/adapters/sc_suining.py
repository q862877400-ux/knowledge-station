"""适配器：**遂宁市·互动交流·市长信箱（来信选登，服务端渲染 HTML）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe20/21.txt）
 · 互动栏目：`https://www.suining.gov.cn/szxx.html`（市长信箱·来信选登，服务端渲染）。
 · 列表：`GET /szxx.html?page=N`（1 基，每页 ≈11~15 条），条目链接形如
   `/mail/view.html?id=<md5>&bid=<md5>`。页面另有「查询码查信」`POST /mail/query`
   （按 queryCode 查单封，非公开列表，不用）。
 · 详情：`GET /mail/view.html?id=<id>&bid=<bid>`（服务端渲染），表格 `jg-item02`：
     来信信息：来信时间 / 来信编号 / 类型 / 来信标题 / 来信内容（`<div class="text">`）
     回复内容：回复时间 / 回复单位 / 答复内容（`<div class="reply">…<div class="text">`）
   ★ 答复全文在 `答复内容` 的 `<div class="text">`。
 · 样例：id `f9ac11afb8d9ae6f6dc76a7a77c9b7f8`「道路维修咨询」→ 遂宁经开区答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-suining",
    "name": "遂宁市·互动交流·市长信箱（来信选登）",
    "kind": "html",
    "level": "city",
    "entry": "https://www.suining.gov.cn/szxx.html",
    "status": "ok",
    "note": "服务端渲染 HTML：列表 /szxx.html?page=N + 详情 /mail/view.html?id=&bid=；答复在「答复内容」",
}

BASE = "https://www.suining.gov.cn"
LIST_TPL = BASE + "/szxx.html?page={p}"
VIEW_TPL = BASE + "/mail/view.html?id={id}&bid={bid}"
REFERER = SITE["entry"]
PAUSE = 1.2

_TAG = re.compile(r"<[^>]+>")
_ITEM_RE = re.compile(r'/mail/view\.html\?id=([0-9a-fA-F]+)&(?:amp;)?bid=([0-9a-fA-F]+)')
_Q_RE = re.compile(r'来信内容\s*</td>\s*<td[^>]*>.*?<div class="text">(.*?)</div>', re.S)
_A_RE = re.compile(r'<div class="reply">.*?<div class="text">(.*?)</div>', re.S)
_CELL = ('<td[^>]*class="td01"[^>]*>\\s*{lab}\\s*</td>\\s*'
         '<td[^>]*class="td02"[^>]*>(.*?)</td>')


def _clean(s) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(s))
    s = re.sub(r"(?i)</p>", "\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    return s.strip()


def _cell(html: str, label: str) -> str:
    m = re.search(_CELL.format(lab=re.escape(label)), html, re.S)
    return _clean(m.group(1)) if m else ""


def harvest(fetch, *, limit: int | None = None, max_pages: int = 200) -> list[dict]:
    """翻页取遂宁来信选登；列表条目 → 逐条取详情解析问答。"""
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_TPL.format(p=page), headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        items = []
        for m in _ITEM_RE.finditer(r.text):
            pair = (m.group(1), m.group(2))
            if pair not in items:
                items.append(pair)
        if not items:
            break
        new = 0
        for sid, bid in items:
            if limit and len(out) >= limit:
                return out
            if sid in seen:
                continue
            seen.add(sid)
            new += 1
            try:
                vr = fetch(VIEW_TPL.format(id=sid, bid=bid), headers={"Referer": REFERER})
                vh = vr.text
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                continue
            mq = _Q_RE.search(vh)
            ma = _A_RE.search(vh)
            question = _clean(mq.group(1)) if mq else ""
            answer = _clean(ma.group(1)) if ma else ""
            title = _cell(vh, "来信标题")
            if len(answer) < 10:            # 未答复，跳过
                continue
            if not question:
                question = title
            elif title:
                question = f"{title}\n{question}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": VIEW_TPL.format(id=sid, bid=bid),
                "question": question,
                "answer": answer,
                "asked_at": _cell(vh, "来信时间") or None,
                "answered_at": _cell(vh, "回复时间") or None,
                "dept": _cell(vh, "回复单位") or None,
                "channel": "互动交流·市长信箱·来信选登",
                "extra": {
                    "title": title,
                    "mail_type": _cell(vh, "类型"),
                    "serial_number": _cell(vh, "来信编号"),
                    "platform": "遂宁 服务端渲染 HTML（szxx.html + mail/view.html）",
                },
            })
            time.sleep(PAUSE)
        if new == 0:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
