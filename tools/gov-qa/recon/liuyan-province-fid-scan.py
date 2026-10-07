"""验证「省级版块 fid 连续编号」假设：试 fid=541..550，看返回哪个省。

已知：北京市委书记=539、市长=540（省级市）；北京的区=736~760。
若省级按行政区划顺序编号，则 541+ 应为天津、河北、山西…（各 2 个：书记/省长）。
命中即可批量建「省 → fid」表，全国覆盖从"等时间流"变成"逐省定向"。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import BASE, _envelope, _headers  # noqa: E402

FIDS = [str(n) for n in range(541, 556)]


def main() -> int:
    import httpx

    rows_out = []
    with httpx.Client(trust_env=False, timeout=20) as c:
        for fid in FIDS:
            path = "/v1/threads/list/df"
            param = {"fid": fid, "showUnAnswer": 0, "lastItem": "",
                     "position": 1, "rows": 3, "orderType": 2}
            rec = {"fid": fid}
            try:
                r = c.post(BASE + path, content=_envelope(path, param),
                           headers=_headers(f"{BASE}/threads/list?fid={fid}"))
                rec["status"] = r.status_code
                if "json" in r.headers.get("content-type", ""):
                    d = (r.json().get("resultData") or {})
                    data = d.get("data") or []
                    rec["n"] = len(data)
                    rec["total"] = d.get("total")
                    if data:
                        rec["forum"] = data[0].get("forumName")
                        rec["p"] = data[0].get("pForumNames")
                        rec["sample"] = (data[0].get("subject") or "")[:30]
                print(json.dumps(rec, ensure_ascii=False)[:220], flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = type(e).__name__
                print(json.dumps(rec, ensure_ascii=False)[:160], flush=True)
            rows_out.append(rec)
            time.sleep(2.0)
    (HERE / "liuyan-province-fid-scan.json").write_text(
        json.dumps(rows_out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[scan] 证据已写 recon/liuyan-province-fid-scan.json")
    return 0


if __name__ == "__main__":
    main()
