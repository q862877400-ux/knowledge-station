"""适配器：**芜湖市·12345 政务服务便民热线·信件选登**（安徽第 4 个可采市级源）。

## 站点事实（2026-10-13 实测）

栏目页 `https://www.wuhu.gov.cn/zmhd/12345zfztc/index.html` 是 **JS 外壳**
（内容模板是 `<?=item.baseContentId?>`，静态抓不到任何条目）。真实数据在 XHR 里：

```
GET https://www.wuhu.gov.cn/site/label/8888
    ?isJson=true&labelName=messageBoardPageList&siteId=6787231
    &organId=&pageSize=15&isUseLabelCache=true&pageIndex=<N>
    &isReply=1&merge=false&organName=&type=3
    &ids=6787581,6787571&isPageMore=true
    &title=&startDate=&endDate=&searchType=title
```

### ★ 三个必须记住的坑

1. **`pageIndex` 是 1 起，且 0 会炸。** 实测 `pageIndex=0` ⇒ **HTTP 550**；
   `pageIndex=1` ⇒ 响应里 `page.index=0`（**响应回显 0 起，请求是 1 起**）。
   别被响应里的 `pageIndex` 骗 —— 用它当下一页会原地打转。
2. **不能直接打 `/OneToFiveMessageBoard/getSzxxMessageBoardPageLst`。**
   页面 JS 里那个 `url` 字段指向它，但**直接请求返回 20 字节**：
   `标签ID(8888)：不存在或已被删除.` —— 必须走 **`/site/label/8888` 标签路由**，
   由标签名 `messageBoardPageList` 间接命中。
3. **响应 `content-type` 是 `text/html`，但 body 是 JSON。**
   别用 `response.json()` 依赖 content-type 的库逻辑，直接 `json.loads(r.text)`。

分页（pageSize=3 实测）：`total=847 / pageCount=283`
⇒ pageSize=15 时约 **57 页**、**847 条**。

### 数据形态

列表 JSON 已带 `messageBoardContent`（**问题全文**）与 `className`（站方标签），
但**不带答复** ⇒ 仍须逐条取明细。

明细 `https://www.wuhu.gov.cn/content/article/<baseContentId>` 是**服务端渲染**，
结构规整（th/td 成对）：

```html
<h1 class="wztit">关于何时可领取注册计量师证书的问题</h1>
<table class="liuyancon">
  <tr><th class="tit">信件编号：</th><td class="nr">26092438717</td>
      <th class="tit">来信时间：</th><td class="nr get-letter-time">2026-09-24 11:18:28</td></tr>
  <tr><th class="tit">信件类型：</th><td class="nr">我要咨询</td> …</tr>
  <tr><th class="tit">信件内容：</th><td colspan="3" class="nrtxt">…</td></tr>
</table>
<h3 class="ls-msg-title">回复情况</h3>
<table class="liuyancon">
  <tr><th class="tit">回复单位：</th><td class="nr">芜湖市12345热线</td>
      <th class="tit">回复时间：</th><td class="nr data">2026-09-28 09:46:43</td></tr>
  <tr><th class="tit">回复内容：</th><td colspan="3" class="nrtxt">…</td></tr>
</table>
```

## 质量（铁律第 6 条）

抽 1 条（`baseContentId=41338717`）：答复 **非空且是优质考卷料** ——
写明"注册计量师证书可领取通知已发布"，给出办理路径（市人社局官网 → 专题专栏 → 人事考试 /
皖事通 APP），并附**经办单位与电话**（芜湖市人社局 0553-3991192）。
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import time

SITE = {
    "key": "wh-hdjl",
    "name": "芜湖市·12345政务服务便民热线·信件选登",
    "kind": "json",
    "level": "city",
    "region": "芜湖市",
    "entry": "https://www.wuhu.gov.cn/zmhd/12345zfztc/index.html",
    "status": "ok",
    "note": "/site/label/8888 标签路由（labelName=messageBoardPageList）；"
            "pageIndex 请求 1 起 / 响应 0 起；实测 total=847",
}

BASE = "https://www.wuhu.gov.cn"
LIST_URL = BASE + "/site/label/8888"
DETAIL_TPL = BASE + "/content/article/{cid}"

SITE_ID = 6787231
COLUMN_IDS = "6787581,6787571"
PAGE_SIZE = 15
PAUSE = 0.8
MAX_PAGES = 120

_TAG = re.compile(r"</?[A-Za-z][^>]*>")
_COMMENT = re.compile(r"<!--.*?-->|<![^>]*>", re.S)
_BR = re.compile(r"(?i)<br\s*/?>")
_P = re.compile(r"(?i)</p>")
_WS = re.compile(r"[ \t\r\f\v]+")

# `<th class="tit">字段名：</th><td class="nr...">值</td>`
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


def _norm_type(v: str) -> str | None:
    """站方标签归一化：「我要咨询」→「咨询」（去掉前缀，保留语义）。"""
    s = _real(v)
    if not s:
        return None
    return re.sub(r"^我要", "", s) or s


def _parse_list(text: str) -> tuple[list, dict]:
    """列表响应 → `(items, meta)`；解析失败返回 `([], {})`。

    ⚠ 响应 content-type 是 text/html，body 才是 JSON ⇒ 只能 `json.loads(text)`。
    """
    try:
        page = json.loads(text).get("page") or {}
    except Exception:                                                   # noqa: BLE001
        return [], {}
    data = page.get("data") or []
    items = []
    for it in data:
        cid = it.get("baseContentId")
        if not cid:
            continue
        items.append({
            "id": str(it.get("docNum") or cid),
            "cid": cid,
            "title": _real(it.get("title")),
            "question": _real(it.get("messageBoardContent")),
            "asked_at": _real(it.get("addDate")) or None,
            "answered_at": _real(it.get("replyDate")) or None,
            "msg_type": _norm_type(it.get("className")),
            "dept": _real(it.get("receiveUnitName")) or None,
            "url": it.get("link") or DETAIL_TPL.format(cid=cid),
        })
    meta = {}
    for k in ("total", "pageCount", "pageIndex"):
        if isinstance(page.get(k), int):
            meta[k] = page[k]
    return items, meta


def _parse_detail(html_text: str) -> dict:
    """详情页 → `{answer, asked_at, answered_at, msg_type, dept, title, question}`。"""
    out = {"answer": "", "asked_at": None, "answered_at": None,
           "msg_type": None, "dept": None, "title": None, "question": None}
    m = re.search(r'<h1[^>]*class="[^"]*\bwztit\b[^"]*"[^>]*>(.*?)</h1>', html_text, re.S)
    if m:
        out["title"] = _real(m.group(1))

    fields: dict[str, str] = {}
    for key, raw in _FIELD.findall(html_text):
        k = key.strip()
        v = _real(raw)
        if k and v and k not in fields:
            fields[k] = v

    out["answer"] = fields.get("回复内容", "")
    out["question"] = fields.get("信件内容", "") or None
    out["asked_at"] = fields.get("来信时间") or None
    out["answered_at"] = fields.get("回复时间") or None
    out["msg_type"] = _norm_type(fields.get("信件类型", ""))
    out["dept"] = fields.get("回复单位") or None
    return out


def harvest(fetch, *, limit: int | None = None, max_pages: int = MAX_PAGES,
            skip_ids: set | None = None) -> list[dict]:
    """翻列表 JSON（pageIndex **1 起**）+ 逐条取明细。

    ★ `skip_ids`：默认自动取已落盘 id。命中的**连明细都不取**，且**不计入 limit**
    ⇒ `limit` 的语义是「本轮**新增**条数」（照抄 `_gd_hdjlpt_common` 第 7 轮修法）。
    """
    if skip_ids is None:
        skip_ids = existing_ids(SITE["key"])
    out: list[dict] = []
    seen: set[str] = set()
    n_detail = n_skip = n_fail = 0

    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        params = {
            "isJson": "true", "labelName": "messageBoardPageList",
            "siteId": SITE_ID, "organId": "", "pageSize": str(PAGE_SIZE),
            "isUseLabelCache": "true", "pageIndex": page, "isReply": 1,
            "merge": "false", "organName": "", "type": 3,
            "ids": COLUMN_IDS, "isPageMore": "true",
            "title": "", "startDate": "", "endDate": "", "searchType": "title",
        }
        try:
            r = fetch(LIST_URL, params=params)
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页失败 {type(e).__name__}（停）", flush=True)
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）", flush=True)
            break
        items, meta = _parse_list(getattr(r, "text", "") or "")
        if page == 1 and meta:
            print(f"    [{SITE['key']}] 站点自报 total={meta.get('total')} "
                  f"pageCount={meta.get('pageCount')}", flush=True)
        if not items:
            print(f"    [{SITE['key']}] 列表第 {page} 页 0 条（停）", flush=True)
            break
        print(f"    [{SITE['key']}] 列表第 {page} 页：{len(items)} 条", flush=True)

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
                d = fetch(it["url"])
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
                    "id": it["id"],
                    "url": it["url"],
                    "question": det.get("question") or it["question"] or it["title"],
                    "answer": ans,
                    "asked_at": det.get("asked_at") or it["asked_at"],
                    "answered_at": det.get("answered_at") or it["answered_at"],
                    "dept": det.get("dept") or it["dept"],
                    "channel": "12345热线",
                    "extra": {
                        "title": det.get("title") or it["title"],
                        "msg_type": det.get("msg_type") or it["msg_type"],
                        "docNum": it["id"],
                        "city": "芜湖市",
                        "platform": "芜湖市政府门户（/site/label/8888 标签路由）",
                    },
                })
            if n_detail % 20 == 0:
                print(f"    [{SITE['key']}] 明细进度 {n_detail}（收 {len(out)}，"
                      f"无答复 {n_fail}，跳过已落盘 {n_skip}）", flush=True)
            time.sleep(PAUSE)

    print(f"    [{SITE['key']}] 收 {len(out)} 条；明细取 {n_detail} 条，"
          f"其中无答复 {n_fail} 条，跳过已落盘 {n_skip} 条", flush=True)
    return out
