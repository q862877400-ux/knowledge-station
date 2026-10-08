"""适配器：**北京市·政民互动·信件选登**（首都之窗门户信件库，Struts2）。

## 站点事实（2026-10-08 实测，证据 `recon/bj-nmg-hunt.txt`）
 · 门户 `www.beijing.gov.cn` 的「政民互动」→「信件选登」
   `/hudong/hdjl/sindex/hdjl-xjxd.html`。
 · 列表（**POST**，实测 200）：
   `.../hudong/hdjl/sindex/bjah-index-hdjl!letterListJson.action`
   `?keyword=&letterType=&page.pageNo=N&page.pageSize=100&orgtitleLength=26`
   ⚠ 返回的是 **JS 对象字面量**（键无引号、值单引号），**不是严格 JSON**
   —— 直接 `r.json()` 会 `JSONDecodeError`；须先转 JSON（见 `_parse_js_obj`）。
   `page.totalCount=215`（pageSize=100 → 3 页）。字段：
   `originalId / letterTypeName / letterTitle / writeDate / replyDate / orgNames`。
 · 明细（**GET**，实测 200，HTML）：
   `/hudong/hdjl/com.web.consult.consultDetail.flow?originalId=<id>`
   用 HTML 注释 `<!--问开始-->`/`<!--问结束-->`/`<!--答开始-->`/`<!--答结束-->` 分区；
   正文在 class 含 `text-format` 的 div 里；答复单位在「答」块的 `<strong>`。
 · 答复**常点名条例条款**（样例：员工休育儿假 → 市卫生健康委答
   《北京市人口与计划生育条例》第四章 第十九条）。
 · ⚠ **无省市县三级归属字段**（`orgNames` 是答复单位、非地区）⇒ 归省靠
   `recon/coverage-matrix.py` 的 `PROVINCE_PREFIX`（**需补 `bj-` → 北京市**）。
"""
from __future__ import annotations

import html as _html
import json
import re
import time

SITE = {
    "key": "bj-hdjl",
    "name": "北京市·政民互动·信件选登",
    "kind": "api",
    "level": "province",
    "entry": "https://www.beijing.gov.cn/hudong/hdjl/sindex/hdjl-xjxd.html",
    "status": "ok",
    "note": "首都之窗门户信件库；列表 POST .action（返回 JS 对象字面量、非 JSON），"
            "明细 GET .flow（HTML）；答复常点名条例条款；无三级归属靠来源前缀",
}

LIST = ("https://www.beijing.gov.cn/hudong/hdjl/sindex/"
        "bjah-index-hdjl!letterListJson.action")
DETAIL = "https://www.beijing.gov.cn/hudong/hdjl/com.web.consult.consultDetail.flow"
REFERER = "https://www.beijing.gov.cn/hudong/hdjl/sindex/hdjl-xjxd.html"
PAGE_SIZE = 100
PAUSE = 1.5

_KEY_RE = re.compile(r"([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:")
_STR_RE = re.compile(r"'((?:\\.|[^'\\])*)'")
_TAG_RE = re.compile(r"<[^>]+>")
_BODY_RE = re.compile(r'<div class="[^"]*text-format[^"]*">(.*?)</div>', re.S)
_STRONG_RE = re.compile(r"<strong>(.*?)</strong>", re.S)
_ANS_TIME_RE = re.compile(r"答复时间：\s*([0-9][0-9\-: ]*)")


def _parse_js_obj(s: str) -> dict:
    """把 `{page: {...}, result: [{a:'x'}]}` 这类 **JS 对象字面量**转成 Python dict。

    两步：① 给无引号的键补双引号；② 单引号字符串 → 双引号字符串（转义内部 `"`）。
    """
    s = _KEY_RE.sub(r'\1"\2":', s)

    def _q(m: re.Match) -> str:
        inner = m.group(1).replace("\\'", "'").replace('"', '\\"')
        return '"' + inner + '"'

    return json.loads(_STR_RE.sub(_q, s))


def _clean(html: str | None) -> str:
    """去标签 + 压空白（正文是 HTML 片段），并还原 HTML 实体（`&#40;`→`(`）。

    先剥标签、后 `unescape`：避免把正文里被转义的 `&lt;` 重新变成真标签再被剥掉。
    """
    if not html:
        return ""
    return _html.unescape(re.sub(r"\s+", " ", _TAG_RE.sub(" ", html))).strip()


def _sections(html: str, start: str, end: str) -> list[str]:
    """取所有被 `start`/`end` 注释夹住的片段（可能多段，如多个答复单位）。"""
    out: list[str] = []
    i = 0
    while True:
        i = html.find(start, i)
        if i < 0:
            break
        j = html.find(end, i)
        out.append(html[i + len(start): j if j > 0 else len(html)])
        i = (j + len(end)) if j > 0 else len(html)
    return out


def _parse_detail(html: str) -> dict:
    """从明细 HTML 抽出 {question, answer, dept, answered_at}。"""
    q_secs = _sections(html, "<!--问开始-->", "<!--问结束-->")
    a_secs = _sections(html, "<!--答开始-->", "<!--答结束-->")
    question = ""
    if q_secs:
        m = _BODY_RE.search(q_secs[0])
        if m:
            question = _clean(m.group(1))
    ans_parts: list[str] = []
    dept = ""
    answered_at = None
    for sec in a_secs:
        for m in _BODY_RE.finditer(sec):
            t = _clean(m.group(1))
            if t:
                ans_parts.append(t)
        if not dept:
            ms = _STRONG_RE.search(sec)
            if ms:
                dept = _clean(ms.group(1))
        if not answered_at:
            mt = _ANS_TIME_RE.search(_clean(sec))
            if mt:
                answered_at = mt.group(1).strip()
    return {"question": question, "answer": "\n".join(ans_parts).strip(),
            "dept": dept, "answered_at": answered_at}


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """翻页取「信件选登」列表，逐条取明细拿问题/答复正文，返回统一记录。"""
    out: list[dict] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        if limit and len(out) >= limit:
            break
        url = (f"{LIST}?keyword=&letterType=&page.pageNo={page}"
               f"&page.pageSize={PAGE_SIZE}&orgtitleLength=26")
        r = fetch.post(url, headers={"Referer": REFERER})
        if getattr(r, "status_code", 0) != 200:
            print(f"    [bj-hdjl] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            d = _parse_js_obj(r.text)
        except Exception as e:                                              # noqa: BLE001
            print(f"    [bj-hdjl] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        rows = d.get("result") or []
        pg = d.get("page") or {}
        try:
            total_pages = int(pg.get("totalPages") or 1)
        except (TypeError, ValueError):
            total_pages = 1
        if not rows:
            break
        print(f"    [bj-hdjl] 第 {page}/{total_pages} 页：{len(rows)} 条")
        for it in rows:
            if limit and len(out) >= limit:
                break
            oid = str(it.get("originalId") or "")
            if not oid:
                continue
            title = _clean(it.get("letterTitle"))
            dept = _clean(it.get("orgNames"))
            time.sleep(PAUSE)
            question = title
            answer = ""
            answered_at = it.get("replyDate")
            try:
                dr = fetch(DETAIL, params={"originalId": oid},
                           headers={"Referer": REFERER})
                if getattr(dr, "status_code", 0) == 200:
                    p = _parse_detail(dr.text)
                    question = p["question"] or title
                    answer = p["answer"]
                    dept = p["dept"] or dept
                    answered_at = answered_at or p["answered_at"]
                else:
                    print(f"    [bj-hdjl] 明细 {oid} HTTP {dr.status_code}")
            except Exception as e:                                          # noqa: BLE001
                print(f"    [bj-hdjl] 明细 {oid} 异常 {type(e).__name__}")
            if len(answer) < 10:
                continue
            out.append({
                "source": SITE["key"],
                "id": oid,
                "url": f"{DETAIL}?originalId={oid}",
                "question": question,
                "answer": answer,
                "asked_at": it.get("writeDate"),
                "answered_at": answered_at,
                "dept": dept,
                "channel": "政民互动·信件选登",
                "extra": {
                    "title": title,
                    "letter_type": _clean(it.get("letterTypeName")),
                    "org_names": _clean(it.get("orgNames")),
                    "platform": "首都之窗门户信件库（Struts2）",
                    "answer_kind": "办理答复（常引条例条款）",
                },
            })
        page += 1
        time.sleep(PAUSE)
    print(f"    [bj-hdjl] 收 {len(out)} 条")
    return out
