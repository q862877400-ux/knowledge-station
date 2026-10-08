"""适配器：**巴中市·政民互动·书记/市长信箱（服务端渲染 HTML）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe24~26.txt）
 · 门户 `https://www.cnbz.gov.cn`（**页面字节是 UTF-8，但响应头无 charset，requests
   会误判 ISO-8859-1 ⇒ 必须 `r.content.decode("utf-8")`**）。
 · 互动栏目：`/zmhd/index.html` → `/zmhd/ldxx/szxx/index.html`（市长信箱）、
   `/zmhd/ldxx/sjxx/index.html`（书记信箱）。
 · 列表（服务端渲染）：`GET /content/column/<col>?pageIndex=N`（1 基，每页 16 条）
     · 市长信箱 col = `6788131`，书记信箱 col = `6788121`（来自页面内联分页脚本）
     · 分页脚本：`Ls.pagination("#page_6788131", … {currPage:1, pageCount:20})` → 各 ≈20 页。
   条目链接：`javascript:messageBoardlink('https://www.cnbz.gov.cn/content/article/<id>')`，
     同行给出 主题 / 办理单位 / 来信时间 / 办理状态。
 · 详情：`GET /content/article/<id>`，表格：
     内容：…（`<td class="nrtxt">`）= 问题
     答复情况：… 内含 `答复单位：X  答复时间：Y` 与 `<div class="dfyj">答复正文</div>`
   ★ 答复全文在 `div.dfyj`；问题在「内容：」单元格。
 · 样例：id `13450796`「巴中西站夜间乘车难」→ 市交通运输综合服务中心答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-bazhong",
    "name": "巴中市·政民互动·书记市长信箱",
    "kind": "html",
    "level": "city",
    "entry": "https://www.cnbz.gov.cn/zmhd/ldxx/szxx/index.html",
    "status": "ok",
    "note": "服务端渲染 HTML：列表 /content/column/<col>?pageIndex=N（市长6788131/书记6788121，各≈20页）+ 详情 /content/article/<id>",
}

BASE = "https://www.cnbz.gov.cn"
LIST_TPL = BASE + "/content/column/{col}?pageIndex={p}"
VIEW_TPL = BASE + "/content/article/{id}"
REFERER = SITE["entry"]
PAUSE = 1.2
COLUMNS = [("6788131", "市长信箱"), ("6788121", "书记信箱")]

_TAG = re.compile(r"<[^>]+>")
_ID_RE = re.compile(r"messageBoardlink\(\s*['\"]https://www\.cnbz\.gov\.cn/content/article/(\d+)['\"]")
_Q_RE = re.compile(r'内容：\s*</th>\s*<td[^>]*class="nrtxt"[^>]*>(.*?)</td>', re.S)
# ⚠ 答复正文内含**嵌套 <div>**（`<div class="dfyj"><p>答复意见：</p>…<big>…</big><div>…</div>…</div>`），
#   用 `(.*?)</div>` 会在第一个内层 `</div>` 处截断（实测 35% 的答复只剩「尊敬的网友：您好！」）。
#   改为匹配到单元格结束 `</td>`（答复正文里不含 </td>）。2026-10-09 修。
_A_RE = re.compile(r'<div class="dfyj">(.*?)</td>', re.S)
_DEPT_RE = re.compile(r"答复单位：\s*([^\s<&]+)")
_TIME_RE = re.compile(r"答复时间：\s*([0-9\-: ]+)")


def _clean(s) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(s))
    s = re.sub(r"(?i)</p>", "\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\u2002", " ").replace("\u2003", " ").replace("\u00a0", " ")
    return re.sub(r"[ \t]+\n", "\n", s).strip()


def _decode(r) -> str:
    """响应头无 charset，统一按 utf-8 解码（见站点事实）。"""
    try:
        return r.content.decode("utf-8")
    except Exception:                                                       # noqa: BLE001
        return r.text


def harvest(fetch, *, limit: int | None = None, max_pages: int = 60) -> list[dict]:
    """遍历 市长/书记 两栏翻页；列表 → 逐条详情解析问答。"""
    out: list[dict] = []
    seen: set[str] = set()
    for col, colname in COLUMNS:
        if limit and len(out) >= limit:
            break
        for page in range(1, max_pages + 1):
            if limit and len(out) >= limit:
                return out
            try:
                r = fetch(LIST_TPL.format(col=col, p=page), headers={"Referer": REFERER})
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] {colname} 第 {page} 页：{type(e).__name__}（停）")
                break
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] {colname} 第 {page} 页 HTTP "
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
                except Exception as e:                                      # noqa: BLE001
                    print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                    continue
                mq = _Q_RE.search(vh)
                ma = _A_RE.search(vh)
                question = _clean(mq.group(1)) if mq else ""
                answer = _clean(ma.group(1)) if ma else ""
                if answer.startswith("答复意见："):
                    answer = answer[len("答复意见："):].strip()
                if len(answer) < 10:            # 未答复，跳过
                    continue
                title = ""
                mt = re.search(r'<meta name="ArticleTitle" content="([^"]*)"', vh)
                if mt:
                    title = _html.unescape(mt.group(1)).strip()
                if title and question and not question.startswith(title):
                    question = f"{title}\n{question}"
                elif not question:
                    question = title
                md = _DEPT_RE.search(vh)
                mtm = _TIME_RE.search(vh)
                out.append({
                    "source": SITE["key"],
                    "id": sid,
                    "url": VIEW_TPL.format(id=sid),
                    "question": question,
                    "answer": answer,
                    "asked_at": None,
                    "answered_at": (mtm.group(1).strip() if mtm else None),
                    "dept": (md.group(1).strip() if md else None),
                    "channel": f"政民互动·{colname}",
                    "extra": {
                        "title": title,
                        "column": colname,
                        "platform": "巴中 服务端渲染 HTML（content/column + content/article）",
                    },
                })
                time.sleep(PAUSE)
            if new == 0:
                break
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
