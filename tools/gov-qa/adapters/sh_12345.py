"""适配器：**上海市 · 12345 市民服务热线「诉求公开」**（办结诉求公示）。

## 形态判断（2026-10-08 实探，证据 recon/sh-zj-hunt.txt 【上海】）
上海市人民政府门户 `www.sh.gov.cn` 的「政民互动」页 `/zmhd/` 可达（33KB），
其中「市委、市政府网上信访受理（投诉）中心」明细指向 `wsxf.sh.gov.cn`（本机 **不可达**：
http=RemoteProtocolError、https=ConnectError，见证据）。
真正能采的是门户挂的 **12345 网上受理平台** `www.sh12345.gov.cn`（Vue SPA，`/demands` 路由=「诉求公开」）。

## 接口（实测 200）
 · 列表：`POST https://www.sh12345.gov.cn/appealPublicService/allAppealPublic?startPage=<n>`
     固定每页 **15 条**（响应里带 `count` 总数；实测 count=7248）。
     必须打 **https**：http 会 302 → https，跟随重定向会把 POST 变成 GET 而报 500。
 · 明细：`GET .../appealPublicService/appealDetail/<rpid>`（列表已带全文，通常不必调）。
 · ★ 响应 `data` 是 **AES-128-ECB(hex)** 密文（前端 `pubInfo-*.js` → `IR/PR`）：
     密钥 = `Ir[4]+Ir[1]+Ir[6]+Ir[2]+Ir[7]+Ir[5]+Ir[0]+Ir[3]`，`Ir=["S5","UC","Gm","IF","ER","Xx","4t","rq"]`
        ⇒ `"ERUC4tGmrqXxS5IF"`（16B），ECB/PKCS7，密文按 **hex** 编码。
     解密后 `{"startPage","count","list":[{relTitle,content(问题),reply(答复),struName(答复单位),
     startTime(提问),createTime(办结),rpid}]}`。
 · 实测样例：家中无电 → 电力热线答复（含《配网故障抢修管理规定》）；驾驶员审验 → 市公安局答复。

## 依赖
AES 解密用 `cryptography`（本仓 venv 已随 pdfminer.six 装入；缺失时给出明确报错）。
"""
from __future__ import annotations

import json
import time

SITE = {
    "key": "sh-12345",
    "name": "上海市·12345热线诉求公开",
    "kind": "api",
    "level": "province",
    "entry": "https://www.sh12345.gov.cn/demands",
    "status": "ok",
    "note": "POST allAppealPublic?startPage=N（AES-ECB 密文，需解密）；实测 count=7248",
}

BASE = "https://www.sh12345.gov.cn"
LIST_URL = BASE + "/appealPublicService/allAppealPublic"
DETAIL_URL = BASE + "/appealPublicService/appealDetail/"
AES_KEY = b"ERUC4tGmrqXxS5IF"
PAGE_SIZE = 15
PAUSE = 1.5
HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "source-client": "wz",
    "Referer": BASE + "/demands",
    "Origin": BASE,
}


def _decrypt_hex(hexstr: str) -> str:
    """AES-128-ECB(hex) → 明文（PKCS7 去填充）。"""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    ct = bytes.fromhex(hexstr)
    dec = Cipher(algorithms.AES(AES_KEY), modes.ECB()).decryptor()
    pt = dec.update(ct) + dec.finalize()
    return pt[:-pt[-1]].decode("utf-8") if pt else ""


def _page(fetch, page: int) -> dict:
    """取第 page 页并解密 → {count, list}；异常/空返回 {}。"""
    r = fetch.post(LIST_URL, params={"startPage": page}, headers=HEADERS)
    if getattr(r, "status_code", 0) != 200:
        raise RuntimeError(f"HTTP {getattr(r, 'status_code', '?')}")
    data = (r.json() or {}).get("data")
    if not data:
        return {}
    if isinstance(data, str):
        return json.loads(_decrypt_hex(data))
    return data if isinstance(data, dict) else {}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 600) -> list[dict]:
    """按 startPage 翻页取「诉求公开」（列表已带问题+答复全文，无需再抓明细）。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            return out[:limit]
        try:
            obj = _page(fetch, page)
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页：{type(e).__name__} {e}（停）")
            break
        rows = obj.get("list") or []
        if total is None:
            total = obj.get("count")
            print(f"    [{SITE['key']}] 诉求公开总数 count={total}")
        if not rows:
            break
        fresh = 0
        for it in rows:
            if limit and len(out) >= limit:
                return out[:limit]
            rpid = str(it.get("rpid") or "").strip()
            if not rpid or rpid in seen:
                continue
            seen.add(rpid)
            content = (it.get("content") or "").strip()
            answer = (it.get("reply") or "").strip()
            if len(answer) < 10:
                continue
            title = (it.get("relTitle") or "").strip()
            out.append({
                "source": SITE["key"],
                "id": rpid,
                "url": f"{BASE}/demandsText?rpid={rpid}",
                "question": content or title,
                "answer": answer,
                "asked_at": it.get("startTime") or None,
                "answered_at": it.get("createTime") or None,
                "dept": (it.get("struName") or "").strip() or None,
                "channel": "12345诉求公开",
                "extra": {
                    "title": title,
                    "answer_kind": "办理答复（12345办结诉求公示）",
                    "detail_url": DETAIL_URL + rpid,
                },
            })
            fresh += 1
        print(f"    [{SITE['key']}] 第 {page} 页：{len(rows)} 条，新增 {fresh}")
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
