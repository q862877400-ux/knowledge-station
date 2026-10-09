"""山东地市 **jpaas-jact 网关** 基座（济南/烟台同款）。

## 平台事实（2026-10-08 实测）
山东部分地市把 jact 挂在统一网关下（与江苏 `_jact_common.py` 的 `/jact/front/` 不同）：
 · **济南** `http://www.jinan.gov.cn/api-gateway/jpaas-jact-web-server/front`
     platformUid=HTMi0SM6aXpdnEJDZH931，submitTargetIds=<47 个部门 id>
 · **烟台** `http://www.yantai.gov.cn/api-gateway/jpaas-jact-web-server/front`
     platformUid=TBCxiImkDT42EEoX3QnkW，submitTargetIds 为空
 · 两者都由门户内联的 `.../default-template/page.js`（layui）驱动，接口同名：
   · 列表 `GET {base}/find-mail-pub-list`
       `?pageNum=N&pageSize=M&platformUid=<pid>&submitTargetIds=<ids>&govOpen=<g>`
       → JSON `{"code":0,"data":[{"iid","title","transactNo","submitDate"(ms),…}],"count":N}`
   · 明细 `GET {base}/mail-pub-detail?iid=<iid>` → HTML 表格（标签/值相邻 `<td>`）
       标签：`标 题： / 内 容： / 提交时间： / 答复部门： / 答复日期： / 答复内容：`

## ⚠ 关键坑：`govOpen`
济南 `govOpen=1` 只回 **250** 条，留空回 **6654** 条；烟台 `govOpen=1` 回 **0**，留空回 **101152**。
⇒ **默认不传 govOpen**（本基座 `gov_open=""`），让服务端回全量，未答复条目由 `答复内容` 过滤掉。
"""
from __future__ import annotations

import html as _html
import re
import time

TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
LABELS = ("标题", "内容", "提交时间", "答复部门", "答复日期", "答复内容", "答复附件")


def _clean(s: str | None) -> str:
    if not s:
        return ""
    return _html.unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", s))).strip()


def _detail(fetch, base: str, referer: str, iid: str) -> dict:
    r = fetch(f"{base}/mail-pub-detail?iid={iid}", headers={"Referer": referer})
    if getattr(r, "status_code", 0) != 200:
        return {}
    cells = [_clean(x) for x in TD_RE.findall(r.text or "")]
    out: dict[str, str] = {}
    for i, c in enumerate(cells):
        key = c.replace(" ", "").rstrip("：:")     # 「标 题：」→「标题」；值保持原样
        if key in LABELS and i + 1 < len(cells):
            out[key] = cells[i + 1]
    return out


def _env_page_from() -> int:
    """起始页号：环境变量 `GOVQA_PAGE_FROM`（把超长源分块采）。"""
    import os
    try:
        return max(1, int(os.environ.get("GOVQA_PAGE_FROM", "1")))
    except ValueError:
        return 1


def harvest_jact_gateway(fetch, *, SITE: dict, base: str, platform_uid: str,
                         submit_target_ids: str = "", gov_open: str = "",
                         page_size: int = 19, referer: str | None = None,
                         limit: int | None = None, pause: float = 1.5,
                         max_pages: int = 400,
                         page_from: int | None = None) -> list[dict]:
    """采某市 jpaas-jact 网关信箱（问题 + 答复全文）。

    `page_from` = 起始页号（默认读环境变量 `GOVQA_PAGE_FROM`，再默认 1）。
    ⚠ 存在的意义：`harvest.py` **只在跑完时落盘**，烟台 10 万条跑不完就被 timeout 杀掉 ⇒ **零产出**。
    分块跑法（pageSize=19 ⇒ 2000 条 ≈ 106 页）：
        GOVQA_PAGE_FROM=1   ... --limit 2000
        GOVQA_PAGE_FROM=107 ... --limit 2000
    """
    out: list[dict] = []
    seen: set[str] = set()
    ref = referer or SITE.get("entry", base)
    total = None
    start = page_from if page_from is not None else _env_page_from()
    for page in range(start, start + max_pages):
        if limit and len(out) >= limit:
            break
        url = (f"{base}/find-mail-pub-list?pageNum={page}&pageSize={page_size}"
               f"&platformUid={platform_uid}&submitTargetIds={submit_target_ids}"
               f"&govOpen={gov_open}")
        r = fetch(url, headers={"Referer": ref})
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            body = r.json()
            items = body.get("data") or []
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        if total is None:
            total = body.get("count")
            print(f"    [{SITE['key']}] {base} count={total}")
        fresh = [it for it in items if str(it.get("iid")) not in seen]
        print(f"    [{SITE['key']}] 第 {page} 页：{len(items)} 条，新增 {len(fresh)}")
        if not fresh:
            break
        for it in fresh:
            if limit and len(out) >= limit:
                return out
            iid = str(it.get("iid") or "")
            if not iid:
                continue
            seen.add(iid)
            time.sleep(pause)
            f = _detail(fetch, base, ref, iid)
            answer = f.get("答复内容", "").strip()
            if not answer:
                continue
            title = f.get("标题") or it.get("title") or ""
            cont = f.get("内容", "")
            question = title if not cont else f"{title}\n{cont}"
            out.append({
                "source": SITE["key"],
                "id": iid,
                "url": f"{base}/mail-pub-detail?iid={iid}",
                "question": question,
                "answer": answer,
                "asked_at": f.get("提交时间") or None,
                "answered_at": f.get("答复日期") or None,
                "dept": f.get("答复部门") or it.get("submitTargetName") or None,
                "channel": SITE.get("channel", "互动交流·回应关切"),
                "extra": {
                    "transact_no": it.get("transactNo"),
                    "platform_uid": platform_uid,
                    "answer_kind": "办理答复（jpaas-jact 网关，多为办事指引/政策口径）",
                },
            })
        if len(items) < page_size:
            break
        time.sleep(pause)
    print(f"    [{SITE['key']}] 收 {len(out)} 条（站内自报 {total}）")
    return out
