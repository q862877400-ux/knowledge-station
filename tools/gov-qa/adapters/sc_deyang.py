"""适配器：**德阳市·互动交流·书记/市长信箱（appeal 模块，服务端渲染 HTML）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe14~16.txt）
 · 门户 `www.deyang.gov.cn` 首页导航无「互动」，但**首页页脚/导航的 href 里藏着**
   `/appeal/list.jsp?model_id=1&tm_id=28`（**市长信箱**）、`model_id=18&tm_id=28`（**书记信箱**）。
   ⚠ 找入口别只看可见文字：德阳的互动链接只出现在 href（首页可见文本无「互动/信箱」字样）。
 · 列表是**服务端渲染 HTML**：每页 14 条，链接形如
   `<a href="/appeal/view.jsp?model_id=<m>&sq_id=<id>">标题</a>`；
   翻页参数是 **`cur_page`**（`/appeal/list.jsp?model_id=<m>&tm_id=28&cur_page=N`）。
   市长信箱 ≈58 页、书记信箱 ≈18 页（合计 ≈1050 封）。
 · 详情：`GET /appeal/view.jsp?model_id=<m>&sq_id=<id>` → HTML 表格
     `td.tdCss1`（标签）+ 相邻 `td.tdCss2/tdCss4`（值）：
     编号 / 来信人 / 来信日期 / 类型 / 来信内容 / 回复部门 / 回复时间 / 答复内容。
   ★ 答复全文在「答复内容」单元格（富文本，含 Word 粘贴样式）。
 · 样例：sq_id 122731「佛山街2段226号顺福苑…」→ 市城管执法局答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-deyang",
    "name": "德阳市·互动交流·书记市长信箱",
    "kind": "html",
    "level": "city",
    "entry": "https://www.deyang.gov.cn/appeal/list.jsp?model_id=1&tm_id=28",
    "status": "ok",
    "note": "服务端渲染 HTML：列表 /appeal/list.jsp?model_id&tm_id=28&cur_page + 详情 /appeal/view.jsp?sq_id；≈1050",
}

BASE = "https://www.deyang.gov.cn"
LIST_TPL = BASE + "/appeal/list.jsp?model_id={m}&tm_id=28&cur_page={p}"
VIEW_TPL = BASE + "/appeal/view.jsp?model_id={m}&sq_id={id}"
REFERER = SITE["entry"]
PAUSE = 1.0
# 两个信箱：(model_id, 名称)
MODELS = [("1", "市长信箱"), ("18", "书记信箱")]

_LINK_RE = re.compile(r'href=["\']/appeal/view\.jsp\?model_id=(\d+)&sq_id=(\d+)["\'][^>]*>([^<]{2,80})</a>')


def _td(html: str, label: str) -> str | None:
    m = re.search(r'<td[^>]*class="tdCss1"[^>]*>\s*' + re.escape(label)
                  + r'\s*[:：]?\s*</td>\s*<td[^>]*>(.*?)</td>', html, re.S)
    if not m:
        return None
    v = re.sub(r"(?i)<br\s*/?>", "\n", m.group(1))
    v = re.sub(r"(?i)</p>", "\n", v)
    v = re.sub(r"<[^>]+>", "", v)
    v = _html.unescape(v)
    return v.strip()


def _fetch_detail(fetch, model: str, sid: str, ref: str) -> dict | None:
    try:
        r = fetch(VIEW_TPL.format(m=model, id=sid), headers={"Referer": ref})
    except Exception as e:                                          # noqa: BLE001
        print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
        return None
    if getattr(r, "status_code", 0) != 200:
        return None
    return {"html": r.text}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 200) -> list[dict]:
    """遍历 市长/书记 两个信箱，逐页取 id → 逐条取详情解析答复。"""
    out: list[dict] = []
    seen: set[str] = set()
    for model, box in MODELS:
        for page in range(1, max_pages + 1):
            if limit and len(out) >= limit:
                return out
            url = LIST_TPL.format(m=model, p=page)
            try:
                r = fetch(url, headers={"Referer": REFERER})
            except Exception as e:                                  # noqa: BLE001
                print(f"    [{SITE['key']}] {box} 第 {page} 页：{type(e).__name__}（停）")
                break
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] {box} 第 {page} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）")
                break
            links = _LINK_RE.findall(r.text)
            new = [(m, i, t) for (m, i, t) in links if f"{m}:{i}" not in seen]
            if not new:
                break
            for m2, sid, title in new:
                if limit and len(out) >= limit:
                    return out
                seen.add(f"{m2}:{sid}")
                det = _fetch_detail(fetch, m2, sid, url)
                if not det:
                    continue
                h = det["html"]
                answer = _td(h, "答复内容") or ""
                if len(answer) < 10:            # 未答复，跳过
                    continue
                content = _td(h, "来信内容") or ""
                title = (title or "").strip()
                question = title if not content else f"{title}\n{content}"
                out.append({
                    "source": SITE["key"],
                    "id": f"{m2}-{sid}",
                    "url": VIEW_TPL.format(m=m2, id=sid),
                    "question": question,
                    "answer": answer,
                    "asked_at": _td(h, "来信日期"),
                    "answered_at": _td(h, "回复时间"),
                    "dept": _td(h, "回复部门"),
                    "channel": f"互动交流·{box}",
                    "extra": {
                        "title": title,
                        "mail_type": _td(h, "类型"),
                        "mail_no": _td(h, "编号"),
                        "model_id": m2,
                        "platform": "德阳 appeal 服务端渲染（列表+详情 HTML）",
                    },
                })
                time.sleep(PAUSE)
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
