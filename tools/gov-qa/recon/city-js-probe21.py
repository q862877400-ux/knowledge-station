"""stage21：南通 messageController/getMessageByCondition.do 实测（市长信箱列表）。"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0"})
    url = "https://www.nantong.gov.cn/truecms/messageController/getMessageByCondition.do"
    ref = {"Referer": "https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html"}
    for lmxx in ("sgkxj", "bumxx"):
        for page in (1, 2):
            data = {"lmxx": lmxx, "lmid": "b88fd122-d5a3-406e-8388-80b4b55b196b",
                    "isGetChild": "1", "pagenum": page, "pagesize": 13, "name": "", "type": ""}
            try:
                rr = c.post(url, data=data, headers=ref, timeout=30)
                try:
                    d = rr.json()
                except Exception:  # noqa: BLE001
                    w(f"  {lmxx} p{page} -> {rr.status_code} non-json {rr.text[:120]!r}")
                    continue
                w(f"  {lmxx} p{page} status={rr.status_code} topkeys={list(d.keys())}")
                # 找列表字段
                for k, v in d.items():
                    if isinstance(v, list) and v:
                        w(f"    {k}: list n={len(v)} itemkeys={list(v[0].keys())}")
                        w("    item0=" + json.dumps(v[0], ensure_ascii=False)[:800])
                    elif isinstance(v, dict):
                        w(f"    {k}: dict keys={list(v.keys())}")
            except Exception as e:  # noqa: BLE001
                w(f"  {lmxx} p{page} -> {type(e).__name__} {str(e)[:70]}")


if __name__ == "__main__":
    main()
