"""适配器：**德州市·政民互动·回应关切（服务端渲染列表 + 明细页）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city3-德州-回应.html、sd-city3-dz-detail.html）
 · 门户 `www.dezhou.gov.cn` 政民互动 `n1480/index.html`；回应关切列表
   `http://www.dezhou.gov.cn/n1480/n59452804/index.html`。
 · **列表是服务端渲染**（⚠ 早先误判「0 条」是因为 `<a href=...>` **未加引号**，
   正则要求引号故漏检）。列表项：
   `<li><a href=../../n1480/n59452804/c<ID>/content.html>标题</a><br>
     <table>…提交时间：… 答复时间：… 答复单位[…]…</table></li>`。
 · 分页：`index.html`（第 1 页）+ `index_71702096_1.html` … `index_71702096_16.html`
   （共 17 页，`maxPageNum=17`；⚠ 分页顺序非时序，需**全量遍历 + 按 id 去重**）。
   实测 17 页去重后 **161 条**。
 · 明细 `c<ID>/content.html`：`<th>问题描述：</th><td>…</td>` /
   `<th>答复内容：</th><td>…</td>` / `<th>答复时间：</th><td>…</td>` /
   `<th>答复单位：</th><td>…</td>`。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sd-dezhou",
    "name": "德州市·政民互动·回应关切（JSP）",
    "kind": "static",
    "level": "city",
    "entry": "http://www.dezhou.gov.cn/n1480/n59452804/index.html",
    "status": "ok",
    "note": "服务端渲染列表 17 页（index.html + index_71702096_1..16）；去重后 161 条",
}

BASE = "http://www.dezhou.gov.cn/n1480/n59452804/"
LIST_PAGES = ["index.html"] + [f"index_71702096_{i}.html" for i in range(1, 17)]
DETAIL_TPL = BASE + "c{mid}/content.html"
PAUSE = 1.2

ITEM_RE = re.compile(
    r"<li>\s*<a href=\.\./\.\./n1480/n59452804/c(\d+)/content\.html[^>]*>(.*?)</a>"
    r"(.*?)</li>", re.S)
SUBMIT_RE = re.compile(r"提交时间[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
REPLYTIME_RE = re.compile(r"答复时间[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
DEPT_RE = re.compile(r"答复单位[\[【]\s*([^\]】]*?)\s*[\]】]")
TH_TD_RE = re.compile(r"<th>\s*(.*?)\s*</th>\s*<td[^>]*>(.*?)</td>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


def clean(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", _html.unescape(TAG_RE.sub(" ", s))).strip()


def _label(s: str) -> str:
    return re.sub(r"[\s:：]+", "", clean(s))


def parse_detail(html: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for lab, val in TH_TD_RE.findall(html or ""):
        k = _label(lab)
        if k and k not in out:
            out[k] = clean(val)
    return out


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采德州回应关切（17 页列表 + 逐条明细）。"""
    out: list[dict] = []
    seen: set[str] = set()
    for pg in LIST_PAGES:
        if limit and len(out) >= limit:
            break
        r = fetch(BASE + pg)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表 {pg} HTTP "
                  f"{getattr(r, 'status_code', '?')}（跳过）")
            continue
        items = ITEM_RE.findall(r.text or "")
        print(f"    [{SITE['key']}] {pg}：{len(items)} 条")
        for mid, title, tail in items:
            if limit and len(out) >= limit:
                break
            if mid in seen:
                continue
            seen.add(mid)
            time.sleep(PAUSE)
            d = fetch(DETAIL_TPL.format(mid=mid), headers={"Referer": BASE + pg})
            if getattr(d, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 明细 {mid} HTTP "
                      f"{getattr(d, 'status_code', '?')}")
                continue
            f = parse_detail(d.text or "")
            answer = f.get("答复内容") or ""
            if len(answer) < 10:
                continue
            out.append({
                "source": SITE["key"],
                "id": mid,
                "url": DETAIL_TPL.format(mid=mid),
                "question": f.get("问题描述") or clean(title),
                "answer": answer,
                "asked_at": f.get("提交时间") or (SUBMIT_RE.search(tail).group(1)
                                                  if SUBMIT_RE.search(tail) else None),
                "answered_at": f.get("答复时间") or (REPLYTIME_RE.search(tail).group(1)
                                                     if REPLYTIME_RE.search(tail) else None),
                "dept": f.get("答复单位") or (DEPT_RE.search(tail).group(1)
                                             if DEPT_RE.search(tail) else None),
                "channel": "回应关切",
                "extra": {
                    "title": clean(title),
                    "platform": "德州门户 CMS",
                    "answer_kind": "部门答复（常引条例原文）",
                },
            })
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
