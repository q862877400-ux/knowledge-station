"""适配器：**乐山市·政民互动·信件选登（服务端渲染 HTML）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe29/30.txt）
 · 互动栏目：`/lsswszf/zmhd/index.html`（政民互动）→ **`/lsswszf/xlxxx/index.html`（信件选登）**。
 · 列表（服务端渲染）：`GET /lsswszf/xlxxx/index.html`、`index_2.html` … `index_N.html`
   （每页 15 条；实测 index_30 通、index_40 404 ⇒ ≈39 页 ≈585 条）。
   条目链接：`/lsswszf/xlxxx/<id>.html`。
 · 详情（服务端渲染，**UTF-8**）：`GET /lsswszf/xlxxx/<id>.html`
     `<div class="ldxx-box">` 信件信息表：信件标题 / 信件编号 / 信访形式(地区) / 写信时间 /
       内容分类 / 回复时间
     `信件内容：</th></tr></table>` 后紧跟的 `<div class="ldxx-content">` = 问题
     `信件回复内容` 标题后的 `<div class="ldxx-content">` = 答复全文
 · 样例：id `854517350903898`「天府通办无犯罪记录证明开具问题」→ 井研县公安局答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-leshan",
    "name": "乐山市·政民互动·信件选登",
    "kind": "html",
    "level": "city",
    "entry": "https://www.leshan.gov.cn/lsswszf/xlxxx/index.html",
    "status": "ok",
    "note": "服务端渲染 HTML：列表 /lsswszf/xlxxx/index[_N].html（每页15，≈39页）+ 详情 /lsswszf/xlxxx/<id>.html",
}

BASE = "https://www.leshan.gov.cn"
LIST_TPL = BASE + "/lsswszf/xlxxx/index.html"
LIST_N_TPL = BASE + "/lsswszf/xlxxx/index_{n}.html"
VIEW_TPL = BASE + "/lsswszf/xlxxx/{id}.html"
REFERER = SITE["entry"]
PAUSE = 1.2

_TAG = re.compile(r"<[^>]+>")
_ID_RE = re.compile(r"/lsswszf/xlxxx/(\d+)\.html")
_Q_RE = re.compile(r'信件内容：\s*</th>\s*</tr>\s*</table>\s*<div class="ldxx-content">(.*?)</div>', re.S)
_A_RE = re.compile(r'信件回复内容\s*</div>\s*<div class="ldxx-content">(.*?)</div>', re.S)


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
    m = re.search(r"<th>\s*" + re.escape(label) + r"\s*</th>\s*<td>(.*?)</td>", t, re.S)
    return _clean(m.group(1)) if m else ""


def _decode(r) -> str:
    try:
        return r.content.decode("utf-8")
    except Exception:                                                       # noqa: BLE001
        return r.text


def harvest(fetch, *, limit: int | None = None, max_pages: int = 80) -> list[dict]:
    """翻页取乐山信件选登；列表 → 逐条详情解析问答。"""
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        url = LIST_TPL if page == 1 else LIST_N_TPL.format(n=page)
        try:
            r = fetch(url, headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        ids = []
        for m in _ID_RE.finditer(_decode(r)):
            if m.group(1) not in ids:
                ids.append(m.group(1))
        if not ids:
            break
        new = 0
        for sid in ids:
            if limit and len(out) >= limit:
                return out
            if sid in seen:
                continue
            seen.add(sid)
            new += 1
            try:
                vr = fetch(VIEW_TPL.format(id=sid), headers={"Referer": REFERER})
                vh = _decode(vr)
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                continue
            mq = _Q_RE.search(vh)
            ma = _A_RE.search(vh)
            question = _clean(mq.group(1)) if mq else ""
            answer = _clean(ma.group(1)) if ma else ""
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = _cell(vh, "信件标题：")
            if title and question and not question.startswith(title):
                question = f"{title}\n{question}"
            elif not question:
                question = title
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": VIEW_TPL.format(id=sid),
                "question": question,
                "answer": answer,
                "asked_at": _cell(vh, "写信时间：") or None,
                "answered_at": _cell(vh, "回复时间：") or None,
                "dept": None,
                "channel": "政民互动·信件选登",
                "extra": {
                    "title": title,
                    "serial_number": _cell(vh, "信件编号："),
                    "area": _cell(vh, "信访形式："),
                    "category": _cell(vh, "内容分类："),
                    "platform": "乐山 服务端渲染 HTML（lsswszf/xlxxx）",
                },
            })
            time.sleep(PAUSE)
        if new == 0:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
