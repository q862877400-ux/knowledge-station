r"""适配器：**惠州市·民意直通车（县区信箱 + 局长信箱）** —— 惠州自己的 Spring Boot 平台。

## 站点事实（2026-10-10 实测）

门户 `www.huizhou.gov.cn` 的「政民互动 → 党政领导信箱」实际落在**独立域名**
`www.hzhmsb.cn`（惠州民意直通车，`/portalweb/...`，Spring Boot）。

### 两个接口（**都必须 POST JSON**，表单编码会被拒）

```
列表  POST {BASE}/portalweb/appealPublic/queryList.do
      Content-Type: application/json
      {"callType":"<sqly>","title":"","type":"","pageNum":N,"pageSize":10,"orgId":""}
      → {"code":0,"data":{"pageCount":…,"rowCount":…,
                          "list":[{"id","code","title","type","createTime","endTime"}]}}

明细  POST {BASE}/portalweb/appealPublic/getFormDetail.do
      Content-Type: application/json
      {"formId":"<id>","orderCode":"<code>","linkmanPhone":"","ispublic":"y"}
      → {"code":0,"data":{…}}
```

### 两个坑（都实测踩过）

1. **必须 `Content-Type: application/json`** —— 发 `application/x-www-form-urlencoded`
   会被 Spring 的 `@RequestBody` 回 **415 Unsupported Media Type**
   （`message: Content type '…form-urlencoded…' not supported`）。
2. **参数名不能猜** —— 我第一版猜 `sqly/pageIndex/pageSize`，接口回
   `{"code":0,"desc":"操作成功","data":null}`（**成功但空**，最容易骗过人）。
   真实参数是 `callType/pageNum/orgId`，**从页面 JS 里抠出来的**
   （`recon/probe-endpoint.py` 打不出这个 —— 得看 `show.do` 的 ajax 段）。
   ⇒ **「接口返回成功但 data 为空」= 参数名错，不是没数据。**

### 明细字段（`data` 里）

`orderId`(id) / `title` / `content`(诉求全文) / `approveContent` 与 `handleResult`(答复正文，
两者实测一致) / `createTime` / `endTime` / `type`(咨询·建议·投诉) / `state`(处理状态)

### 存量

`callType=29` 县区信箱 `rowCount=4204`；`callType=30` 局长信箱 **`rowCount=20144`**。
⇒ 约 **2.4 万条**，**明细必须逐条取**（列表不含答复）⇒ 慢，务必用 `limit` 分块。
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

HOST = "https://www.hzhmsb.cn"
BASE = HOST
LIST_API = f"{BASE}/portalweb/appealPublic/queryList.do"
DETAIL_API = f"{BASE}/portalweb/appealPublic/getFormDetail.do"
PAGE_API = f"{BASE}/portalweb/appealPublic/show.do"
PAGE_SIZE = 10
PAUSE = 0.4
TAG_RE = re.compile(r"<[^>]+>")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

#: callType → 信箱名（`show.do?sqly=` 的取值）
CALL_TYPES = (("30", "局长信箱"), ("29", "县区信箱"))

SITE = {
    "key": "gd-huizhou",
    "name": "惠州市·民意直通车（党政领导信箱）",
    "kind": "api",
    "level": "city",
    "entry": f"{BASE}/portalweb/appealPublic/show.do?sqly=30",
    "status": "ok",
    "note": "hzhmsb.cn Spring Boot；queryList.do + getFormDetail.do 均须 POST JSON；"
            "callType 30=局长信箱(20144) / 29=县区信箱(4204)",
}


def clean(s: str | None) -> str:
    """去标签 + 还原实体 + 压空白（答复正文可能含 HTML）。"""
    import html as _h
    if not s:
        return ""
    return re.sub(r"\s+", " ", _h.unescape(TAG_RE.sub(" ", str(s)))).strip()


def existing_ids(site_key: str) -> set:
    ids: set = set()
    try:
        for p in DATA_DIR.glob(f"{site_key}-*.jsonl"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    mid = str(json.loads(line).get("id") or "").strip()
                    if mid:
                        ids.add(mid)
    except Exception:                                                     # noqa: BLE001
        pass
    return ids


def _post_json(fetch, url: str, payload: dict, referer: str):
    return fetch.post(url, content=json.dumps(payload), headers={
        "Content-Type": "application/json;charset=utf-8",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": referer,
    })


def harvest(fetch, *, limit: int | None = None, pause: float = PAUSE,
            skip_ids: set | None = None) -> list[dict]:
    """翻列表 + 逐条取明细，返回统一记录。`limit` = 本轮**新增**条数上限。"""
    if skip_ids is None:
        skip_ids = existing_ids(SITE["key"])
    if skip_ids:
        print(f"    [{SITE['key']}] 已落盘 {len(skip_ids)} 条，本轮跳过其明细")
    out: list[dict] = []
    skipped = 0
    tried = 0
    for call_type, label in CALL_TYPES:
        if limit and len(out) >= limit:
            break
        ref = f"{PAGE_API}?sqly={call_type}"
        fetch(ref)                                  # 建会话
        page, total = 1, None
        while True:
            if limit and len(out) >= limit:
                break
            try:
                r = _post_json(fetch, LIST_API, {
                    "callType": call_type, "title": "", "type": "",
                    "pageNum": page, "pageSize": PAGE_SIZE, "orgId": ""}, ref)
            except Exception as e:                                        # noqa: BLE001
                print(f"    [{SITE['key']}] {label} 第 {page} 页 {type(e).__name__}（停）")
                break
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] {label} 第 {page} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）")
                break
            try:
                d = (r.json() or {}).get("data") or {}
            except Exception as e:                                        # noqa: BLE001
                print(f"    [{SITE['key']}] {label} 第 {page} 页解析失败 {type(e).__name__}（停）")
                break
            rows = d.get("list") or []
            if total is None:
                total = d.get("rowCount")
                print(f"    [{SITE['key']}] {label} rowCount={total}")
            if not rows:
                break
            for it in rows:
                if limit and len(out) >= limit:
                    break
                fid, code = str(it.get("id") or ""), str(it.get("code") or "")
                if not fid:
                    continue
                if fid in skip_ids:
                    skipped += 1
                    continue
                tried += 1
                # ★ 2026-10-10 加：明细是本引擎最慢的一步（每条一次 POST + pause），
                #   而它**原来没有任何日志** ⇒ 跑起来像「卡死」。
                #   （同一个坑在 `gs_tianshui` 上踩过，见 `AUTO_HANDOFF.md` §15）
                if tried % 50 == 0:
                    print(f"    [{SITE['key']}] {label} 明细进度 {tried}，已收 {len(out)} 条",
                          flush=True)
                time.sleep(pause)
                try:
                    dr = _post_json(fetch, DETAIL_API, {
                        "formId": fid, "orderCode": code,
                        "linkmanPhone": "", "ispublic": "y"},
                        f"{BASE}/portalweb/appealPublic/toDetail"
                        f"?formId={fid}&code={code}&sqly={call_type}")
                    det = (dr.json() or {}).get("data") or {}
                except Exception as e:                                    # noqa: BLE001
                    print(f"    [{SITE['key']}] 明细 {fid[:8]} {type(e).__name__}（跳过）")
                    continue
                answer = clean(det.get("approveContent")) or clean(det.get("handleResult"))
                if len(answer) < 10:
                    continue                       # 未答复/办理中
                skip_ids.add(fid)
                content = clean(det.get("content"))
                # `handleOrgName` 在 getFormDetail 的响应里**不存在**（JS 里引用了但没返回）
                # ⇒ 从正文头部抠「写信部门：XXX」（`content` 前几行是「诉求来源/写信部门/诉求类型/…」）
                dept = clean(det.get("handleOrgName")) or ""
                if not dept:
                    m = re.search(r"写信部门[：:]\s*([^\s\r\n]+)", content)
                    if m:
                        dept = m.group(1)
                out.append({
                    "source": SITE["key"],
                    "id": fid,
                    "url": f"{BASE}/portalweb/appealPublic/toDetail"
                           f"?formId={fid}&code={code}&sqly={call_type}",
                    "question": (content
                                 or clean(det.get("title")) or clean(it.get("title"))),
                    "answer": answer,
                    "asked_at": det.get("createTime") or it.get("createTime"),
                    "answered_at": det.get("endTime") or it.get("endTime"),
                    "dept": dept,
                    "channel": f"民意直通车·{label}",
                    "extra": {
                        "title": clean(det.get("title")) or clean(it.get("title")),
                        "order_code": code,
                        "msg_type": det.get("type") or it.get("type"),
                        "state": det.get("state"),
                        "call_type": call_type,
                        "platform": "hzhmsb",
                    },
                })
            if total is not None and page * PAGE_SIZE >= int(total):
                break
            page += 1
            time.sleep(pause)
    print(f"    [{SITE['key']}] 收 {len(out)} 条"
          + (f"（跳过已落盘 {skipped} 条）" if skipped else ""))
    return out
