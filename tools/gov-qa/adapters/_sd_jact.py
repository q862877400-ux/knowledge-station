"""山东地市 jact 基座（**http**；列表支持 POST/GET 两种）。

## 为什么另起一个基座
`adapters/_jact_common.py` 是江苏版，**硬编码 `https://{host}`** 且列表固定 POST。
山东地市实测：
 · **东营** `http://www.dongying.gov.cn/jact/`（sysid=129，**POST** 列表，totalRecord=20299）；
 · **淄博** `http://www.zibo.gov.cn/jact/`（sysid=54，**GET** 列表，totalRecord=376）；
 · 两站 https 均不可用（证书不匹配）⇒ 必须 http。
⇒ 复用 `_jact_common` 的 `parse_list` **与 `parse_detail`**（后者已含 `LABEL_ALIASES`
  别名归一：答复内容/答复机构/答复时间 ↔ 内容回复/答复单位/回复日期），仅另实现
  「http + POST/GET 可配」的采集循环。**明细解析不再自建，避免两套逻辑分叉。**

## 接口（与江苏同构）
 · 列表 `{base}/jact/front/dataproxy_mailpublist.do?startrecord=&endrecord=&perpage=&groupSize=3`
   · POST（东营）：参数走表单 body；
   · GET（淄博）：参数走 query string。
   返回 JS 文本：`totalRecord=N;dataStore=["<tr…transactId=…>…</tr>", …]`
 · 明细 `GET {base}/jact/front/mailpubdetail.do?transactId=<id>&sysid=<n>` → HTML 表格，
   标签/值是**相邻两个 `<td>`**；由 `_jact_common.parse_detail` 归一。
"""
from __future__ import annotations

import time
from urllib.parse import urlencode

from adapters._jact_common import (DETAIL_PATH, GROUP_SIZE, LIST_PATH, PAUSE,
                                   parse_detail, parse_list)


def _env_page_from() -> int:
    """起始页号：环境变量 `GOVQA_PAGE_FROM`（把超长源分块采）。"""
    import os
    try:
        return max(1, int(os.environ.get("GOVQA_PAGE_FROM", "1")))
    except ValueError:
        return 1


def harvest_jact_sd(fetch, *, SITE: dict, base: str, sysid: str,
                    list_method: str = "POST", per_page: int = 19,
                    limit: int | None = None, pause: float = PAUSE,
                    page_from: int | None = None) -> list[dict]:
    """采山东某市 jact 信箱（问题 + 答复全文）。`list_method` ∈ {POST, GET}。

    `page_from` = 起始页号（默认读环境变量 `GOVQA_PAGE_FROM`，再默认 1）。
    ⚠ `harvest.py` 只在跑完时落盘 ⇒ 大源必须分块，否则 timeout 一到就是零产出。
    """
    out: list[dict] = []
    ref = f"{base}/jact/front/mailpublist.do?sysid={sysid}"
    total = None
    page = page_from if page_from is not None else _env_page_from()
    while True:
        if limit and len(out) >= limit:
            break
        start = (page - 1) * per_page + 1
        end = page * per_page
        url = (f"{base}{LIST_PATH}?startrecord={start}&endrecord={end}"
               f"&perpage={per_page}&groupSize={GROUP_SIZE}")
        params = {"sysid": str(sysid), "datadetailid": "", "dicvalue": "",
                  "mailnumber": "", "querycode": "", "groupid": "", "mailstate": "",
                  "starttime": "", "endtime": "", "keyword": "", "orderfield": "1"}
        try:
            if list_method.upper() == "GET":
                # ⚠ 必须把 query **拼进 URL**：服务端会 301 跳 https，若用 httpx 的
                #   params= 参数，重定向后会丢掉 startrecord/endrecord/perpage ⇒ 服务端
                #   返回 totalRecord=0（淄博实测踩坑）。
                r = fetch(f"{url}&{urlencode(params)}", headers={"Referer": ref})
            else:
                r = fetch.post(url, data=params, headers={
                    "Referer": ref, "X-Requested-With": "XMLHttpRequest"})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        t, rows = parse_list(r.text or "")
        if total is None:
            total = t
            print(f"    [{SITE['key']}] {base} sysid={sysid} totalRecord={total}")
        if not rows:
            break
        for row in rows:
            if limit and len(out) >= limit:
                return out
            tid = row["tid"]
            try:
                d = fetch(f"{base}{DETAIL_PATH}?transactId={tid}&sysid={sysid}",
                          headers={"Referer": ref})
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {tid}：{type(e).__name__}（跳过）")
                time.sleep(pause)
                continue
            if getattr(d, "status_code", 0) != 200:
                time.sleep(pause)
                continue
            f = parse_detail(d.text or "")
            answer = (f.get("内容回复") or "").strip()      # 别名归一后的答复键
            if not answer:
                time.sleep(pause)
                continue
            title = f.get("标题") or row["title"]
            body = f.get("内容", "")
            question = title if not body else f"{title}\n{body}"
            out.append({
                "source": SITE["key"],
                "id": str(tid),
                "url": f"{base}{DETAIL_PATH}?transactId={tid}&sysid={sysid}",
                "question": question,
                "answer": answer,
                "asked_at": f.get("提交时间") or row.get("date"),
                "answered_at": f.get("回复日期") or None,
                "dept": f.get("答复单位") or None,
                "channel": "政民互动·信件公开",
                "extra": {
                    "base": base,
                    "sysid": str(sysid),
                    "mail_number": row.get("num"),
                    "handle_status": f.get("处理状态") or None,
                    "answer_kind": "办理答复（jact 信箱，多为办事指引/政策口径）",
                },
            })
            time.sleep(pause)
        if total is not None and page * per_page >= total:
            break
        page += 1
        time.sleep(pause)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
