"""找 `ipUrl` 的定义（在 head.js 或页面内联），并**直接试调**拉萨来信列表 API。"""
import json
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

B = "https://www.lasa.gov.cn"
H = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36"),
     "Referer": B + "/lasa/lxxd/hd_mailbox.shtml",
     "Accept-Language": "zh-CN,zh;q=0.9"}

SELF_DEPT = "d548f0a35d60483c8c67bbb86f7a5723"


def main() -> int:
    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        # ① 找 ipUrl
        ip_url = None
        for src in ("/lasa/xhtml/js/head.js", "/lasa/lxxd/hd_mailbox.shtml"):
            try:
                t = c.get(B + src).text or ""
            except Exception:                                           # noqa: BLE001
                continue
            for m in re.finditer(r"ipUrl\s*[:=]\s*[\"']([^\"']+)[\"']", t):
                ip_url = m.group(1)
                print(f"ipUrl 在 {src} 找到: {ip_url}")
                break
            if ip_url:
                break
        if not ip_url:
            # 兜底猜测（同域）
            ip_url = ""
            print("ipUrl 未找到，按同域试")

        # ② 直接试调
        for base in ([ip_url] if ip_url else []) + ["", B]:
            url = (base or "") + "/communication/api-mailbox/frontMail/mailList"
            if not url.startswith("http"):
                url = B + url
            body = {"pageNum": 1, "pageSize": 10,
                    "sortMap": {"createTime": "desc"},
                    "params": {"phone": "", "searchCode": "", "selfDeptId": SELF_DEPT}}
            try:
                r = c.post(url, json=body,
                           headers={"Content-Type": "application/json",
                                    "X-Requested-With": "XMLHttpRequest"})
            except Exception as e:                                      # noqa: BLE001
                print(f"POST {url}\n  FAIL {type(e).__name__} {str(e)[:50]}")
                continue
            t = r.text or ""
            print(f"\nPOST {url}\n  HTTP {r.status_code} len={len(t)}")
            if t.strip().startswith("{"):
                try:
                    d = json.loads(t)
                    print(f"  status={d.get('status')}")
                    data = d.get("data") or {}
                    if isinstance(data, dict):
                        print(f"  data 键: {list(data.keys())[:10]}")
                        rows = data.get("rows") or []
                        print(f"  rows: {len(rows)} 条")
                        if rows:
                            print(f"  首条键: {list(rows[0].keys())[:20]}")
                            print(f"  首条样本: {json.dumps(rows[0], ensure_ascii=False)[:450]}")
                            return 0
                    elif isinstance(data, list):
                        print(f"  data 是 list: {len(data)} 条")
                        if data:
                            print(f"  首条: {json.dumps(data[0], ensure_ascii=False)[:400]}")
                            return 0
                except Exception as e:                                  # noqa: BLE001
                    print(f"  JSON 失败 {type(e).__name__}: {t[:180]}")
            else:
                print(f"  非 JSON: {t[:180]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
