"""适配器：**蚌埠市·政民直通车·信件选登**（安徽第 5 个可采市级源）。

## 站点事实（2026-10-13 实测）

栏目页 `https://www.bengbu.gov.cn/hdjl/zmztc/index.html` 是 **JS 外壳**
（`<title>政民直通车_蚌埠市人民政府</title>`，静态抓不到条目）。

### 与芜湖（`wh-hdjl`）**同一个 CMS 家族**，但四处全不一样

| 项 | 芜湖 `wh-hdjl` | 蚌埠 `bb-hdjl` |
|---|---|---|
| 标签路由 | `/site/label/8888` | `/site/label/8888`（**同一个**）|
| `labelName` | `messageBoardPageList` | **`hotlineSZPageList`** |
| 响应格式 | **JSON**（content-type 却是 text/html）| **HTML 片段**（`<ul><li>`）|
| `pageIndex` | **请求 1 起**（0 会 HTTP 550）| **0 起** |
| 额外参数 | `siteId/organId/type/ids/…` | `file=/c1/bengbu/hotlineSZPageList_new2020` |
| 明细 URL | `/content/article/<baseContentId>` | **`/site/tpl/8002?cguid=<uuid>`** |
| 明细字段 | 信件内容 / 回复内容 / 回复时间 | **诉求内容 / 回复内容 / 答复时间 / 诉求类型** |

⇒ **「同一个 `/site/label/8888`」不等于「同一套参数」** ——
与 `ANHUI-CITY-LEADS.md` 里铜陵/池州那条教训是同一个病：
**不能因为平台一样就照抄适配器，四处都要从目标站自己的页面 JS 里抄。**

列表调用（页面 JS `hotline12345PageList(pageIndex,pageSize,keyWord,docNum,startDate,endDate)`）：

```
GET https://www.bengbu.gov.cn/site/label/8888
    ?labelName=hotlineSZPageList&pageIndex=<N>&pageSize=100
    &keyWord=&serialnum=&startTime=&endTime=
    &file=/c1/bengbu/hotlineSZPageList_new2020
```

返回 HTML：

```html
<li class="num1 odd clearfix">
  <div class="t1"><a href="https://www.bengbu.gov.cn/site/tpl/8002?cguid=<uuid>"
                     title="蚌埠南站停车">蚌埠南站停车</a></div>
  <p class="t2" title="蚌投集团">蚌投集团</p>
  <p class="t4">2026-08-05</p>
</li>
```

明细 `/site/tpl/8002?cguid=<uuid>` **服务端渲染**，且**表格结构与芜湖逐字一致**
（`<th class="tit">字段：</th><td class="nr…">值</td>`）⇒ 解析正则可以直接复用。

## 质量（铁律第 6 条）

抽 1 条（`cguid=91830675-…`，「蚌埠南站停车」）：
诉求内容 160 字、答复 **非空且 400+ 字**，给出「暂无开通包月套餐服务的计划」的明确结论
+ 理由 + **经办单位联系电话**（蚌埠市投资促进有限公司 17760840960）⇒ 优质考卷料。
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import time

SITE = {
    "key": "bb-hdjl",
    "name": "蚌埠市·政民直通车·信件选登",
    "kind": "json",
    "level": "city",
    "region": "蚌埠市",
    "entry": "https://www.bengbu.gov.cn/hdjl/zmztc/index.html",
    "status": "ok",
    "note": "/site/label/8888 标签路由（labelName=hotlineSZPageList，返回 HTML）；"
            "pageIndex 0 起；明细 /site/tpl/8002?cguid=<uuid>",
}

BASE = "https://www.bengbu.gov.cn"
LIST_URL = BASE + "/site/label/8888"
LABEL_NAME = "hotlineSZPageList"
LIST_FILE = "/c1/bengbu/hotlineSZPageList_new2020"
PAGE_SIZE = 100
PAUSE = 0.8
MAX_PAGES = 200

#: 列表页之间必须停顿（同 `wh_hdjl` 的教训：连续打列表页会触发按时间窗口的 IP 配额 429）。
LIST_PAUSE = 3.0
RETRY_ATTEMPTS = 4
RETRY_BACKOFF = 5.0
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})

_TAG = re.compile(r"</?[A-Za-z][^>]*>")
_COMMENT = re.compile(r"<!--.*?-->|<![^>]*>", re.S)
_BR = re.compile(r"(?i)<br\s*/?>")
_P = re.compile(r"(?i)</p>")
_WS = re.compile(r"[ \t\r\f\v]+")

# 列表项：<a href="…?cguid=xxx" title="标题">…</a>，后跟 <p class="t2">单位</p> 与 <p class="t4">日期</p>
_ITEM = re.compile(
    r'<a\s+href="([^"]*?cguid=([0-9a-fA-F-]{36}))"[^>]*title="([^"]*)"[^>]*>.*?</a>'
    r'(?:\s*<p[^>]*class="[^"]*\bt2\b[^"]*"[^>]*>(.*?)</p>)?'
    r'(?:\s*<p[^>]*class="[^"]*\bt4\b[^"]*"[^>]*>(.*?)</p>)?',
    re.S,
)

# 明细表：<th class="tit">字段：</th><td class="nr…">值</td>
_FIELD = re.compile(
    r'<th[^>]*class="[^"]*\btit\b[^"]*"[^>]*>\s*([^<：:]{2,10})\s*[：:]\s*</th>\s*'
    r'<td[^>]*class="[^"]*\bnr[^"]*"[^>]*>(.*?)</td>',
    re.S,
)


def existing_ids(site_key: str) -> set:
    """读 `data/<site_key>-*.jsonl` 已有 id（增量续采用）。"""
    out: set[str] = set()
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    if not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        if fn.startswith(site_key + "-") and fn.endswith(".jsonl"):
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:                                   # noqa: BLE001
                        continue
                    rid = rec.get("id")
                    if rid:
                        out.add(str(rid))
    return out


def _clean(s) -> str:
    if not s:
        return ""
    s = _COMMENT.sub(" ", str(s))
    s = _BR.sub("\n", s)
    s = _P.sub("\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\xa0", " ")
    s = _WS.sub(" ", s)
    return re.sub(r"\n{2,}", "\n", s).strip()


def _real(v) -> str:
    s = _clean(v)
    return "" if s.strip().lower() in ("null", "none", "undefined") else s


def _get(fetch, url, *, params=None, attempts: int = RETRY_ATTEMPTS):
    """带指数退避重试的取页（429/5xx 重试）。"""
    r = None
    for n in range(attempts):
        try:
            r = fetch(url, params=params) if params is not None else fetch(url)
        except Exception:                                               # noqa: BLE001
            if n == attempts - 1:
                raise
            time.sleep(RETRY_BACKOFF * (2 ** n))
            continue
        code = getattr(r, "status_code", 0)
        if code not in RETRY_STATUS or n == attempts - 1:
            return r
        wait = RETRY_BACKOFF * (2 ** n)
        print(f"    [{SITE['key']}] HTTP {code}（限流/故障），退避 {wait:.0f}s 后重试"
              f"（第 {n + 1}/{attempts - 1} 次）", flush=True)
        time.sleep(wait)
    return r


def _parse_list(text: str) -> list:
    """列表 HTML 片段 → `[{id, title, dept, date, url}]`（去重、保序）。"""
    out, seen = [], set()
    for href, cguid, title, dept, date in _ITEM.findall(text or ""):
        if cguid in seen:
            continue
        seen.add(cguid)
        t = _real(title)
        if not t:
            continue
        out.append({
            "id": cguid,
            "title": t,
            "dept": _real(dept) or None,
            "date": _real(date) or None,
            "url": href if href.startswith("http") else BASE + href,
        })
    return out


def _parse_detail(html_text: str) -> dict:
    """明细页 → `{question, answer, asked_at, answered_at, msg_type, dept, doc_num}`。

    结构：`<th class="tit">诉求内容：</th><td class="nrtxt">…</td>` 等（与芜湖同构）。
    """
    out = {"question": None, "answer": "", "asked_at": None, "answered_at": None,
           "msg_type": None, "dept": None, "doc_num": None}
    fields: dict[str, str] = {}
    for key, raw in _FIELD.findall(html_text or ""):
        k = re.sub(r"\s+", "", key)          # 「姓 名」→「姓名」
        v = _real(raw)
        if k and v and k not in fields:
            fields[k] = v
    out["question"] = fields.get("诉求内容") or fields.get("信件内容")
    out["answer"] = fields.get("回复内容") or fields.get("答复内容") or ""
    out["asked_at"] = fields.get("来信时间") or fields.get("留言时间")
    out["answered_at"] = fields.get("答复时间") or fields.get("回复时间")
    out["msg_type"] = fields.get("诉求类型") or fields.get("信件类型") or fields.get("留言类型")
    out["dept"] = fields.get("回复单位") or fields.get("答复单位")
    out["doc_num"] = fields.get("信件编号")
    return out


def harvest(fetch, *, limit: int | None = None, max_pages: int = MAX_PAGES,
            skip_ids: set | None = None) -> list[dict]:
    """翻列表 HTML（pageIndex **0 起**）+ 逐条取明细。

    `skip_ids` 默认自动取已落盘 id；命中的**连明细都不取**且**不计入 limit**
    ⇒ `limit` 语义是「本轮**新增**条数」。
    """
    if skip_ids is None:
        skip_ids = existing_ids(SITE["key"])
    out: list[dict] = []
    seen: set[str] = set()
    n_detail = n_skip = n_fail = 0

    for page in range(0, max_pages):
        if limit and len(out) >= limit:
            break
        params = {
            "labelName": LABEL_NAME, "pageIndex": page, "pageSize": PAGE_SIZE,
            "keyWord": "", "serialnum": "", "startTime": "", "endTime": "",
            "file": LIST_FILE,
        }
        try:
            r = _get(fetch, LIST_URL, params=params)
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页失败 {type(e).__name__}（停）", flush=True)
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（重试后仍失败，停）", flush=True)
            break
        items = _parse_list(getattr(r, "text", "") or "")
        if not items:
            print(f"    [{SITE['key']}] 列表第 {page} 页 0 条（停）", flush=True)
            break
        print(f"    [{SITE['key']}] 列表第 {page} 页：{len(items)} 条", flush=True)
        time.sleep(LIST_PAUSE)

        for it in items:
            if limit and len(out) >= limit:
                break
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            if it["id"] in skip_ids:
                n_skip += 1
                continue
            det = {}
            try:
                d = _get(fetch, it["url"])
                if getattr(d, "status_code", 0) == 200:
                    det = _parse_detail(getattr(d, "text", "") or "")
            except Exception:                                           # noqa: BLE001
                det = {}
            n_detail += 1
            ans = det.get("answer") or ""
            if not ans:
                n_fail += 1
            else:
                out.append({
                    "source": SITE["key"],
                    "id": det.get("doc_num") or it["id"],
                    "url": it["url"],
                    "question": det.get("question") or it["title"],
                    "answer": ans,
                    "asked_at": det.get("asked_at") or it["date"],
                    "answered_at": det.get("answered_at"),
                    "dept": det.get("dept") or it["dept"],
                    "channel": "政民直通车",
                    "extra": {
                        "title": it["title"],
                        "msg_type": det.get("msg_type"),
                        "cguid": it["id"],
                        "city": "蚌埠市",
                        "platform": "蚌埠市政府门户（/site/label/8888 标签路由）",
                    },
                })
            if n_detail % 20 == 0:
                print(f"    [{SITE['key']}] 明细进度 {n_detail}（收 {len(out)}，"
                      f"无答复 {n_fail}，跳过已落盘 {n_skip}）", flush=True)
            time.sleep(PAUSE)

    print(f"    [{SITE['key']}] 收 {len(out)} 条；明细取 {n_detail} 条，"
          f"其中无答复 {n_fail} 条，跳过已落盘 {n_skip} 条", flush=True)
    return out
