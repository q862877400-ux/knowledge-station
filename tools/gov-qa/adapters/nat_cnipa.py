"""适配器：**国家知识产权局·留言咨询（已答问题）**（jact 平台，多 sysid）。

## 站点事实（2026-10-09 实测，证据 recon/nat-cnipa-*）
 · 入口 `https://www.cnipa.gov.cn/col/col79/index.html`（互动 → 留言咨询）→ 各业务咨询系统
   `https://www.cnipa.gov.cn/jact/front/main.do?sysid=<N>`，页面「已答问题」tab 即公开问答列表。
 · 列表（**POST，免登录**，jact 平台）：
   `POST https://www.cnipa.gov.cn/jact/front/dataproxy_mailpublist.do
        ?sysid=<N>&startrecord=<起>&endrecord=<止>&perpage=<每页>`
   → 纯文本 `totalRecord=76302.0;totalPage=7631;dataStore = ["<tr>…transactId=541983&sysid=13…>标题</a>…</tr>", …]`
   ⚠ **分页参数在 query string**（`startrecord/endrecord/perpage`），不是 body。
 · 明细（**GET，服务端渲染 HTML**，答复原文在此）：
   `GET https://www.cnipa.gov.cn/jact/front/mailpubdetail.do?transactId=<id>&sysid=<N>`
   页内 `<title>标题</title>`、`问题内容</td><td…>…`、`答复内容</td><td…>…`、
   `答复机构`、`答复时间`、`提交时间`。
 · 实测 sysid 与规模（2026-10-09，recon/nat-cnipa-sysid-hunt.txt）：
   | sysid | 栏目 | totalRecord |
   |---|---|---|
   | 6 | 专利申请流程咨询（专利咨询） | **137327** |
   | 11 | （待定，14369） | **14369** |
   | 12 | 专利文献咨询 | **464** |
   | 13 | 商标注册业务咨询 | **76302** |
   | 14 | 商标评审业务咨询 | **16611** |
   | 16 | 专利复审无效咨询 | **5947** |
   合计约 **25.1 万条**（枚举 1..60 已覆盖，25..60 全空）。
 · 实测答复常点名《文件》（例：《关键数字技术专利分类体系（2023）》）⇒ 优质考卷料。
 · ⚠ 规模极大（25 万）× 逐条明细 ⇒ **全量不现实**（>100h）。务必用 `limit` 分批。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "nat-cnipa",
    "name": "国家知识产权局·留言咨询",
    "kind": "api",
    "level": "national",
    "entry": "https://www.cnipa.gov.cn/col/col79/index.html",
    "status": "ok",
    "note": "jact 平台 dataproxy_mailpublist.do(POST,分页在query)+mailpubdetail.do；6 sysid 合计≈25.1万条",
}

BASE = "https://www.cnipa.gov.cn/jact/front"
LIST_API = BASE + "/dataproxy_mailpublist.do"
DETAIL_API = BASE + "/mailpubdetail.do"
PAGE_SIZE = 20
PAUSE = 1.2

#: (sysid, 栏目名)
SYSIDS = [
    ("6", "专利申请流程咨询"),
    ("11", "专利咨询(11)"),
    ("12", "专利文献咨询"),
    ("13", "商标注册业务咨询"),
    ("14", "商标评审业务咨询"),
    ("16", "专利复审无效咨询"),
]

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", re.S | re.I)
TOTAL_RE = re.compile(r"totalRecord=([0-9.]+)")
ROW_RE = re.compile(r"transactId=(\d+)&sysid=\d+'[^>]*>([^<]+)</a>")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
#: 各字段：`<td>标签</td> <td …>内容</td>`。⚠ 标签本身**有的包在 `<a>` 里（如「问题内容」）、
#: 有的不包（如「答复内容」）** ⇒ `</a>` 必须可选，否则抽不到答复正文（踩过）。
def _field_re(label: str) -> re.Pattern:
    return re.compile(label + r"\s*(?:</a>)?\s*</td>\s*<td[^>]*>(.*?)</td>", re.S | re.I)


Q_RE = _field_re("问题内容")
A_RE = _field_re("答复内容")
DEPT_RE = _field_re("答复机构")
ANS_T_RE = _field_re("答复时间")
ASK_T_RE = _field_re("提交时间")


def _text(html: str | None) -> str:
    if not html:
        return ""
    t = SCRIPT_RE.sub(" ", html)
    t = TAG_RE.sub(" ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", t).strip()


def _parse_detail(html: str) -> dict:
    def g(pat):
        m = pat.search(html)
        return _text(m.group(1)) if m else ""
    mt = TITLE_RE.search(html)
    return {
        "title": _text(mt.group(1)) if mt else "",
        "question": g(Q_RE),
        "answer": g(A_RE),
        "dept": g(DEPT_RE),
        "answered_at": g(ANS_T_RE),
        "asked_at": g(ASK_T_RE),
    }


def _list_page(fetch, sysid: str, page: int, per_page: int) -> tuple[list[tuple[str, str]], int | None]:
    start = (page - 1) * per_page
    r = fetch.post(LIST_API,
                   params={"sysid": sysid, "startrecord": start,
                           "endrecord": start + per_page, "perpage": per_page},
                   headers={"Referer": f"https://www.cnipa.gov.cn/jact/front/main.do?sysid={sysid}",
                            "X-Requested-With": "XMLHttpRequest"})
    if getattr(r, "status_code", 0) != 200:
        raise RuntimeError(f"HTTP {getattr(r, 'status_code', '?')}")
    body = r.text or ""
    mt = TOTAL_RE.search(body)
    total = int(float(mt.group(1))) if mt else None
    rows = ROW_RE.findall(body)
    return rows, total


def harvest(fetch, *, limit: int | None = None, page_size: int = PAGE_SIZE,
            sysids=None) -> list[dict]:
    """遍历各 sysid 的「已答问题」，逐条取明细拿答复原文。`limit` 为总条数上限。"""
    out: list[dict] = []
    for sid, name in (sysids or SYSIDS):
        if limit and len(out) >= limit:
            break
        page = 1
        total = None
        while True:
            if limit and len(out) >= limit:
                return out[:limit]
            try:
                rows, total = _list_page(fetch, sid, page, page_size)
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] {name}(sysid={sid}) 第 {page} 页失败 "
                      f"{type(e).__name__}: {e}（停）")
                break
            if page == 1:
                print(f"    [{SITE['key']}] {name}(sysid={sid}) totalRecord={total}")
            if not rows:
                break
            for tid, title in rows:
                if limit and len(out) >= limit:
                    return out[:limit]
                time.sleep(PAUSE)
                d = fetch(DETAIL_API, params={"transactId": tid, "sysid": sid},
                          headers={"Referer": f"https://www.cnipa.gov.cn/jact/front/main.do?sysid={sid}"})
                if getattr(d, "status_code", 0) != 200:
                    print(f"    [{SITE['key']}] 明细 {tid} HTTP {d.status_code}（跳过）")
                    continue
                info = _parse_detail(d.text or "")
                if len(info["answer"] or "") < 10:
                    print(f"    [{SITE['key']}] {tid} 未取到答复正文（跳过）")
                    continue
                out.append({
                    "source": SITE["key"],
                    "id": f"{sid}-{tid}",
                    "url": f"{DETAIL_API}?transactId={tid}&sysid={sid}",
                    "question": info["question"] or _text(title),
                    "answer": info["answer"],
                    "asked_at": info["asked_at"],
                    "answered_at": info["answered_at"],
                    "dept": info["dept"],
                    "channel": name,
                    "extra": {"sysid": sid, "title": info["title"] or _text(title),
                              "platform": "cnipa-jact"},
                })
            if total is not None and page * page_size >= total:
                break
            page += 1
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
