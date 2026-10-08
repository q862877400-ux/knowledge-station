"""适配器：**宜宾市·12345 市民服务平台·办件摘编（服务端渲染 HTML）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe27/28.txt）
 · 平台独立域：`http://12345.zwfwhfgjjfzj.yibin.gov.cn`（宜宾 12345 市民服务平台，
   非门户 `www.yibin.gov.cn`；门户的 `/hdjl/szywm/lxxd/` 无公开列表）。
 · 列表：`GET /DoExcerpts/List/?PageNum=N`（1 基，每页 10 条，服务端渲染）。
   分页控件 `#hidPageCount`（实测 233 页 ⇒ ≈2330 条）。
   条目：`<tr class="table_trcss" dataid="<base64 id>"><td>标题</td><td>日期</td></tr>`。
 · 详情：`GET /DoExcerpts/Detail/<dataid>`（服务端渲染），表格 `#detailinfo`：
     受理标题 / 来源方式 / 办理情况 / 来信时间 / 办理单位 / 办结时间
     信件内容（`<td id="Content">`）= 问题
     处理结果（`<td id="EndUp">`）= 答复全文
 · 样例：dataid `MDhkZjFiYzQtNDExMi00ODFlLTg0YTItOWUzMGJjMGViODEz`
   「咨询公积金装修提取条件」→ 热线中心答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-yibin",
    "name": "宜宾市·12345 市民服务平台·办件摘编",
    "kind": "html",
    "level": "city",
    "entry": "http://12345.zwfwhfgjjfzj.yibin.gov.cn/DoExcerpts/List/",
    "status": "ok",
    "note": "服务端渲染 HTML：列表 /DoExcerpts/List/?PageNum=N（每页10，≈233页）+ 详情 /DoExcerpts/Detail/<dataid>",
}

BASE = "http://12345.zwfwhfgjjfzj.yibin.gov.cn"
LIST_TPL = BASE + "/DoExcerpts/List/?PageNum={p}"
VIEW_TPL = BASE + "/DoExcerpts/Detail/{id}"
REFERER = SITE["entry"]
PAUSE = 1.0

_TAG = re.compile(r"<[^>]+>")
_ROW_RE = re.compile(r'dataid="([^"]+)"\s*>\s*<td>(.*?)</td>\s*<td>(.*?)</td>', re.S)
_CONTENT_RE = re.compile(r'id="Content"[^>]*>(.*?)</td>', re.S)
_ANSWER_RE = re.compile(r'id="EndUp"[^>]*>(.*?)</td>', re.S)
_PAGECOUNT_RE = re.compile(r'id="hidPageCount"[^>]*value="(\d+)"')


def _clean(s) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(s))
    s = re.sub(r"(?i)</p>", "\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\u00a0", " ").replace("\u2002", " ").replace("\u2003", " ")
    return re.sub(r"[ \t]+\n", "\n", s).strip()


def _cell(t: str, label: str) -> str:
    m = re.search(r"<td[^>]*>\s*" + re.escape(label) + r"\s*</td>\s*<td[^>]*>(.*?)</td>", t, re.S)
    return _clean(m.group(1)) if m else ""


def harvest(fetch, *, limit: int | None = None, max_pages: int = 400) -> list[dict]:
    """翻页取宜宾 12345 办件摘编；列表 → 逐条详情解析问答。"""
    out: list[dict] = []
    seen: set[str] = set()
    pagecount = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_TPL.format(p=page), headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        t = r.text
        if pagecount is None:
            mc = _PAGECOUNT_RE.search(t)
            pagecount = int(mc.group(1)) if mc else None
            print(f"    [{SITE['key']}] 总页数 pageCount={pagecount}")
        rows = _ROW_RE.findall(t)
        if not rows:
            break
        new = 0
        for sid, title, _date in rows:
            if limit and len(out) >= limit:
                return out
            if sid in seen:
                continue
            seen.add(sid)
            new += 1
            try:
                vr = fetch(VIEW_TPL.format(id=sid), headers={"Referer": REFERER})
                vh = vr.text
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                continue
            mq = _CONTENT_RE.search(vh)
            ma = _ANSWER_RE.search(vh)
            question = _clean(mq.group(1)) if mq else ""
            answer = _clean(ma.group(1)) if ma else ""
            if len(answer) < 10:            # 未答复，跳过
                continue
            ttl = _cell(vh, "受理标题") or _clean(title)
            if ttl and question and not question.startswith(ttl):
                question = f"{ttl}\n{question}"
            elif not question:
                question = ttl
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": VIEW_TPL.format(id=sid),
                "question": question,
                "answer": answer,
                "asked_at": _cell(vh, "来信时间") or None,
                "answered_at": _cell(vh, "办结时间") or None,
                "dept": _cell(vh, "办理单位") or None,
                "channel": "12345 市民服务平台·办件摘编",
                "extra": {
                    "title": ttl,
                    "source_way": _cell(vh, "来源方式"),
                    "status": _cell(vh, "办理情况"),
                    "platform": "宜宾 12345 服务端渲染 HTML（DoExcerpts）",
                },
            })
            time.sleep(PAUSE)
        if new == 0:
            break
        if pagecount and page >= pagecount:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
