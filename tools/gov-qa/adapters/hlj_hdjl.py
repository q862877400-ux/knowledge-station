"""适配器：**黑龙江省人民政府门户 · 政民互动（留言选登）**。

## 站点形态（2026-10-08 实探，证据 recon/hlj-list.html / hlj-detail.html；同日重写，见下）
 · 入口 `/hlj/c115707/wycx.shtml`（留言选登）。列表静态页只渲染 11 条，
   **翻页走 JS 接口**（`/hlj/xhtml/js/wycx.js` 的 `table_ajax()`）：
   `GET /common/search/<channelId>?_isAgg=false&_isJson=true&_pageSize=100
        &_template=index&_rangeTimeGte=&_channelName=&page=<页码>`
   其中 `channelId=bec7146b06964311a4fb4b77e1eea17d`（取自列表页 `<meta name="channelId">`）。
   → JSON `{data:{total, results:[{…, domainMetaList, manuscriptId, url, title, …}]}}`
   （实测 **total=4082**）。

## ★★ 2026-10-08 重写：列表接口即全量，**不再抓明细页**
实测 `results[].domainMetaList[0].resultList` 是**结构化字段数组**，`name` 直接是中文列名：
`留言内容`(问题) / `回复内容`(答复) / `回复单位` / `回复时间` / `留言时间` / `办件编号`
/ `办理状态` / `类型` / `领域` / `留言人` / `评价`。
证据 `recon/hlj-common-search.sample.json`。**答复文本与明细页同源且是完整版**。
 ⇒ 原实现「1 次列表 + 每条来信 1 次明细」= 4083 次请求 ≈ 2.5 小时；
   现实现「`_pageSize=200` 翻页」= **21 次请求 ≈ 40 秒**（`_pageSize` 实测无上限）。
 ⇒ 旧注释「列表页的答复是截断的，必须以明细页为准」是**误判**：截断的是列表页
   **HTML 静态渲染**，接口返回的 `回复内容` 本来就是完整字段。
 ⚠ `resultList` **顺序不稳定**，`listpage_lyhf.js` 按下标取值是投机取巧；
   本适配器**一律按 `name` 取值**（见 `_meta_map`）。
 ⚠ `value` 里偶有字符串 `"null"`（「评价」字段实测有）⇒ `_clean_meta` 归一成 None。
 ⚠ 去重键用 `manuscriptId`（稳定数字），不用 `url`（同一条来信的 url 可能变）。

## 说明
答复是**承办单位办理答复**（如「哈尔滨市公安局交通管理支队」「哈尔滨市阿城区人民政府」），
带单位与时间 ⇒ 可当考卷口径。`answer` 取 `回复内容` 原文，不清洗。

## 已排除的扩展路线（别再走）
 · 「省级门户站群多 channelId」：门户「部门互动」`/hlj/c115777/dep_list.shtml` 的
   channelId=`f6365b0d9fa64c39859ba0ef1b584a45` 返回的**不是留言**，而是 **40 个厅局的
   政民互动入口 URL 清单**（`recon/hlj-dep-roster.json`，这个清单本身有用）。
 · 「40 个厅局各自的留言公开栏目」：每个厅局站确实是独立站群，其
   `/xxx/ldxx/public_wycx.shtml` 有自己的 channelId（教育厅 `3df6c090…` /
   生态环境厅 `007c274c…`，见 `recon/hlj-dep-roster.json` 同批探测），
   但 `common/search/<该 channelId>` **`total=0`** ⇒ 厅局留言栏目是**空壳**，
   数据全在省门户这个 channelId 里。**别再逐个厅局抓页面找 channelId**。
 · 「厅局 `api-mailbox/frontMail/mailList` 接口」：这是另一个中间件（与湖南同族，
   见 `_hunan_hd_common.py`），黑龙江侧**强签名**：
   `POST /communication/api-base/dict/getKey`（form `val=<明文>`）拿 AES key
   → `sign = AES(timestamp + 参数按字母序拼接)`，`timestamp` 是毫秒。
   **JSON 路径缺 sign/timestamp 一律 401**（`缺少sign或者timestamp`）；
   **form 路径不校验签名但服务端解析不出参数**（恒 `99002 未知错误`）。
   服务端 `getKey` 是**确定性映射**（同明文恒同密文）⇒ 固定 key 的 ECB/CBC，
   但对 10 万条候选 key 字典爆破**未命中** ⇒ **这道墙本轮未破，别再花时间**。
   证据：`recon/hlj-jyt-zmhd.html` / `hlj-aejpublic.js` / `hlj-aes.js` / `hlj-dept-tree.json`。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "hlj-hdjl",
    "name": "黑龙江省人民政府·政民互动（留言选登）",
    "kind": "api",
    "level": "province",
    "entry": "https://www.hlj.gov.cn/hlj/c115707/wycx.shtml",
    "status": "ok",
    "note": "列表 /common/search/<channelId> 接口(total≈4082, pageSize≤100) + 静态明细(留言内容/回复内容)",
}

KEY = "hlj-hdjl"
BASE = "https://www.hlj.gov.cn"
CHANNEL_ID = "bec7146b06964311a4fb4b77e1eea17d"
LIST_API = BASE + "/common/search/" + CHANNEL_ID
#: ★ 实测 `_pageSize` **无上限**（100/200/500 都整页返回）⇒ 200 是「请求数 ~ 响应体大小」的折中。
PAGE_SIZE = 200
LIST_PARAMS = {"_isAgg": "false", "_isJson": "true", "_pageSize": str(PAGE_SIZE),
               "_template": "index", "_rangeTimeGte": "", "_channelName": ""}
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
Q_RE = re.compile(r'<font>留言内容</font>\s*</td>\s*<td[^>]*class="cont"[^>]*>(.*?)</td>', re.S)
A_RE = re.compile(r'<font>回复内容</font>\s*</td>\s*<td[^>]*class="cont"[^>]*>(.*?)</td>', re.S)
DEPT_RE = re.compile(r'回复单位</td>\s*<td[^>]*><span></span>(.*?)</td>', re.S)
ANS_RE = re.compile(r'>回复时间</td>\s*<td[^>]*><span>(.*?)</span>', re.S)
ASK_RE = re.compile(r'>留言时间</td>\s*<td[^>]*><span>(.*?)</span>', re.S)
ID_RE = re.compile(r'<td[^>]*>ID</td>\s*<td[^>]*><span>(.*?)</span>', re.S)
TITLE_RE = re.compile(r'<td class="biaoti" width="10%">标题</td>\s*<td[^>]*><span><p>(.*?)</p>',
                      re.S)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _parse_detail(html: str) -> dict | None:
    q = Q_RE.search(html)
    a = A_RE.search(html)
    if not q or not a:
        return None
    question = _text(q.group(1))
    answer = _text(a.group(1))
    if len(question) < 4 or len(answer) < 10:
        return None
    d = DEPT_RE.search(html)
    at = ANS_RE.search(html)
    ak = ASK_RE.search(html)
    tm = TITLE_RE.search(html)
    return {"question": question, "answer": answer,
            "title": _text(tm.group(1)) if tm else None,
            "dept": _text(d.group(1)) if d else None,
            "answered_at": at.group(1).strip() if at else None,
            "asked_at": ak.group(1).strip() if ak else None}


def _meta_map(it: dict) -> dict:
    """把 `domainMetaList[0].resultList` 摊平成 {中文名: 值}。

    ⚠ 该数组的**顺序不稳定**（`listpage_lyhf.js` 里按 `resultList[3]`/`[4]`/`[10]`
       取下标，那是**投机取巧**；实测各条来信的 `resultList` 长度与顺序都不一致）
       ⇒ 必须**按 `name` 取值**，不能按下标。
    """
    dm = it.get("domainMetaList") or []
    if not dm:
        return {}
    out: dict[str, str] = {}
    for x in (dm[0].get("resultList") or []):
        nm = x.get("name")
        val = x.get("value")
        if nm and val is not None:
            out[str(nm)] = str(val)
    return out


def _clean_meta(v: str | None) -> str | None:
    """`value` 里偶有字符串 `"null"`（实测「评价」字段）⇒ 归一成 None。"""
    if v is None:
        return None
    s = v.strip()
    return None if s in ("", "null", "None") else s


def harvest(fetch, *, limit: int | None = None, max_pages: int = 20,
            page_size: int = PAGE_SIZE) -> list[dict]:
    """翻列表接口直接取全量（**不再逐条抓明细页**）。

    ## 2026-10-08 重写（原实现 8 倍浪费）
    原实现：1 次列表 + **每条来信 1 次明细页**，4082 条 ⇒ 4083 次请求、约 2.5 小时。
    实测发现：**列表接口的 `domainMetaList[0].resultList` 已含全部字段**
    —— `留言内容` / `回复内容` / `回复单位` / `回复时间` / `留言时间` / `办件编号`
    / `办理状态` / `类型` / `领域` / `留言人`（证据 `recon/hlj-common-search.sample.json`），
    且 `_pageSize` **实测无上限**（100/200/500 都整页返回）
    ⇒ 4082 条 **21 次请求**（pageSize=200）、约 40 秒即可采完。
    ⚠ 明细页的答复文本与列表 `回复内容` **同源**（列表是完整版，不是截断）；
      旧注释里「列表页的答复是截断的」是**误判**——截断的是列表页**HTML 静态渲染**，
      接口返回的是完整 `回复内容`。
    """
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        params = dict(LIST_PARAMS)
        params["page"] = str(page)
        params["_pageSize"] = str(page_size)
        r = fetch(LIST_API, params=params)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            data = r.json().get("data") or {}
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页 JSON 异常 {type(e).__name__}（停）")
            break
        results = data.get("results") or []
        if total is None:
            total = data.get("total")
            print(f"    [{SITE['key']}] total={total}（pageSize={page_size} ⇒ 约 "
                  f"{-(-int(total or 0) // page_size)} 页即可取全）")
        if not results:
            break
        fresh = 0
        for it in results:
            if limit and len(out) >= limit:
                break
            kv = _meta_map(it)
            uid = str(it.get("manuscriptId") or "").strip()
            if not uid or uid in seen:
                continue
            seen.add(uid)
            question = _clean_meta(kv.get("留言内容")) or it.get("title")
            answer = _clean_meta(kv.get("回复内容"))
            # 与旧解析器同口径：问题 <4 字或答复 <10 字的丢掉
            if not answer or len(answer) < 10 or not question or len(question) < 4:
                continue
            path = it.get("url") or ""
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": (path if path.startswith("http") else BASE + path) if path else None,
                "question": question,
                "answer": answer,
                "asked_at": _clean_meta(kv.get("留言时间")),
                "answered_at": _clean_meta(kv.get("回复时间")),
                "dept": _clean_meta(kv.get("回复单位")),
                "channel": "政民互动·留言选登",
                "extra": {
                    "title": it.get("title"),
                    "case_no": _clean_meta(kv.get("办件编号")),
                    "reply_no": _clean_meta(kv.get("回复编号")),
                    "status": _clean_meta(kv.get("办理状态")),
                    "kind": _clean_meta(kv.get("类型")),
                    "domain": _clean_meta(kv.get("领域")),
                    "reply_meta_name": ((it.get("domainMetaList") or [{}])[0]
                                        .get("domainMetadataName")),
                    "list_api": LIST_API,
                    "answer_kind": "承办单位办理答复",
                },
            })
            fresh += 1
        print(f"    [{SITE['key']}] 第 {page} 页：条目 {len(results)}，入库 {fresh}"
              f"（已累计 {len(out)}）")
        if total and page * page_size >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条（列表接口直取，未抓明细页）")
    return out
