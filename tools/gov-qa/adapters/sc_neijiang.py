"""适配器：**内江市·互动交流·书记市长网上政务信箱（通信平台 /communication/api-mailbox）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe19/21.txt）
 · 互动栏目：`/njs/hdjl/zmhd.shtml`（政民互动）→ `/njs/mail/mail_list.shtml`（市长信箱）。
 · 前端 `/njs/xhtml/mail/js/zw_mailbox.js` 调 —— 与**绵阳同款「通信平台」**：
   · 列表：`POST /communication/api-mailbox/frontMail/mailList`
       body(JSON): `{pageNum, pageSize, sortMap:{createTime:"desc"},
                     params:{siteId:"a2d1ee6703c7405cadaa15488b9bf5ac"}, sign, timestamp}`
     → `{"status":"success","data":{"total":11010,"pageNum":1,"pageSize":20,"pageTotal":551,
        "rows":[{id, serialNumber, fromName, objectiveType, deptName, title, createTime, …}]}}`
   · 详情：`GET /communication/api-mailbox/frontMail/detail?mailId=<id>&sign=&timestamp=`
     → `{"status":"success","data":{title, content, deptName, createTime, objectiveType,
        replyContents:[{allName, replyContent, …}], serialNumber}}`
   ★ 答复全文在 `replyContents[].replyContent`（HTML）；`content` 是问题正文。
 · ⚠ **接口需签名**：`sign = AES-ECB-Pkcs7-Base64( timestamp + key , key='communication123' )`，
   其中 `key` = 请求体参数按名排序后 `name + JSON.stringify(value)` 拼接（对象用无空格 JSON）。
   由 `zw_mailbox.js` 的 `getKeyVal()` 反推（与绵阳 `hd_common.js` 同源）。
 · 样例：id `4ed10697b0f44824bc071368533a2465`「蜀里安逸购车补贴」→ 经开区经科局答复。
"""
from __future__ import annotations

import base64
import html as _html
import json
import re
import time

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SITE = {
    "key": "sc-neijiang",
    "name": "内江市·互动交流·书记市长网上政务信箱",
    "kind": "api",
    "level": "city",
    "entry": "https://www.neijiang.gov.cn/njs/mail/mail_list.shtml",
    "status": "ok",
    "note": "POST /communication/api-mailbox/frontMail/mailList（列表 total≈11010）+ GET …/detail?mailId=（答复）；需 AES 签名",
}

BASE = "https://www.neijiang.gov.cn"
LIST_URL = BASE + "/communication/api-mailbox/frontMail/mailList"
DETAIL_URL = BASE + "/communication/api-mailbox/frontMail/detail"
SITE_ID = "a2d1ee6703c7405cadaa15488b9bf5ac"
REFERER = SITE["entry"]
PAUSE = 1.0
PAGE_SIZE = 20
_AES_KEY = b"communication123"      # 来自 zw_mailbox.js getKeyVal/Encrypt()

_TAG = re.compile(r"<[^>]+>")


def _enc(val: str) -> str:
    p = padding.PKCS7(128).padder()
    data = p.update(val.encode("utf-8")) + p.finalize()
    e = Cipher(algorithms.AES(_AES_KEY), modes.ECB()).encryptor()
    return base64.b64encode(e.update(data) + e.finalize()).decode()


def _sign(data: dict) -> tuple[str, str]:
    """复刻 getKeyVal：key = 按名排序 name+JSON.stringify(value)，sign=AES(timestamp+key)。"""
    key = ""
    for k in sorted(data.keys()):
        v = data[k]
        if isinstance(v, (dict, list)):
            key += k + json.dumps(v, separators=(",", ":"), ensure_ascii=False)
        else:
            key += k + str(v)
    ts = str(int(time.time() * 1000))
    return _enc(ts + key), ts


def _clean(s) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(s))
    s = re.sub(r"(?i)</p>", "\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    return s.strip()


def harvest(fetch, *, limit: int | None = None, max_pages: int = 600) -> list[dict]:
    """翻页取内江书记市长信箱；列表不含答复，逐条取详情。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        body = {"pageNum": page, "pageSize": PAGE_SIZE,
                "sortMap": {"createTime": "desc"}, "params": {"siteId": SITE_ID}}
        s, ts = _sign(body)
        payload = dict(body, sign=s, timestamp=ts)
        try:
            r = fetch.post(LIST_URL, json=payload, headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            d = (r.json() or {}).get("data") or {}
        except Exception:                                                   # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        rows = d.get("rows") or []
        if total is None:
            total = d.get("total")
            print(f"    [{SITE['key']}] 信件总数 total={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("id") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            q = {"mailId": sid}
            s2, ts2 = _sign(q)
            try:
                dr = fetch(DETAIL_URL, params=dict(q, sign=s2, timestamp=ts2),
                           headers={"Referer": REFERER})
                dd = (dr.json() or {}).get("data") or {}
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                continue
            reps = dd.get("replyContents") or []
            answer = "\n".join(_clean(x.get("replyContent")) for x in reps
                               if isinstance(x, dict) and x.get("replyContent")).strip()
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("title") or dd.get("title") or "").strip()
            content = _clean(dd.get("content"))
            question = title if not content else f"{title}\n{content}"
            dept = (it.get("deptName") or dd.get("deptName")
                    or (reps[0].get("allName") if reps else None))
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": SITE["entry"],
                "question": question,
                "answer": answer,
                "asked_at": (it.get("createTime") or dd.get("createTime") or None),
                "answered_at": None,
                "dept": (dept or "").strip() or None,
                "channel": "互动交流·书记市长网上政务信箱",
                "extra": {
                    "title": title,
                    "objective_type": it.get("objectiveType") or dd.get("objectiveType"),
                    "serial_number": it.get("serialNumber") or dd.get("serialNumber"),
                    "platform": "内江 通信平台 api-mailbox（列表+详情，AES 签名）",
                },
            })
            time.sleep(PAUSE)
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
