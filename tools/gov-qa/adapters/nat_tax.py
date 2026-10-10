"""适配器：**国家税务总局·12366 纳税服务平台·网上留言**（自研接口）。

## 站点事实（2026-10-09 实测，证据 recon/nat-tax-*）
 · 入口 `https://12366.chinatax.gov.cn/nszx/onlinemessage/main`（网上留言）。
 · 列表接口（**POST，免登录**）：
   `POST https://12366.chinatax.gov.cn/nszx/onlinemessage/messagelist`
   body `currentPage=<页>&nr=&jg=&zxjg=&lykssj=`
   → JSON `{"page":1,"pageSize":8,"maxPage":4801,"maxCount":38404,
          "pageSet":[{code,id,title,content,fbsj(发布时间),unitname(所属地),...}]}`
   ⚠ 分页参数是 **`currentPage`**（不是 pageNum/page）；**`pageSize` 服务端锁死为 8**（传 20/50/100 均被忽略）。
   ⚠ 列表**不含答复**（`dfnr` 只在 JS 里对 pageSet 渲染，接口未返回）⇒ 必须逐条取明细。
 · 明细（**服务端渲染 HTML**，答复原文在此）：
   `GET https://12366.chinatax.gov.cn/nszx/onlinemessage/detail?id=<code>`
   页内 `<th>问题内容</th><td><textarea>…</textarea>`、`<th>答复内容</th><td><textarea>…</textarea>`、
   `<th>答复机构</th><td><input value="…">`、`<th>答复时间</th><td><input value="…">`、
   提问时间 `<b id="cjsj">…</b>`。
 · 实测答复点名《文件》/法条（例：《中华人民共和国契税法》主席令第五十二号）⇒ 优质考卷料。
 · 规模 **maxCount≈38404**（每页 8 ⇒ 约 4801 页）。逐条明细 ⇒ 全量极慢（>10h）。
   ⚠ 全量请先与 team-lead 报备。`limit` 用于分批/试跑。
"""
from __future__ import annotations

import os
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



def _env_page_from() -> int:
    """起始页号：环境变量 `GOVQA_PAGE_FROM`（用于把超长源分块采）。"""
    try:
        return max(1, int(os.environ.get("GOVQA_PAGE_FROM", "1")))
    except ValueError:
        return 1

SITE = {
    "key": "nat-tax",
    "name": "国家税务总局·12366网上留言",
    "kind": "api",
    "level": "national",
    "entry": "https://12366.chinatax.gov.cn/nszx/onlinemessage/main",
    "status": "ok",
    "note": "自研 POST messagelist(currentPage，pageSize锁死8，maxCount≈38404)+HTML明细 detail?id=",
}

BASE = "https://12366.chinatax.gov.cn"
LIST_API = BASE + "/nszx/onlinemessage/messagelist"
DETAIL_API = BASE + "/nszx/onlinemessage/detail"
REFERER = BASE + "/nszx/onlinemessage/main"
PAGE_SIZE = 8            # 服务端锁死，勿改
PAUSE = 1.5
#: 明细连续失败多少次就熔断（返回已收部分，避免长跑成果全丢）
MAX_CONSEC_FAIL = 8

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", re.S | re.I)
TITLE_RE = re.compile(r'<meta name="ArticleTitle" content="([^"]*)"', re.I)
Q_RE = re.compile(r"问题内容</th>\s*<td>\s*<textarea[^>]*>(.*?)</textarea>", re.S | re.I)
A_RE = re.compile(r"答复内容</th>\s*<td>\s*<textarea[^>]*>(.*?)</textarea>", re.S | re.I)
DEPT_RE = re.compile(r"答复机构</th>\s*<td>\s*<input[^>]*value=\"([^\"]*)\"", re.S | re.I)
ANS_TIME_RE = re.compile(r"答复时间</th>\s*<td>\s*<input[^>]*value=\"([^\"]*)\"", re.S | re.I)
ASK_TIME_RE = re.compile(r'<b id="cjsj">([^<]*)</b>', re.I)


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
        return m.group(1) if m else None
    return {
        "title": _text(g(TITLE_RE)),
        "question": _text(g(Q_RE)),
        "answer": _text(g(A_RE)),
        "dept": _text(g(DEPT_RE)),
        "answered_at": g(ANS_TIME_RE),
        "asked_at": g(ASK_TIME_RE),
    }


def harvest(fetch, *, limit: int | None = None,
            page_from: int | None = None) -> list[dict]:
    """翻页取列表，逐条取明细拿答复原文。`limit` 为总条数上限。

    `page_from` = 起始页号（默认读环境变量 `GOVQA_PAGE_FROM`，再默认 1）。
    ⚠ 存在的意义：`harvest.py` **只在跑完时落盘**，而本源 maxCount≈38404、pageSize 被服务端
    锁死为 8 ⇒ 全量约 16 小时，中断即零产出。分块跑法：
        GOVQA_PAGE_FROM=1    ... --limit 2000
        GOVQA_PAGE_FROM=251  ... --limit 2000     # 每页 8 条 ⇒ 2000 条 ≈ 250 页
    每块跑完即落盘，重跑按 (source, id) 天然续采。
    """
    out: list[dict] = []
    page = page_from if page_from is not None else _env_page_from()
    max_count = None
    consec_fail = 0
    while True:
        if limit and len(out) >= limit:
            break
        try:
            r = fetch.post(LIST_API,
                           data={"currentPage": page, "nr": "", "jg": "", "zxjg": "",
                                 "lykssj": ""},
                           headers={"Referer": REFERER,
                                    "X-Requested-With": "XMLHttpRequest"})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页 {type(e).__name__}"
                  f"（停，返回已收 {len(out)} 条）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP {getattr(r, 'status_code', '?')}（停）")
            break
        try:
            j = r.json()
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（{type(e).__name__}，停）")
            break
        rows = j.get("pageSet") or []
        if max_count is None:
            max_count = j.get("maxCount")
            print(f"    [{SITE['key']}] maxCount={max_count} maxPage={j.get('maxPage')}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            code = it.get("code") or it.get("id")
            if not code:
                continue
            time.sleep(PAUSE)
            # ⚠ 明细请求必须自己兜异常：实测本站在长跑中会偶发 ReadTimeout，
            #   若让异常冒泡，harvest.py 会整站丢弃、**已收的几十条/几千条全丢**
            #   （2026-10-09 踩过：跑 63 分钟后一条超时 ⇒ 零产出）。
            #   ⇒ 单条失败跳过；连续失败达阈值则熔断，**返回已收部分**。
            try:
                d = fetch(DETAIL_API, params={"id": code}, headers={"Referer": REFERER})
            except Exception as e:                                          # noqa: BLE001
                consec_fail += 1
                print(f"    [{SITE['key']}] 明细 {code} {type(e).__name__}"
                      f"（连续失败 {consec_fail}/{MAX_CONSEC_FAIL}）")
                if consec_fail >= MAX_CONSEC_FAIL:
                    safe_print(f"    [{SITE['key']}] 连续 {consec_fail} 次失败 => 熔断，"
                          f"返回已收 {len(out)} 条（下次续采）")
                    return out
                time.sleep(PAUSE * 3)
                continue
            consec_fail = 0
            if getattr(d, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 明细 {code} HTTP {d.status_code}（跳过）")
                continue
            info = _parse_detail(d.text or "")
            if len(info["answer"] or "") < 10:
                print(f"    [{SITE['key']}] {code} 未取到答复正文（跳过）")
                continue
            out.append({
                "source": SITE["key"],
                "id": str(code),
                "url": f"{DETAIL_API}?id={code}",
                "question": info["question"] or (it.get("title") or ""),
                "answer": info["answer"],
                "asked_at": info["asked_at"],
                "answered_at": info["answered_at"],
                "dept": info["dept"] or it.get("unitname"),
                "channel": "网上留言",
                "extra": {
                    "title": it.get("title"),
                    "unitname": it.get("unitname"),
                    "fbsj": it.get("fbsj"),
                    "platform": "chinatax-12366",
                },
            })
        if max_count is not None and page * PAGE_SIZE >= int(max_count):
            break
        page += 1
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
