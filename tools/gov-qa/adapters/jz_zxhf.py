"""适配器：**焦作市·咨询回复**（`/zmhd/zxhf/`，政民互动咨询选登）。

## 站点事实（2026-10-10 实测）

- 列表 `https://www.jiaozuo.gov.cn/zmhd/zxhf/` **服务端渲染**，
  每页 `<a href="https://www.jiaozuo.gov.cn/YYYY/MM-DD/<id>.html">标题</a>`
- **分页**：`index.html` → `index_1.html` → `index_2.html` …
  （从 `paging.js` 的 `goto` 抄到的：`returnp = page==0 ? '' : '_'+page`，
  即**页号从 0 起**、文件名是 `index_<page-1>.html`）
- ⚠ 页面里 `<div id="pageDec" pagesize="24" pagecount="34">` 的 `pagecount=34`
  **是"总条数"不是"总页数"**（JS 里 `pages = ceil(pagecount/pagesize)`）。
  **实测**：`index_0` 24 条 + `index_1` 10 条 = **34 条**，`index_2` 空 ⇒ **2 页**。
- 详情 `https://www.jiaozuo.gov.cn/YYYY/MM-DD/<id>.html` **服务端渲染**，
  含「详细信息」（标题 / 提交日期 / 来源）与「受理回复」（回复日期 / 回复单位 / 回复内容）

## 质量（铁律第 6 条）

抽 3 条详情，**答复非空**，且带具体依据/电话：
「依据焦作市相关文件规定，新参保人员应连续参保交费 6 个月以上…拨打 **0391-8826930**」

## ⚠ 一个被否掉的入口（记下来省得重试）

首页也暴露了 `https://t.jiaozuo.gov.cn/consultview/api/view/selectsiteconsult`
—— 实测是**登录页**（要账号验证码）⇒ **不可采**。
（与安阳 `letter.anyang.gov.cn/api/view/welcome` **同形** ——
河南省政府网站统一技术平台的登录页。**看到 `api` 不能就以为能采。**）
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "jz-zxhf",
    "name": "焦作市·政民互动·咨询回复",
    "kind": "static",
    "level": "city",
    "region": "焦作市",
    "entry": "https://www.jiaozuo.gov.cn/zmhd/zxhf/",
    "status": "ok",
    "note": "服务端渲染 index.html/index_N.html（页号从 0 起）；详情 /YYYY/MM-DD/<id>.html；"
            "实测 34 条（2 页），抽 3 条答复非空",
}

BASE = "https://www.jiaozuo.gov.cn/zmhd/zxhf"
LIST_TPL = BASE + "/index{page}.html"      # page = "" 或 "_1" / "_2" …
PAUSE = 0.8
MAX_PAGES = 40

_TAG = re.compile(r"</?[A-Za-z][^>]*>")
_BR = re.compile(r"(?i)<br\s*/?>")
_WS = re.compile(r"[ \t\r\f\v]+")


def _clean(s) -> str:
    if not s:
        return ""
    s = _BR.sub("\n", str(s))
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\xa0", " ")
    s = _WS.sub(" ", s)
    return re.sub(r"\n{2,}", "\n", s).strip()


def _real(v) -> str:
    s = _clean(v)
    return "" if s.strip().lower() in ("null", "none", "undefined") else s


def _parse_list(html: str) -> list:
    """列表页 → `[{id, title, url}]`（去重、保序）。"""
    out = []
    seen = set()
    for href, title in re.findall(
            r'<a[^>]+href="(https://www\.jiaozuo\.gov\.cn/\d{4}/[^"]+\.html)"[^>]*>([^<]{2,120})</a>',
            html):
        mid = href.rsplit("/", 1)[-1].removesuffix(".html")
        if mid in seen:
            continue
        seen.add(mid)
        t = _real(title)
        if not t or len(t) < 4:
            continue
        out.append({"id": mid, "title": t, "url": href})
    return out


def _parse_detail(html: str) -> dict:
    """详情页 → `{question, answer, asked_at, answered_at, dept}`。

    页面结构（实测）：
        详细信息 / 标题 … / 提交日期 … / 内容 <问题正文>
        受理回复 / 回复日期 … / 回复单位 … / 回复内容 <答复正文>
    """
    out = {"question": "", "answer": "", "asked_at": None,
           "answered_at": None, "dept": None}
    txt = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    # 标题
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    if m:
        out["title"] = _real(m.group(1))
    # 提交日期
    m = re.search(r"提交日期[：: ]*</?[^>]*>?\s*(\d{4}-\d{2}-\d{2})", txt)
    if not m:
        m = re.search(r"提交日期[：: ]{0,4}(\d{4}-\d{2}-\d{2})", txt)
    out["asked_at"] = m.group(1) if m else None
    # 回复日期
    m = re.search(r"回复日期[：: ]{0,4}(\d{4}-\d{2}-\d{2})", txt)
    out["answered_at"] = m.group(1) if m else None
    # 回复单位
    m = re.search(r"回复单位[：: ]{0,4}([^\s<]{2,40})", txt)
    out["dept"] = _real(m.group(1)) if m else None
    # 内容（问题）
    m = re.search(r"[内内]容[：: ]{0,4}(.{10,4000}?)(?:受理回复|回复日期|回复单位)", txt, re.S)
    if m:
        out["question"] = _real(m.group(1))
    # 回复内容（答复）
    m = re.search(r"回复内容[：: ]{0,4}(.{10,8000}?)(?:相关阅读|关闭当前页面|扫一扫|$)", txt, re.S)
    if m:
        out["answer"] = _real(m.group(1))
    return out


def harvest(fetch, *, limit: int | None = None, max_pages: int = MAX_PAGES) -> list[dict]:
    """翻列表（服务端渲染）+ 逐条取详情。

    ⚠⚠ **逐条取详情必须打进度点** —— 本模块为此踩过 5 次坑
    （列表有日志、明细静默 ⇒ 被误判成"站点节流"）。
    """
    out: list[dict] = []
    seen: set[str] = set()
    n_detail = n_fail = 0
    for n in range(0, max_pages):
        if limit and len(out) >= limit:
            break
        suffix = "" if n == 0 else f"_{n}"
        url = LIST_TPL.format(page=suffix)
        try:
            r = fetch(url)
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {n} 页失败 {type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {n} 页 HTTP "
                  f"{getattr(r,'status_code','?')}（停）")
            break
        items = _parse_list(r.text)
        print(f"    [{SITE['key']}] 列表第 {n} 页：{len(items)} 条", flush=True)
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
                "dept": det.get("dept"),
                "channel": "咨询回复",
                "extra": {
                    "title": det.get("title") or it["title"],
                    "platform": "焦作市政府门户（服务端渲染咨询回复）",
                },
            })
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条；明细取 {n_detail} 条，其中无答复 {n_fail} 条")
    return out
