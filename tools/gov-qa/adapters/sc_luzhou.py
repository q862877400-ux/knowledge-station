"""适配器：**泸州市·互动交流·书记市长信箱（信件公开，服务端渲染 HTML）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe1~13.txt）
 · 门户 `www.luzhou.gov.cn` → 互动交流 `/hd` → 书记市长信箱(网上信访渠道)
   `https://www.luzhou.gov.cn/LetterBox/sjszxx/List`（信件公开）。
 · 列表是**服务端渲染 HTML**（非 JSON）：每页 20 条，链接形如
   `<a href="/LetterBox/<id>">标题</a>`；翻页 `/LetterBox/sjszxx/List_2`、`List_3`（共 3 页，≈56 封）。
 · 详情：`GET https://www.luzhou.gov.cn/LetterBox/<id>` → HTML 表格
     `td.tdName`（标签）+ `td.tdCon`（值）成对出现：
     标题 / 咨询日期 / 信件状态 / 咨询内容（`<pre>` 内）/ 回复单位 / 办结日期 / 回复内容。
   ★ 答复全文在详情的「回复内容」单元格。
 · ⚠ `letterbox/query` 是「信件查询」表单页（需编号+查询码），非公开列表，不用。
 · 样例：id 15046「泸州市乒乓球裁判证考取通道」→ 市教育体育局答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-luzhou",
    "name": "泸州市·互动交流·书记市长信箱（信件公开）",
    "kind": "html",
    "level": "city",
    "entry": "https://www.luzhou.gov.cn/LetterBox/sjszxx/List",
    "status": "ok",
    "note": "服务端渲染 HTML：列表 /LetterBox/sjszxx/List_N + 详情 /LetterBox/<id>；约 3 页 56 封",
}

BASE = "https://www.luzhou.gov.cn"
LIST_TPL = BASE + "/LetterBox/sjszxx/List"
DETAIL_TPL = BASE + "/LetterBox/{id}"
REFERER = SITE["entry"]
PAUSE = 1.2

_ID_RE = re.compile(r'/LetterBox/(\d+)')
_TD_RE = None  # built per-label below


def _td(html: str, label: str) -> str | None:
    """取 `<td class="tdName">label</td><td ...>值</td>` 的值（去标签）。"""
    m = re.search(r'<td[^>]*class="tdName"[^>]*>\s*' + re.escape(label)
                  + r'\s*</td>\s*<td[^>]*>(.*?)</td>', html, re.S)
    if not m:
        return None
    v = m.group(1)
    v = re.sub(r"(?i)<br\s*/?>", "\n", v)
    v = re.sub(r"(?i)</p>", "\n", v)
    v = re.sub(r"<[^>]+>", "", v)
    v = _html.unescape(v)
    return v.strip()


def harvest(fetch, *, limit: int | None = None, max_pages: int = 100) -> list[dict]:
    """翻列表页拿 id → 逐条取详情解析答复。"""
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        url = LIST_TPL if page == 1 else f"{LIST_TPL}_{page}"
        try:
            r = fetch(url, headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        ids = [i for i in dict.fromkeys(_ID_RE.findall(r.text))]
        new_ids = [i for i in ids if i not in seen]
        if not new_ids:
            break
        for sid in new_ids:
            if limit and len(out) >= limit:
                return out
            seen.add(sid)
            try:
                dr = fetch(DETAIL_TPL.format(id=sid), headers={"Referer": url})
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                continue
            if getattr(dr, "status_code", 0) != 200:
                continue
            h = dr.text
            answer = _td(h, "回复内容") or ""
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (_td(h, "标题") or "").strip()
            content = (_td(h, "咨询内容") or "").strip()
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": DETAIL_TPL.format(id=sid),
                "question": question,
                "answer": answer,
                "asked_at": _td(h, "咨询日期"),
                "answered_at": _td(h, "办结日期"),
                "dept": _td(h, "回复单位"),
                "channel": "互动交流·书记市长信箱·信件公开",
                "extra": {
                    "title": title,
                    "state": _td(h, "信件状态"),
                    "platform": "泸州 LetterBox 服务端渲染（列表+详情 HTML）",
                },
            })
            time.sleep(PAUSE)
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
