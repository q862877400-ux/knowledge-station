"""适配器：**雅安市·政民互动·党政领导信箱（服务端渲染 HTML）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe31/32.txt）
 · 门户 `https://www.yaan.gov.cn`，互动入口 `/mail/index.html`（信箱中心）。
 · **入口页给出 34 个「部门/领导」信箱的 uuid**：
     `href="/mail/mailbox.html?id=<uuid>"`（书记信箱、市长信箱、各局信箱…）。
 · 列表（服务端渲染，UTF-8）：
     `GET /mail/mailbox.html?id=<uuid>&page=N`（1 基，每页 15 条）
     页脚给出总页数：`共 50 页`（书记信箱实测 50 页）。
     行内列：编号 / 信件标题 / 目的 / 写信日期 / 回复日期；
     详情链接：`/mail/view.html?id=<uuid>&mailid=<32位md5>`。
 · 详情（服务端渲染，UTF-8）：表格字段
     信件编号 / 信件状态 / 写信时间 / 信件标题 / 信件内容 / 办理情况
     · 问题 = `<td class="td01">信件内容</td><td class="td02"><div class="text">…</div>`
     · 答复 = `<td class="td01">办理情况</td><td class="td02"><div class="reply"><ul>
                 <li><div class="replycontent">答复正文</div>
                     <p class="replydesc">答复单位 &nbsp; 时间</p></li>…`
       ★ 一个信件可有多个 li（先「请X处复」流转说明，再具体答复）；
         答复正文 = 全部 `div.replycontent` 逐字拼接（**原文不改写**）。
   ★ 页面声明 UTF-8 但响应头无 charset，requests 会误判 ISO-8859-1 ⇒
     必须 `r.content.decode("utf-8")`。
 · 样例：uuid `ca423879-…`（书记信箱）/ mailid `d42c4e11…` →
     「关于咨询雅安生物多样性公园内设置收费娱乐项目相关事项」，雅投公司答复。
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
    "key": "sc-yaan",
    "name": "雅安市·政民互动·党政领导信箱",
    "kind": "html",
    "level": "city",
    "entry": "https://www.yaan.gov.cn/mail/index.html",
    "status": "ok",
    "note": "服务端渲染 HTML：/mail/index.html 给 34 个部门 uuid；列表 /mail/mailbox.html?id=<uuid>(第1页)/&page=N（共50页/15条）；详情 /mail/view.html?id=<uuid>&mailid=<md5>。★ 该站有 IP 级反爬，快抓会返回『你的请求被拦截』空页 ⇒ 慢速 + 拦截即停",
}

BASE = "https://www.yaan.gov.cn"
INDEX_URL = BASE + "/mail/index.html"
# ★ 第 1 页用**无 page 参数**的 URL（站内「首页」就是这么链的；显式 page=1 会返回空/拦截页）。
LIST_TPL = BASE + "/mail/mailbox.html?id={uid}&page={p}"
LIST_P1_TPL = BASE + "/mail/mailbox.html?id={uid}"
VIEW_TPL = BASE + "/mail/view.html?id={uid}&mailid={mid}"
PAUSE = 2.5                       # ★ 该站有 **IP 级反爬**，节奏必须放慢

_TAG = re.compile(r"<[^>]+>")
_UUID_RE = re.compile(r"mailbox\.html\?id=([0-9a-fA-F\-]{36})")
_DETAIL_RE = re.compile(
    r"view\.html\?id=([0-9a-fA-F\-]{36})&(?:amp;)?mailid=([0-9a-fA-F]{16,64})")
_PAGECOUNT_RE = re.compile(r"共\s*(\d+)\s*页")
#: 反爬拦截页：「系统检测到您的ip存在恶意请求，已对您的ip进行拦截，请稍后再试。」
_BLOCK_RE = re.compile(r"被拦截|恶意请求")
_TITLE_RE = re.compile(r'<div class="h1">(.*?)</div>', re.S)
_Q_RE = re.compile(
    r'信件内容</td>\s*<td class="td02">\s*<div class="text">(.*?)</div>', re.S)
_A_RE = re.compile(r'办理情况</td>\s*<td class="td02">(.*?)</td>\s*</tr>', re.S)
_REPLYCONTENT_RE = re.compile(r'<div class="replycontent">(.*?)</div>', re.S)
_REPLYDESC_RE = re.compile(r'class="replydesc">(.*?)</p>', re.S)
_DESC_TIME_RE = re.compile(r"^(.*?)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*$")


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


def _cell(t: str, label: str) -> str:
    m = re.search(re.escape(label) + r"</td>\s*<td[^>]*>(.*?)</td>", t, re.S)
    return _clean(m.group(1)) if m else ""


def _uuids(fetch) -> list[str]:
    try:
        r = fetch(INDEX_URL, headers={"Referer": BASE + "/"})
    except Exception as e:                                                  # noqa: BLE001
        print(f"    [{SITE['key']}] 入口页异常：{type(e).__name__}")
        return []
    if getattr(r, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] 入口页 HTTP {getattr(r, 'status_code', '?')}")
        return []
    out: list[str] = []
    for m in _UUID_RE.finditer(_decode(r)):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def harvest(fetch, *, limit: int | None = None, max_pages: int = 60) -> list[dict]:
    """遍历全部部门信箱 → 翻页取列表 → 逐条详情解析问答。"""
    out: list[dict] = []
    seen: set[str] = set()
    uuids = _uuids(fetch)
    print(f"    [{SITE['key']}] 部门信箱 {len(uuids)} 个")
    for uid in uuids:
        if limit and len(out) >= limit:
            break
        total_pages = None
        blocked = False
        for page in range(1, max_pages + 1):
            if limit and len(out) >= limit:
                return out
            if total_pages is not None and page > total_pages:
                break
            list_url = (LIST_P1_TPL.format(uid=uid) if page == 1
                        else LIST_TPL.format(uid=uid, p=page))
            try:
                r = fetch(list_url, headers={"Referer": INDEX_URL})
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] {uid[:8]} 第 {page} 页：{type(e).__name__}（停）")
                break
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] {uid[:8]} 第 {page} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）")
                break
            t = _decode(r)
            if _BLOCK_RE.search(t):                 # 反爬拦截，立刻停（别再加剧）
                safe_print(f"    [{SITE['key']}] [!!] 触发 IP 反爬拦截（第 {page} 页），本轮停止")
                blocked = True
                break
            if total_pages is None:
                mp = _PAGECOUNT_RE.search(t)
                if mp:
                    total_pages = int(mp.group(1))
            rows = []
            for m in _DETAIL_RE.finditer(t):
                key = (m.group(1), m.group(2))
                if key not in rows:
                    rows.append(key)
            if not rows:
                break
            new = 0
            for duid, mid in rows:
                if limit and len(out) >= limit:
                    return out
                if mid in seen:
                    continue
                seen.add(mid)
                new += 1
                try:
                    vr = fetch(VIEW_TPL.format(uid=duid, mid=mid),
                               headers={"Referer": list_url})
                    vh = _decode(vr)
                    if _BLOCK_RE.search(vh):        # 详情页也被拦，停
                        safe_print(f"    [{SITE['key']}] [!!] 触发 IP 反爬拦截（详情），本轮停止")
                        blocked = True
                        break
                except Exception as e:                                      # noqa: BLE001
                    print(f"    [{SITE['key']}] 详情 {mid[:10]}：{type(e).__name__}（跳过）")
                    continue
                mq = _Q_RE.search(vh)
                ma = _A_RE.search(vh)
                question = _clean(mq.group(1)) if mq else ""
                answer = ""
                dept = None
                answered_at = None
                if ma:
                    blocks = [_clean(x) for x in _REPLYCONTENT_RE.findall(ma.group(1))]
                    answer = "\n".join(b for b in blocks if b)
                    descs = [_clean(x) for x in _REPLYDESC_RE.findall(ma.group(1))]
                    if descs:
                        dm = _DESC_TIME_RE.match(descs[-1])
                        if dm:
                            dept = dm.group(1).strip() or None
                            answered_at = dm.group(2).strip()
                        else:
                            dept = descs[-1] or None
                if len(answer) < 10:            # 未答复/无实质答复，跳过
                    continue
                title = _clean(_TITLE_RE.search(vh).group(1)) if _TITLE_RE.search(vh) else ""
                if title and question and not question.startswith(title):
                    question = f"{title}\n{question}"
                elif not question:
                    question = title
                serial = _cell(vh, "信件编号")
                asked = _cell(vh, "写信时间")
                out.append({
                    "source": SITE["key"],
                    "id": mid,
                    "url": VIEW_TPL.format(uid=duid, mid=mid),
                    "question": question,
                    "answer": answer,
                    "asked_at": (asked or None),
                    "answered_at": answered_at,
                    "dept": dept,
                    "channel": "政民互动·党政领导信箱",
                    "extra": {
                        "title": title,
                        "serial": serial,
                        "dept_uuid": duid,
                        "platform": "雅安 服务端渲染 HTML（mail/mailbox + mail/view）",
                    },
                })
                time.sleep(PAUSE)
            if blocked:
                break
            if new == 0:
                break
            time.sleep(PAUSE)
        if blocked:
            break
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
