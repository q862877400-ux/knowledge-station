"""适配器：**白银市·政民互动（jpaas-jact 变体）**。

## 站点事实（2026-10-08 实测，worker-gansu）
 · 白银门户 `www.baiyin.gov.cn` 的「市长信箱 / 我对书记说 / 县长信箱…」聚合在
   **jpaas-jact-web-server**（与江苏 jact **接口不同**，需自写解析）：
   · 列表 GET `https://www.baiyin.gov.cn/api-gateway/jpaas-jact-web-server/front/
     find-mail-pub-list?platformIid=<pid>&pageNum=<p>&pageSize=<n>`
     → JSON `{"code":0,"data":[…],"count":1889}`。
   · ⚠ **真实分页参数是 `pageNum`/`pageSize`**（实测 `page`/`limit` 被忽略：换页返回
     同一批数据）。`platformIid` = 全部平台（1889）；`platformUid` 是子平台（仅 273）。
   · 列表字段：`iid / title / transactNo / platformName`（「我对市长写信」/「我对书记说」/
     「县长信箱-XX县」）`/ submitDate / handleTime / showHandleTime / stateName`；
     `opinion`/`frontOpinion` 在列表中恒为 null ⇒ **答复正文必须走详情页**。
   · 详情 GET `…/front/mail-pub-detail?iid=<iid>` → HTML「办件公开详细页」，
     标签/值是**相邻两个 `<td>`**（同 jact 结构）：标题 / 办件状态 / 留言时间 / 留言人 /
     留言内容 / 回复时间 / 回复单位 / 办件编号 / 回复内容。
   · `submitDate` / `handleTime` 是**毫秒时间戳**；`showHandleTime` 是日期串。
"""
from __future__ import annotations

import re
import time

LIST_PATH = "/api-gateway/jpaas-jact-web-server/front/find-mail-pub-list"
DETAIL_PATH = "/api-gateway/jpaas-jact-web-server/front/mail-pub-detail"
BASE = "https://www.baiyin.gov.cn"
PLATFORM_IID = "dc0a47c54dce496a9cc6321fac5a973a"
REFERER = "https://www.baiyin.gov.cn/"
PAGE_SIZE = 20
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)

#: 详情页「标签 td → 值 td」的标签 → 规范键。
LABELS = {
    "标题": "标题",
    "留言内容": "内容",
    "留言时间": "提交时间",
    "回复时间": "回复日期",
    "回复内容": "内容回复",
    "回复单位": "答复单位",
    "办件状态": "处理状态",
    "办件编号": "编号",
}

SITE = {
    "key": "gs-baiyin",
    "name": "白银市·政民互动（市长信箱）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.baiyin.gov.cn/zmhd/",
    "status": "ok",
    "note": "jpaas-jact 变体（api-gateway），pageNum/pageSize 分页；答复在详情页；count≈1889",
}


def clean(html: str | None) -> str:
    """去标签 + 压空白（答复正文是 HTML 片段）。"""
    if not html:
        return ""
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()


def ms(ts) -> str | None:
    """毫秒时间戳 → `YYYY-MM-DD HH:MM:SS`；非法/0 返回 None。"""
    try:
        v = int(ts)
    except (TypeError, ValueError):
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v / 1000)) if v > 0 else None


def parse_detail(html: str) -> dict[str, str]:
    """解析「办件公开详细页」→ {规范标签: 值}（label/value 是相邻两个 <td>）。"""
    cells = [clean(x) for x in TD_RE.findall(html or "")]
    out: dict[str, str] = {}
    for i, c in enumerate(cells):
        key = LABELS.get(c)
        if not key or i + 1 >= len(cells):
            continue
        out.setdefault(key, cells[i + 1])
    return out


def _list_page(fetch, page: int, per_page: int) -> dict:
    url = (f"{BASE}{LIST_PATH}?platformIid={PLATFORM_IID}"
           f"&pageNum={page}&pageSize={per_page}")
    r = fetch(url, headers={"Referer": REFERER})
    if getattr(r, "status_code", 0) != 200:
        raise RuntimeError(f"list HTTP {getattr(r, 'status_code', '?')}")
    return r.json()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """翻页取白银政民互动已答复留言（问题 + 答复全文）。

    ⚠ `fetch` 是 harvest.py 注入的 `_Fetcher`（可调用 = GET）。
    """
    out: list[dict] = []
    total = None
    page = 1
    while True:
        try:
            j = _list_page(fetch, page, PAGE_SIZE)
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        rows = j.get("data") or []
        if total is None:
            total = j.get("count")
            print(f"    [{SITE['key']}] count={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            iid = it.get("iid")
            if not iid:
                continue
            try:
                d = fetch(f"{BASE}{DETAIL_PATH}?iid={iid}", headers={"Referer": REFERER})
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {iid}：{type(e).__name__}（跳过）")
                time.sleep(PAUSE)
                continue
            if getattr(d, "status_code", 0) != 200:
                time.sleep(PAUSE)
                continue
            f = parse_detail(d.text or "")
            answer = f.get("内容回复", "").strip()
            if len(answer) < 10:            # 未答复/办理中，跳过
                time.sleep(PAUSE)
                continue
            out.append({
                "source": SITE["key"],
                "id": str(iid),
                "url": f"{BASE}{DETAIL_PATH}?iid={iid}",
                "question": f.get("内容") or clean(it.get("title")),
                "answer": answer,
                "asked_at": ms(it.get("submitDate")) or f.get("提交时间") or None,
                "answered_at": ms(it.get("handleTime")) or f.get("回复日期") or None,
                "dept": f.get("答复单位") or None,
                "channel": "政民互动·留言公示",
                "extra": {
                    "title": clean(it.get("title")),
                    "transact_no": it.get("transactNo"),
                    "platform_name": it.get("platformName"),
                    "handle_status": f.get("处理状态"),
                    "platform": "jpaas-jact",
                },
            })
            time.sleep(PAUSE)
        if total is not None and page * PAGE_SIZE >= int(total):
            break
        page += 1
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
