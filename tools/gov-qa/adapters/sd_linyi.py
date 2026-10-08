"""适配器：**临沂市·政民互动·网上信箱（服务端渲染 JSP）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city3-probe.txt、sd-city3-linyi-*.html）
 · 门户 `www.linyi.gov.cn` 网上信箱列表：
   `http://www.linyi.gov.cn/hd/szxx-list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1086`
   —— **纯服务端渲染**（无 JS 拉取），第 1 页 15 条，分页链接形如
   `?totalpage=63&PAGENUM=2&wbtreeid=1086&urltype=tree.TreeTempUrl` ⇒ 约 63×15≈945 条。
 · 列表项结构：`<a href="content-list.jsp?...&leadermailid=<HEX>">
   <div class="ly">在线咨询</div><div class="bt">标题</div>
   <div class="sj">日期</div><div class="zt">已回复</div></a>`。
 · 明细：`content-list.jsp?urltype=leadermail.LeaderMailContentUrl&wbtreeid=1086
   &leadermailid=<HEX>` → 服务端渲染表格，
   `titlestyle`/`contentstyle` 相邻 `<td>` 成对：流水号/标题/写信时间/信件内容/
   处理状态/**回复内容**/处理对象/处理时间。
 · ⚠ 本平台（`urltype=tree.TreeTempUrl` + `wbtreeid` + `content-list.jsp`）是
   **山东西部 CMS**（与潍坊/菏泽同源指纹），但临沂这个列表未加密、可直接抓。
 · `hygq.htm`（回应关切）无信件列表、无分页，**不采**。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sd-linyi",
    "name": "临沂市·政民互动·网上信箱（JSP）",
    "kind": "static",
    "level": "city",
    "entry": "http://www.linyi.gov.cn/hd/szxx-list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1086",
    "status": "ok",
    "note": "服务端渲染 JSP（urltype/wbtreeid），约 63 页；明细含回复内容",
}

BASE = "http://www.linyi.gov.cn/hd"
LIST_URL = (BASE + "/szxx-list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1086")
LIST_PAGE_TPL = (BASE + "/szxx-list.jsp?totalpage={tp}&PAGENUM={p}"
                 "&wbtreeid=1086&urltype=tree.TreeTempUrl")
DETAIL_TPL = (BASE + "/content-list.jsp?urltype=leadermail.LeaderMailContentUrl"
              "&wbtreeid=1086&leadermailid={mid}")
PAUSE = 1.3

ITEM_RE = re.compile(
    r'<a\s+href="(content-list\.jsp\?[^"]*?leadermailid=([0-9A-Fa-f]+))">\s*'
    r'<div class="ly">(.*?)</div>\s*<div class="bt">(.*?)</div>\s*'
    r'<div class="sj">(.*?)</div>\s*<div class="zt">(.*?)</div>', re.S)
PAIR_RE = re.compile(
    r'<td[^>]*class="titlestyle\d*"[^>]*>(.*?)</td>\s*'
    r'<td[^>]*class="contentstyle\d*"[^>]*>(.*?)</td>', re.S)
TAG_RE = re.compile(r"<[^>]+>")
TOTAL_RE = re.compile(r"totalpage=(\d+)")


def clean(s: str | None) -> str:
    """去标签 + 还原实体 + 压空白。"""
    if not s:
        return ""
    return re.sub(r"\s+", " ", _html.unescape(TAG_RE.sub(" ", s))).strip()


def _label(s: str) -> str:
    return re.sub(r"\s+", "", clean(s))


def parse_detail(html: str) -> dict[str, str]:
    """把 `titlestyle/contentstyle` 相邻 `<td>` 解析成 标签→值 字典。"""
    out: dict[str, str] = {}
    for lab, val in PAIR_RE.findall(html or ""):
        k = _label(lab)
        if k and k not in out:
            out[k] = clean(val)
    return out


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采临沂网上信箱（服务端渲染，含答复原文）。"""
    out: list[dict] = []
    first = fetch(LIST_URL)
    if getattr(first, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] 列表首页 HTTP "
              f"{getattr(first, 'status_code', '?')}（停）")
        return out
    html = first.text or ""
    m = TOTAL_RE.search(html)
    total_page = int(m.group(1)) if m else 1
    print(f"    [{SITE['key']}] 共 {total_page} 页")

    for page in range(1, total_page + 1):
        if limit and len(out) >= limit:
            break
        if page == 1:
            rows_html = html
        else:
            time.sleep(PAUSE)
            r = fetch(LIST_PAGE_TPL.format(tp=total_page, p=page))
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）")
                break
            rows_html = r.text or ""
        items = ITEM_RE.findall(rows_html)
        if not items:
            print(f"    [{SITE['key']}] 第 {page} 页无条目（停）")
            break
        print(f"    [{SITE['key']}] 第 {page}/{total_page} 页：{len(items)} 条")
        for href, mid, ly, bt, sj, zt in items:
            if limit and len(out) >= limit:
                break
            time.sleep(PAUSE)
            d = fetch(DETAIL_TPL.format(mid=mid), headers={"Referer": LIST_URL})
            if getattr(d, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 明细 {mid} HTTP "
                      f"{getattr(d, 'status_code', '?')}")
                continue
            f = parse_detail(d.text or "")
            answer = f.get("回复内容") or ""
            if len(answer) < 10:
                continue
            question = f.get("信件内容") or clean(bt)
            out.append({
                "source": SITE["key"],
                "id": mid,
                "url": DETAIL_TPL.format(mid=mid),
                "question": question,
                "answer": answer,
                "asked_at": f.get("写信时间") or clean(sj) or None,
                "answered_at": f.get("处理时间") or None,
                "dept": f.get("处理对象") or None,
                "channel": "网上信箱·在线咨询",
                "extra": {
                    "title": f.get("标题") or clean(bt),
                    "category": clean(ly),
                    "state": f.get("处理状态") or clean(zt),
                    "serial": f.get("流水号"),
                    "platform": "西部CMS(JSP)",
                    "answer_kind": "部门办理答复（含承办单位）",
                },
            })
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
