"""适配器：**周口市·政民互动·咨询受理**（`/front/mailbox/`，河南第 4 个可采市级源）。

## 站点事实（2026-10-10 实测）

- 列表页 `https://www.zhoukou.gov.cn/front/mailbox/mailboxs?siteId=<sid>&category=1`
  是**壳**（10KB，正文只有 `var siteId`）⇒ 列表由 JS 拉
- **接口**（从 `sitesources/zksrmzf/jsp/common/mailbox/mailboxList.js` 抄到）：

  ```js
  $.ajax({ type:'post', url: basePath+'/front/mailbox/tableData',
           data:{ loadMailboxsDataToken:…, category:1, title:'',
                  starttime:'', endtime:'', siteId:siteId,
                  type:1, state:2, open:1, offset:offset, limit:limit } })
  ```

  ⇒ **POST 表单**，参数如上；响应 `{"rows":[{id,title,writeTime,…}],"total":N}`
- ⚠⚠ **必须带 CSRF token**：页面里有
  `<input type="hidden" value="…" id="loadMailboxsDataToken">`
  —— **`value` 在 `id` 前面**（我第一版正则按 `id` 在前写 ⇒ 抠到空串
  ⇒ 接口返回 `{"rows":[],"total":-1}`，**看起来像"没有数据"**）
- **详情**（从 `getHtml(result)` 抄到）：
  `https://www.zhoukou.gov.cn/front/mailbox/mailbox?id=<id>&siteId=<sid>`
  服务端渲染，含「回复时间」+「回复内容」

## 质量（铁律第 6 条）

抽 3 条详情，**答复非空**且带具体电话/依据：
「拨打周口市住房保障和房地产业发展中心大厅（**0394-8221088**）」
「依据省教育厅公布的《本、专科专业对照及考试课程一览表》」

## ⚠ 一个被否掉的入口

`/front/mailbox/add?siteId=...`（我要写信）实测 **404**；
`/front/mailbox/mailboxs` 本身**不是**登录页（与焦作/安阳的登录页不同）。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "zk-zxsq",
    "name": "周口市·政民互动·咨询受理",
    "kind": "api",
    "level": "city",
    "region": "周口市",
    "entry": "https://www.zhoukou.gov.cn/front/mailbox/mailboxs?siteId=9752499e88b94e1881e46bbeeef1376e&category=1",
    "status": "ok",
    "note": "POST /front/mailbox/tableData（需 CSRF token loadMailboxsDataToken）；"
            "详情 /front/mailbox/mailbox?id=&siteId=；实测 total=91，抽 3 条答复非空",
}

SID = "9752499e88b94e1881e46bbeeef1376e"
BASE = "https://www.zhoukou.gov.cn"
PAGE = f"{BASE}/front/mailbox/mailboxs?siteId={SID}&category=1"
API = f"{BASE}/front/mailbox/tableData"
DETAIL_TPL = BASE + "/front/mailbox/mailbox?id={mid}&siteId=" + SID
TOKEN_RE = re.compile(r'<input[^>]*value="([^"]*)"[^>]*id="loadMailboxsDataToken"')
PAGE_SIZE = 20
PAUSE = 0.8
MAX_PAGES = 100

#: HTML 注释 / doctype / CDATA —— 窄正则 `</?[A-Za-z]` **吃不掉**它们
#:   （`<!--` 不以字母开头）。实测（2026-10-10）：周口答复里混进了
#:   `<!--47个文件要求meta-->` ⇒ 必须在剥标签**之前**先剥注释。
_COMMENT = re.compile(r"<!--.*?-->|<![^>]*>", re.S)
_TAG = re.compile(r"</?[A-Za-z][^>]*>")
_BR = re.compile(r"(?i)<br\s*/?>")
_WS = re.compile(r"[ \t\r\f\v]+")


def _clean(s) -> str:
    if not s:
        return ""
    s = _COMMENT.sub(" ", str(s))
    s = _BR.sub("\n", str(s))
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\xa0", " ")
    s = _WS.sub(" ", s)
    return re.sub(r"\n{2,}", "\n", s).strip()


def _real(v) -> str:
    s = _clean(v)
    return "" if s.strip().lower() in ("null", "none", "undefined") else s


def _parse_detail(html: str) -> dict:
    """详情页 → `{question, answer, asked_at, answered_at, dept}`。

    页面结构（实测）：
        … 来信内容 <问题> … 回复时间 <时间> 回复内容 <答复> …
    """
    out = {"question": "", "answer": "", "asked_at": None,
           "answered_at": None, "dept": None}
    txt = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S | re.I)
    txt = _clean(txt)
    # 标题
    m = re.search(r"(?:来信|信件|咨询)?标题[：: ]{0,4}(.{4,80}?)(?:来信内容|信件内容|咨询内容|提交时间|回复时间)",
                  txt)
    if m:
        out["title"] = _real(m.group(1))
    # 提问正文
    m = re.search(r"(?:来信内容|信件内容|咨询内容|反映内容)[：: ]{0,4}"
                  r"(.{5,4000}?)(?:回复时间|办理时间|回复内容|答复内容|受理回复)", txt, re.S)
    if m:
        out["question"] = _real(m.group(1))
    # 回复时间
    m = re.search(r"回复时间[：: ]{0,4}(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})", txt)
    if not m:
        m = re.search(r"回复时间[：: ]{0,4}(\d{4}-\d{2}-\d{2})", txt)
    out["answered_at"] = m.group(1) if m else None
    # 回复正文
    m = re.search(r"(?:回复内容|答复内容)[：: ]{0,4}(.{5,8000}?)(?:相关阅读|关闭当前页面|扫一扫|上一篇|下一篇|$)",
                  txt, re.S)
    if m:
        out["answer"] = _real(m.group(1))
    return out


def harvest(fetch, *, limit: int | None = None, max_pages: int = MAX_PAGES) -> list[dict]:
    """取 token → 翻列表（POST）→ 逐条取详情。

    ⚠ 本接口是 **POST 表单**，而 `harvest.py` 传进来的 `fetch` 是 `client.get`
    的包装 ⇒ **自建 httpx client**（与 `xz_lasa` / `_post_list_common` 同法）。

    ⚠⚠ **逐条取详情必须打进度点**（本模块为此踩过 5 次坑）。
    """
    import httpx

    out: list[dict] = []
    seen: set[str] = set()
    n_detail = n_fail = 0
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120 Safari/537.36")
    with httpx.Client(timeout=30, headers={"User-Agent": ua},
                      follow_redirects=True, trust_env=False, verify=False) as c:
        # 1) 取 CSRF token（**value 在 id 之前**，别写反）
        try:
            ph = c.get(PAGE).text
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 列表页取不到 {type(e).__name__}（停）")
            return []
        m = TOKEN_RE.search(ph)
        token = m.group(1) if m else ""
        if not token:
            print(f"    [{SITE['key']}] **没抠到 CSRF token** —— "
                  f"接口会返回 total=-1（看起来像'没数据'）。停。")
            return []

        total = None
        offset = 0
        for _page in range(1, max_pages + 1):
            if limit and len(out) >= limit:
                break
            data = {"loadMailboxsDataToken": token, "category": 1, "title": "",
                    "starttime": "", "endtime": "", "siteId": SID, "type": 1,
                    "state": 2, "open": 1, "offset": offset, "limit": PAGE_SIZE}
            try:
                r = c.post(API, data=data, headers={"Referer": PAGE})
            except Exception as e:                                      # noqa: BLE001
                print(f"    [{SITE['key']}] 列表 offset={offset} 失败 "
                      f"{type(e).__name__}（停）")
                break
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 列表 offset={offset} HTTP "
                      f"{getattr(r,'status_code','?')}（停）")
                break
            try:
                d = r.json()
            except Exception:                                           # noqa: BLE001
                print(f"    [{SITE['key']}] 列表 offset={offset} 非 JSON（停）")
                break
            rows = d.get("rows") or []
            if total is None:
                total = d.get("total")
                print(f"    [{SITE['key']}] total={total}", flush=True)
            print(f"    [{SITE['key']}] offset={offset}：{len(rows)} 条", flush=True)
            if not rows:
                break
            for it in rows:
                if limit and len(out) >= limit:
                    break
                mid = str(it.get("id") or "")
                if not mid or mid in seen:
                    continue
                seen.add(mid)
                det = {}
                try:
                    dr = c.get(DETAIL_TPL.format(mid=mid), headers={"Referer": PAGE})
                    if getattr(dr, "status_code", 0) == 200:
                        det = _parse_detail(dr.text)
                except Exception:                                       # noqa: BLE001
                    det = {}
                n_detail += 1
                ans = det.get("answer") or ""
                if not ans:
                    n_fail += 1
                    if n_detail % 10 == 0:
                        print(f"    [{SITE['key']}] 明细进度 {n_detail}"
                              f"（无答复 {n_fail}）", flush=True)
                    time.sleep(PAUSE)
                    continue
                if n_detail % 10 == 0:
                    print(f"    [{SITE['key']}] 明细进度 {n_detail}"
                          f"（无答复 {n_fail}）", flush=True)
                out.append({
                    "source": SITE["key"],
                    "id": mid,
                    "url": DETAIL_TPL.format(mid=mid),
                    "question": det.get("question") or _real(it.get("title")),
                    "answer": ans,
                    "asked_at": None,
                    "answered_at": det.get("answered_at"),
                    "dept": det.get("dept"),
                    "channel": "咨询受理",
                    "extra": {
                        "title": det.get("title") or _real(it.get("title")),
                        "write_time": _real(it.get("writeTime")) or None,
                        "case_state": it.get("state"),
                        "platform": "周口市政府门户（front/mailbox/tableData）",
                    },
                })
                time.sleep(PAUSE)
            if len(rows) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
    print(f"    [{SITE['key']}] 收 {len(out)} 条；明细取 {n_detail} 条，其中无答复 {n_fail} 条")
    return out
