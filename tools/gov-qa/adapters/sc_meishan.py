"""适配器：**眉山市·政民互动·来信选登（服务端渲染 HTML / WCM 西部数通站群）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe33/34/37/40/41.txt）
 · 门户 `http://www.ms.gov.cn`（WCM「西部数通」站群，`urltype=tree.TreeTempUrl&wbtreeid=` 指纹）。
 · 互动入口 `/17_hudong/hdjl_index.jsp?...wbtreeid=1010`（互动交流，诉求总数 55870）；
   其「来信选登」= `/old13/list_ldxx.jsp?...wbtreeid=5761`。
 · 列表（服务端渲染，UTF-8）：`GET /old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761`
     · 翻页 = **同一 URL 加 query `&pageNumber245916=N`**（1 基，每页 10 条）。
       ★ 页面里的 `changeleadermailpage()` 是 JS 提交表单；实测 **GET 加 pageNumber 参数即可**，
         而 POST 表单（action=list_content_ldxxnew.jsp）反而返回「暂无数据」。
     · 页脚：`共5658条  1页/566页`。
     · 行：`<A onclick="do_detail('<guid>')" title="标题"><SPAN class="titlestyle44098">标题</SPAN></A>`
           同行还有 信件类型 / 发布时间。
 · 详情：`GET /old13/list_content_ldxxnew.jsp?urltype=tree.TreeTempUrl&wbtreeid=7433&guid=<guid>`
     · 字段：标题 / 编号 / 内容分类 / 来电信时间 / 是否公开 / 回复时间 / 承办部门
     · 问题 = 「**反映诉求**」表格行内 `<span>…</span>`
     · 答复 = 「**办理结果**」表格行内 `<span>…</span>`
   ★ 页面声明 UTF-8 但响应头无 charset，requests 会误判 ISO-8859-1 ⇒ 强制 `r.content.decode("utf-8")`。
 · 样例：guid `c592f5c1-…`「关于群众反映医护人员的表扬」→ 东坡区热线/东坡区卫生健康局答复。
 · ★ **IP 频率反爬**：访问过快会被打回「用户验证」验证码页（约 120 条后触发）：
     「我们发现您所在的IP地址…访问本站过于频繁，请您输入验证码后继续访问！」
   适配器识别到即停；靠 `(source,id)` 去重可冷却后反复跑累积。
"""
from __future__ import annotations

import html as _html
import re
import time

# ⚠ 本机控制台是 GBK，日志里的 emoji/箭头（⚠ ⇒ 等）用裸 `print` 会
#   `UnicodeEncodeError` **把整个采集带崩**（实测 2026-10-10）⇒ 走 `safe_print`。
try:
    from common import safe_print
except ImportError:                                          # 适配器被单独 import 时
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
    from common import safe_print


SITE = {
    "key": "sc-meishan",
    "name": "眉山市·政民互动·来信选登",
    "kind": "html",
    "level": "city",
    "entry": "http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761",
    "status": "ok",
    "note": "服务端渲染 HTML（WCM 站群）：列表 /old13/list_ldxx.jsp?wbtreeid=5761&pageNumber245916=N（共5658条/566页）；详情 /old13/list_content_ldxxnew.jsp?wbtreeid=7433&guid=<guid>。★ 有 IP 频率反爬（约120条后打回『用户验证』验证码），去重可反复跑累积",
}

BASE = "http://www.ms.gov.cn"
LIST_TPL = BASE + "/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761&pageNumber245916={p}"
VIEW_TPL = BASE + "/old13/list_content_ldxxnew.jsp?urltype=tree.TreeTempUrl&wbtreeid=7433&guid={g}"
PAUSE = 1.0

_TAG = re.compile(r"<[^>]+>")
_GUID_RE = re.compile(r"do_detail\('([0-9a-fA-F\-]{36})'\)")
_TOTAL_RE = re.compile(r"共\s*(\d+)\s*条")
_PAGES_RE = re.compile(r"(\d+)\s*页\s*/\s*(\d+)\s*页")
_Q_RE = re.compile(r"<strong>反映诉求</strong></TD>\s*</TR>\s*<TR>\s*<TD[^>]*>(.*?)</TD>", re.S)
_A_RE = re.compile(r"<strong>办理结果</strong></TD>\s*</TR>\s*<TR>\s*<TD[^>]*>(.*?)</TD>", re.S)
#: ★ 该站有 IP 频率反爬：访问过快会被打回「用户验证」验证码页
#:   「我们发现您所在的IP地址…访问本站过于频繁，请您输入验证码后继续访问！」
#:   实测约 120 条后触发；去重可反复跑，冷却后再采即可累积。
_CAPTCHA_RE = re.compile(r"访问过于频繁|请输入验证码|用户验证|createvisitcode")


def _field(t: str, label: str) -> str:
    m = re.search(r"<strong>" + re.escape(label) + r":</strong><span[^>]*>(.*?)</span>", t, re.S)
    return _clean(m.group(1)) if m else ""


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
    try:
        return r.content.decode("utf-8")
    except Exception:                                                       # noqa: BLE001
        return r.text


def harvest(fetch, *, limit: int | None = None, max_pages: int = 600) -> list[dict]:
    """遍历 来信选登 列表翻页 → 逐条详情解析问答。"""
    out: list[dict] = []
    seen: set[str] = set()
    total_pages = None
    blocked = False
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            return out
        if total_pages is not None and page > total_pages:
            break
        try:
            r = fetch(LIST_TPL.format(p=page), headers={"Referer": SITE["entry"]})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页：{type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 HTTP {getattr(r, 'status_code', '?')}（停）")
            break
        t = _decode(r)
        if _CAPTCHA_RE.search(t):               # 触发频率验证码，立刻停
            safe_print(f"    [{SITE['key']}] [!!] 触发 IP 频率验证码（第 {page} 页），本轮停止（已采 {len(out)} 条）")
            blocked = True
            break
        if total_pages is None:
            mp = _PAGES_RE.search(t)
            if mp:
                total_pages = int(mp.group(2))
                mt = _TOTAL_RE.search(t)
                print(f"    [{SITE['key']}] 共 {mt.group(1) if mt else '?'} 条 / {total_pages} 页")
        guids = []
        for m in _GUID_RE.finditer(t):
            if m.group(1) not in guids:
                guids.append(m.group(1))
        if not guids:
            break
        new = 0
        for g in guids:
            if limit and len(out) >= limit:
                return out
            if g in seen:
                continue
            seen.add(g)
            new += 1
            try:
                vr = fetch(VIEW_TPL.format(g=g), headers={"Referer": LIST_TPL.format(p=page)})
                vh = _decode(vr)
                if _CAPTCHA_RE.search(vh):      # 详情页也被打回验证码
                    safe_print(f"    [{SITE['key']}] [!!] 触发 IP 频率验证码（详情），本轮停止（已采 {len(out)} 条）")
                    blocked = True
                    break
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {g[:8]}：{type(e).__name__}（跳过）")
                continue
            mq = _Q_RE.search(vh)
            ma = _A_RE.search(vh)
            question = _clean(mq.group(1)) if mq else ""
            answer = _clean(ma.group(1)) if ma else ""
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = _field(vh, "标题")
            if title and question and not question.startswith(title):
                question = f"{title}\n{question}"
            elif not question:
                question = title
            out.append({
                "source": SITE["key"],
                "id": g,
                "url": VIEW_TPL.format(g=g),
                "question": question,
                "answer": answer,
                "asked_at": (_field(vh, "来电/信时间") or None),
                "answered_at": (_field(vh, "回复时间") or None),
                "dept": (_field(vh, "承办部门") or None),
                "channel": "政民互动·来信选登",
                "extra": {
                    "title": title,
                    "serial": _field(vh, "编号"),
                    "type": _field(vh, "内容分类"),
                    "platform": "眉山 WCM 西部数通站群（list_ldxx + list_content_ldxxnew）",
                },
            })
            time.sleep(PAUSE)
        if blocked:
            break
        if new == 0:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
