"""适配器：**山东省·12345 政务服务便民热线·典型留言**（JSON 接口）。

## 站点事实（2026-10-08 实测，证据 recon/xj-xz-sd-gx-qh-hunt.txt 【山东】）
 · 门户 `www.shandong.gov.cn` 的「政民互动 → 12345 热线」`/12345/default.aspx`
   → 典型留言列表 `/12345/szfwz/ListDxal.aspx`；
 · ⚠ **旧结论「山东 ConnectError」是 https 失败所致**：`https://www.shandong.gov.cn`
   SSL 握手失败（`SSLV3_ALERT_HANDSHAKE_FAILURE`），而 **http 明文 200 可达**。
 · 列表/明细均为同一个 ashx 的 POST（layui table 数据源）：
   · 列表 `POST http://www.shandong.gov.cn/12345/szfwz/CommonHandler.ashx`
        body `{opreate: 'szf_wz_base_list', page: N, limit: 20}`
        → JSON `{code:200, count:"71", data:[{id,title,content,sendtime,status,ReplayUnit}]}`
   · 明细 `POST .../CommonHandler.ashx` body `{opreate: 'szf_wz_base_info', id: <id>}`
        → JSON `{success:true, data:{title,content(问题描述),sendtime,dfzt(答复状态),
          lxr,handledate(答复时间),handledepartment(办理单位),handleresult(答复内容),slsj}}`
 · 实测列表 `count=71`；明细 200 且含答复（样例：咨询二级造价师证书领取 → 省住建厅答复）。
 · 另一条线：政民互动「反馈回应」`/col/col100084/index.html`（hanweb，首页 46 条 + 静态明细
   `art_100084_*.html` 含「答复内容」），但其翻页 `dataproxy.jsp` 有 CSRF 防护（返回空），
   仅首页可取 ⇒ 本适配器选 12345 的 JSON 接口（干净、可翻页）。
"""
from __future__ import annotations

import time

SITE = {
    "key": "sd-12345",
    "name": "山东省·12345热线·典型留言",
    "kind": "api",
    "level": "province",
    "entry": "http://www.shandong.gov.cn/12345/szfwz/ListDxal.aspx",
    "status": "ok",
    "note": "12345 ashx JSON（opreate=szf_wz_base_list/base_info），count=71；http 可达（https 握手失败）",
}

BASE = "http://www.shandong.gov.cn"
ASHX = BASE + "/12345/szfwz/CommonHandler.ashx"
REFERER = BASE + "/12345/szfwz/ListDxal.aspx"
PAGE_SIZE = 20
PAUSE = 1.5


def _one(fetch, item: dict) -> dict | None:
    rid = str(item.get("id") or "").strip()
    if not rid:
        return None
    time.sleep(PAUSE)
    r = fetch.post(ASHX, data={"opreate": "szf_wz_base_info", "id": rid},
                   headers={"Referer": REFERER})
    if getattr(r, "status_code", 0) != 200:
        return None
    try:
        d = r.json().get("data") or {}
    except Exception:  # noqa: BLE001
        return None
    answer = (d.get("handleresult") or "").strip()
    if len(answer) < 10:
        return None
    question = (d.get("content") or item.get("content") or "").strip()
    return {
        "source": SITE["key"],
        "id": rid,
        "url": BASE + "/12345/szfwz/DxalView.aspx?id=" + rid,
        "question": question[:400] or (d.get("title") or item.get("title") or ""),
        "answer": answer,
        "asked_at": d.get("sendtime") or item.get("sendtime"),
        "answered_at": d.get("handledate"),
        "dept": (d.get("handledepartment") or item.get("ReplayUnit") or None),
        "channel": "12345热线·典型留言",
        "extra": {
            "title": d.get("title") or item.get("title"),
            "status": d.get("status") or item.get("status"),
            "reply_status": d.get("dfzt"),
            "accept_time": d.get("slsj"),
            "answer_kind": "办理答复（12345 典型留言，多为办事指引）",
        },
    }


def harvest(fetch, *, limit: int | None = None, max_pages: int = 20) -> list[dict]:
    """翻页取「典型留言」列表，逐条取明细拿答复正文。"""
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        r = fetch.post(ASHX, data={"opreate": "szf_wz_base_list",
                                   "page": page, "limit": PAGE_SIZE},
                       headers={"Referer": REFERER})
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            body = r.json()
            items = body.get("data") or []
        except Exception as e:  # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        fresh = [it for it in items if str(it.get("id")) not in seen]
        print(f"    [{SITE['key']}] 第 {page} 页：{len(items)} 条，新增 {len(fresh)}")
        if not fresh:
            break
        for it in fresh:
            if limit and len(out) >= limit:
                return out[:limit]
            seen.add(str(it.get("id")))
            rec = _one(fetch, it)
            if rec:
                out.append(rec)
        if len(items) < PAGE_SIZE:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条（站内自报 71）")
    return out
