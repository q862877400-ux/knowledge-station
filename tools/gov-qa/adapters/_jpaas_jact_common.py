"""jpaas-jact 平台（`api-gateway/jpaas-jact-web-server`）· 共用采集引擎——**多市共用**。

## 平台识别（2026-10-08 worker-gansu）
同一套「jpaas-jact 政务网关」在多个地市门户出现，**接口同构**：
 · 甘肃白银 `www.baiyin.gov.cn`（`platformIid`，count=1889）
 · 甘肃临夏 `www.linxia.gov.cn`（`platformUid`，书记 46 / 州长 39）
 · 山东济南/烟台/济宁/威海/日照/滨州（见 sd-* 适配器，另属他对话）
⇒ 加市只需补 (base, platform_key, platform_value)。

## 接口
```
列表 GET {base}/api-gateway/jpaas-jact-web-server/front/find-mail-pub-list
        ?{platform_key}={platform_value}&pageNum=<p>&pageSize=<n>   (可加 type/orderType)
     → JSON {"code":0,"data":[…],"count":N}
     ⚠ 分页参数是 **pageNum/pageSize**（实测 `page`/`limit` 被忽略）
     ⚠ `platformIid`=全平台聚合；`platformUid`=单栏目（如临夏书记/州长各一个）
详情 GET {base}/api-gateway/jpaas-jact-web-server/interface/transact/find-transact-detail
        ?transactId=<iid>
     → JSON {"data":{"transact":{…},"transactOpinion":[{handlerName,opinion,handleTime}…]}}
     · 问题正文在 `transact.transactData[]` 里 `fieldName=="content"`（标题 fieldName=="title"）
     · 答复在 `transactOpinion[]`：**取最后一个非占位项**（临夏首项常为「申请流程」占位）
```
⚠ `transactData` 含 `mphone`(手机号) / `cardNo`(证件号) 等**个人隐私字段** —— 本引擎
   **只取 title/content**，其余一律不入库。
"""
from __future__ import annotations

import re
import time

LIST_PATH = "/api-gateway/jpaas-jact-web-server/front/find-mail-pub-list"
DETAIL_PATH = "/api-gateway/jpaas-jact-web-server/interface/transact/find-transact-detail"
PAUSE = 1.5
PAGE_SIZE = 20
TAG_RE = re.compile(r"<[^>]+>")
#: 「无实质答复」占位（临夏首条常为「申请流程」；其余为通用空值）
_NO_ANSWER = {"", "无", "无。", "暂无", "-", "（无）", "(无)", "申请流程"}


def clean(html: str | None) -> str:
    """去标签 + 压空白（答复正文可能是 HTML 片段）。"""
    if not html:
        return ""
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()


def _field(detail: dict, name: str) -> str:
    """从 `transact.transactData[]` 里按 fieldName 取值。"""
    for f in ((detail.get("transact") or {}).get("transactData") or []):
        if (f or {}).get("fieldName") == name:
            return str((f or {}).get("fieldValue") or "")
    return ""


def _answer(detail: dict) -> tuple[str, str | None, str | None]:
    """取答复：`transactOpinion[]` 中**最后一个非占位项** → (正文, 单位, 时间)。"""
    ops = detail.get("transactOpinion") or []
    chosen = None
    for op in ops:
        txt = clean((op or {}).get("opinion"))
        if txt and txt not in _NO_ANSWER and len(txt) >= 10:
            chosen = op
    if not chosen:
        return "", None, None
    return (clean(chosen.get("opinion")), chosen.get("handlerName"),
            chosen.get("handleTime"))


def _list_page(fetch, *, base: str, platform_key: str, platform_value: str,
               page: int, per_page: int, referer: str,
               extra: dict | None) -> dict:
    params = {platform_key: platform_value, "pageNum": page, "pageSize": per_page}
    if extra:
        params.update(extra)
    r = fetch(f"{base}{LIST_PATH}", params=params, headers={"Referer": referer})
    if getattr(r, "status_code", 0) != 200:
        raise RuntimeError(f"list HTTP {getattr(r, 'status_code', '?')}")
    return r.json()


def harvest_jpaas(fetch, *, SITE: dict, base: str, platform_key: str,
                  platform_value: str, referer: str, page_size: int = PAGE_SIZE,
                  limit: int | None = None, list_extra: dict | None = None,
                  pause: float = PAUSE) -> list[dict]:
    """翻页取某 jpaas-jact 栏目的已答复留言（问题 + 答复原文）。

    ⚠ `fetch` 是 harvest.py 注入的 `_Fetcher`（可调用 = GET）。
    """
    out: list[dict] = []
    total = None
    page = 1
    while True:
        try:
            j = _list_page(fetch, base=base, platform_key=platform_key,
                           platform_value=platform_value, page=page,
                           per_page=page_size, referer=referer, extra=list_extra)
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
                d = fetch(f"{base}{DETAIL_PATH}", params={"transactId": iid},
                          headers={"Referer": referer})
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {iid}：{type(e).__name__}（跳过）")
                time.sleep(pause)
                continue
            if getattr(d, "status_code", 0) != 200:
                time.sleep(pause)
                continue
            try:
                detail = (d.json() or {}).get("data") or {}
            except Exception:                                               # noqa: BLE001
                time.sleep(pause)
                continue
            answer, dept, answered = _answer(detail)
            if len(answer) < 10:            # 未答复/办理中，跳过
                time.sleep(pause)
                continue
            title = clean(_field(detail, "title")) or clean(it.get("title"))
            content = clean(_field(detail, "content"))
            question = title if not content else f"{title}\n{content}"
            tr = detail.get("transact") or {}
            out.append({
                "source": SITE["key"],
                "id": str(iid),
                "url": f"{base}{DETAIL_PATH}?transactId={iid}",
                "question": question,
                "answer": answer,
                "asked_at": tr.get("submitDate") or it.get("submitDate") or None,
                "answered_at": answered,
                "dept": dept,
                "channel": clean(it.get("platformName")) or "政民互动·留言公示",
                "extra": {
                    "title": title,
                    "transact_no": tr.get("transactNo") or it.get("transactNo"),
                    "platform_name": it.get("platformName"),
                    "platform": "jpaas-jact",
                },
            })
            time.sleep(pause)
        if total is not None and page * page_size >= int(total):
            break
        page += 1
        time.sleep(pause)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
