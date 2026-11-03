"""探针：拉萨来信选登 API `/lasa-comment/email/findDetailByQuery.do`。

只读，不落盘。目标：确认列表返回结构 + 是否能翻页 + 详情是否含答复。
"""
import json
import os
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

BASE = "https://www.lasa.gov.cn"
API = BASE + "/lasa-comment/email/findDetailByQuery.do"
REFERER = BASE + "/lasa/lxxd/hd_mailbox.shtml"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": REFERER,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


def main() -> int:
    with httpx.Client(timeout=25, headers=HEADERS,
                      follow_redirects=True, trust_env=False, verify=False) as c:
        # 试多种参数组合（不知道接口契约，逐个试）
        tries = [
            ("GET 无参", "get", {}),
            ("GET page=1", "get", {"page": 1, "pageSize": 10}),
            ("POST page=1", "post", {"page": 1, "pageSize": 10}),
            ("POST pageNum", "post", {"pageNum": 1, "pageSize": 10}),
            ("POST 空", "post", {}),
        ]
        for label, method, params in tries:
            try:
                if method == "get":
                    r = c.get(API, params=params)
                else:
                    r = c.post(API, data=params)
            except Exception as e:                                      # noqa: BLE001
                print(f"{label:14s} FAIL {type(e).__name__} {str(e)[:40]}")
                continue
            t = r.text or ""
            print(f"\n{label:14s} HTTP {r.status_code} len={len(t)} ctype={r.headers.get('content-type', '')[:40]}")
            if r.status_code == 200 and t.strip().startswith(("{", "[")):
                try:
                    d = json.loads(t)
                    if isinstance(d, dict):
                        print(f"  顶层键: {list(d.keys())[:12]}")
                        for k in ("data", "rows", "list", "result", "records"):
                            v = d.get(k)
                            if isinstance(v, list) and v:
                                print(f"  {k} 有 {len(v)} 条；首条键: {list(v[0].keys())[:16]}")
                                print(f"    首条样本: {json.dumps(v[0], ensure_ascii=False)[:400]}")
                                break
                            if isinstance(v, dict):
                                print(f"  {k} 是 dict，键: {list(v.keys())[:12]}")
                    break          # 成功一次就够
                except Exception as e:                                  # noqa: BLE001
                    print(f"  JSON 解析失败 {type(e).__name__}: {t[:150]}")
            elif r.status_code == 200:
                print(f"  非 JSON 开头: {t[:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
