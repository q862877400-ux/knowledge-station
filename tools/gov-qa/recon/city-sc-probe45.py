"""city-sc-probe45：四川政务服务网「政民互动」——全省 21 市州 areaCode 总量普查。"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
API = "https://www.sczwfw.gov.cn/cns-bmfw-websdt/rest/cnspublic/scwebsitecaseinfoaction/"
LIST_URL = API + "getInteractCaseInfoListByCondition"
CITIES = [
    ("成都市", "510100000000"), ("自贡市", "510300000000"), ("攀枝花市", "510400000000"),
    ("泸州市", "510500000000"), ("德阳市", "510600000000"), ("绵阳市", "510700000000"),
    ("广元市", "510800000000"), ("遂宁市", "510900000000"), ("内江市", "511000000000"),
    ("乐山市", "511100000000"), ("南充市", "511300000000"), ("眉山市", "511400000000"),
    ("宜宾市", "511500000000"), ("广安市", "511600000000"), ("达州市", "511700000000"),
    ("雅安市", "511800000000"), ("巴中市", "511900000000"), ("资阳市", "512000000000"),
    ("阿坝州", "513200000000"), ("甘孜州", "513300000000"), ("凉山州", "513400000000"),
]


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def main():
    OUT.write_text("", encoding="utf-8")
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Content-Type": "json/application",
                      "Referer": "https://www.sczwfw.gov.cn/"})
    w("城市 | areaCode | 咨询 | 建议 | 投诉 | 合计")
    grand = 0
    for name, code in CITIES:
        row = []
        tot = 0
        for rt in ("10", "15", "20"):
            body = {"pageSize": 1, "currentPageIndex": 1, "title": "", "rqstType": rt,
                    "webrqsttime": "", "areaCode": code, "iszwfw": "1"}
            try:
                r = s.post(LIST_URL, data=json.dumps(body), timeout=20)
                j = r.json()
                t = int((j.get("custom") or {}).get("total") or 0)
            except Exception:  # noqa: BLE001
                t = -1
            row.append(t)
            if t > 0:
                tot += t
        grand += tot
        w(f"{name} | {code} | {row[0]} | {row[1]} | {row[2]} | {tot}")
    w(f"—— 全省合计 ≈ {grand} 条 ——")


if __name__ == "__main__":
    main()
