"""city-sc-probe44：四川政务服务网「政民互动」平台（可覆盖成都及全省，绕过瑞数）。"""
import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
ROOT = "https://www.sczwfw.gov.cn/cns-bmfw-websdt/rest/cnspublic/scwebsitecaseinfoaction/"
PAGE = "https://www.sczwfw.gov.cn/cns-bmfw-websdt/pages/website/scwebsit/pages/peogovinteract/"


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def dec(r):
    try:
        return r.content.decode("utf-8")
    except Exception:  # noqa: BLE001
        return r.text


def main():
    OUT.write_text("", encoding="utf-8")
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Content-Type": "application/json",
                      "Referer": "https://www.sczwfw.gov.cn/"})

    w("===== getInteractCaseInfoList（成都 510100000000，rqstType 10/15/20）=====")
    for rt in ("10", "15", "20"):
        r = s.post(ROOT + "getInteractCaseInfoList",
                   data=json.dumps({"rqstType": rt, "areaCode": "510100000000", "htmlSource": "zwfw"}),
                   timeout=20)
        try:
            j = json.loads(dec(r))
            info = (j.get("custom") or {}).get("infoList") or []
            rec = (j.get("custom") or {}).get("caseRecord") or {}
            w(f"  rqstType={rt} -> {r.status_code} infoList={len(info)} caseRecord={rec}")
            if info:
                w("     " + json.dumps(info[0], ensure_ascii=False)[:250])
        except Exception as e:  # noqa: BLE001
            w(f"  rqstType={rt} -> {r.status_code} 解析失败 {e}: {dec(r)[:200]}")

    w("\n===== getInteractCaseInfoListByCondition（分页全量）=====")
    for body in [
        {"rqstType": "10", "areaCode": "510100000000", "htmlSource": "zwfw", "pageNo": 1, "pageSize": 10},
        {"rqstType": "10", "areaCode": "510100000000", "page": 1, "limit": 10},
        {"rqstType": "10", "areaCode": "510100000000", "pageIndex": 1, "pageSize": 10},
        {"rqstType": "10", "areaCode": "510100000000", "current": 1, "size": 10},
    ]:
        r = s.post(ROOT + "getInteractCaseInfoListByCondition", data=json.dumps(body), timeout=20)
        t = dec(r)
        try:
            j = json.loads(t)
            cust = j.get("custom") or {}
            w(f"  {json.dumps(body, ensure_ascii=False)[:80]} -> {r.status_code} custom keys={list(cust.keys())}")
            w("     " + json.dumps(cust, ensure_ascii=False)[:400])
        except Exception:  # noqa: BLE001
            w(f"  {json.dumps(body, ensure_ascii=False)[:80]} -> {r.status_code} len={len(t)} {t[:150]}")
        break

    w("\n===== 详情页 wantconsultdetail?cguid=… =====")
    r = s.post(ROOT + "getInteractCaseInfoList",
               data=json.dumps({"rqstType": "10", "areaCode": "510100000000", "htmlSource": "zwfw"}),
               timeout=20)
    j = json.loads(dec(r))
    info = (j.get("custom") or {}).get("infoList") or []
    if info:
        hu = info[0]["handleurl"]
        u = PAGE + hu
        rr = requests.get(u, timeout=25, headers={"User-Agent": UA,
                                                  "Referer": PAGE + "interact.html?areaCode=510100000000"})
        t = dec(rr)
        w(f"  {hu} -> {rr.status_code} len={len(t)}")
        for m in re.finditer(r'(?s)<script[^>]*>(.*?)</script>', t):
            sc = m.group(1).strip()
            if any(k in sc for k in ("ajax", "url:", "cguid", "detail", "Config")):
                w("  SC " + re.sub(r"\s+", " ", sc)[:600])
                break
        b = re.sub(r"(?s)<script.*?</script>", " ", t)
        b = re.sub(r"(?s)<style.*?</style>", " ", b)
        w("  body: " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b))[:600])


if __name__ == "__main__":
    main()
