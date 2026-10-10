"""适配器：**亳州市·信件选登**（`/InFeedback/`，安徽第 3 个可采市级源）。

## 站点事实（2026-10-10 实测）

- 列表 `https://www.bozhou.gov.cn/InFeedback/showList/1/page_1.html`
  **服务端渲染**，每页 12 条（站点自报 `pagecount=14 total=163`）
- 详情 `/InFeedback/show/<id>.html` **服务端渲染**，**表格式**结构：

  ```html
  <section class="m-maildetail">
  <table class="table table-bordered"><tbody>
    <tr><td class="u-tit"><div>信件标题</div></td><td colspan="4">…</td></tr>
    <tr><td class="u-tit"><div>信件来源</div></td><td class="u-item">政府网站</td>
        <td class="u-tit"><div>来信时间</div></td><td class="u-item">2026-04-02 08:31</td></tr>
    <tr><td class="u-tit"><div>信件内容</div></td><td class="u-desc" colspan="4">…</td></tr>
    <tr><td class="u-tit"><div>办理部门</div></td><td class="u-item">市科技局</td>
        <td class="u-tit"><div>办理时间</div></td><td class="u-item">2026-04-07 17:12</td></tr>
    <tr><td class="u-tit"><div>回复内容</div></td><td class="u-desc" colspan="4">…</td></tr>
  </tbody></table></section>
  ```

  ⇒ **`u-tit` 是字段名、紧邻的 `u-item`/`u-desc` 是值** —— 按这个配对抽，比按标签切块稳。

## ★★ 重要：**首页是"登录页" ≠ 这个入口不可采**

上一轮侦察把亳州标成「⚠ 首页即登录页」。本轮实测：
**首页正文确实含「账号登录/获取验证码」**（那是页头的用户入口），
但 **`/InFeedback/showList/` 这个具体入口完全公开**，返回 10 条详情链接、`total=163`。

⇒ **纪律：判"登录页"要看目标入口，不能只看首页。**
（与开封/焦作的教训同族：**同一个站可能同时暴露"要登录的"和"公开的"。**）

## 质量（铁律第 6 条）

答复 **900+ 字**，分七点列审批条件，含具体金额/面积/时限与**联系电话**（`5606917`）
⇒ **优质考卷料**。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "bz-hdjl",
    "name": "亳州市·政民互动·信件选登",
    "kind": "static",
    "level": "city",
    "region": "亳州市",
    "entry": "https://www.bozhou.gov.cn/InFeedback/showList/1/page_1.html",
    "status": "ok",
    "note": "服务端渲染 /InFeedback/showList/1/page_N.html（N 从 1 起，每页 12 条）；"
            "详情表格式（u-tit 字段名 + u-item/u-desc 值）；实测 pagecount=14 total=163；"
            "⚠ 首页含登录入口但**本入口公开**",
}

BASE = "https://www.bozhou.gov.cn"
LIST_TPL = BASE + "/InFeedback/showList/1/page_{page}.html"
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
    for path, mid, raw in re.findall(
            r'<a[^>]+href="(/InFeedback/show/([^"/]+)\.html)"[^>]*>(.*?)</a>',
            html, re.S):
        if mid in seen:
            continue
        seen.add(mid)
        t = _real(raw)
        if not t or len(t) < 2:
            continue
        out.append({"id": mid, "title": t, "url": BASE + path})
    return out


def _parse_total(html: str) -> dict:
    m = re.search(r'<pagination\b([^>]*)>', html)
    if not m:
        return {}
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
    out = {}
    for k in ("pagecount", "total", "pagesize"):
        if attrs.get(k, "").isdigit():
            out[k] = int(attrs[k])
    return out


def _fields(html: str) -> dict:
    """从表格式详情里抽 `{字段名: 值}`。

    结构：`<td class="u-tit" …><div>字段名</div></td>` 后面紧跟**该字段的值格**。
    实测值格有两种：
      · `<td class="u-item">值</td>` / `<td class="u-desc" colspan="4">值</td>`
      · **`<td colspan="4">值</td>`（没有 class）** ← 「信件标题」就是这种

    ⇒ 按「u-tit 的位置」切段，段内取**第一个** `<td>`（不要求它有 class）。
    ⚠ 我第一版只认 `u-item|u-desc` ⇒ **「信件标题」恒为空**（测试抓到）。
    """
    out: dict = {}
    marks = [(m.start(), m.end()) for m in
             re.finditer(r'<td[^>]*class="[^"]*u-tit[^"]*"[^>]*>(.*?)</td>', html, re.S)]
    for i, (s, e) in enumerate(marks):
        name = _real(re.sub(r"<[^>]+>", " ", html[s:e]))
        nxt = marks[i + 1][0] if i + 1 < len(marks) else len(html)
        seg = html[e:nxt]
        m2 = re.search(r"<td[^>]*>(.*?)</td>", seg, re.S)
        if m2 and name:
            out.setdefault(name, _real(m2.group(1)))
    return out


def _parse_detail(html: str) -> dict:
    """详情页 → 统一记录字段。"""
    f = _fields(html)
    out = {
        "question": f.get("信件内容") or "",
        "answer": f.get("回复内容") or "",
        "asked_at": f.get("来信时间") or f.get("留言时间") or None,
        "answered_at": f.get("办理时间") or f.get("回复时间") or None,
        "dept": f.get("办理部门") or f.get("回复部门") or None,
        "title": f.get("信件标题") or None,
        "msg_type": f.get("信件类型") or f.get("留言类型") or None,
        "source": f.get("信件来源") or None,
    }
    # 兜底：标题从 h1 拿
    if not out["title"]:
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if m:
            out["title"] = _real(m.group(1)) or None
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
                if n_detail % 25 == 0:
                    print(f"    [{SITE['key']}] 明细进度 {n_detail}"
                          f"（无答复 {n_fail}）", flush=True)
                time.sleep(PAUSE)
                continue
            if n_detail % 25 == 0:
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
                "dept": det.get("dept"),
                "channel": "信件选登",
                "extra": {
                    "title": det.get("title") or it["title"],
                    "msg_type": det.get("msg_type"),
                    "letter_source": det.get("source"),
                    "platform": "亳州市政府门户（InFeedback 服务端渲染）",
                },
            })
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条；明细取 {n_detail} 条，其中无答复 {n_fail} 条")
    return out
