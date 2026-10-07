"""稀疏探 fid 800~4000：找「地级市」版块的编号区间。

已知：省 539~600、直辖市辖区 601~763、部委 5050~5120。
推测地级市版块在更高区间。稀疏取样（800/1000/1200/1500/2000/2500/3000/4000），
看每处返回什么行政层级，据此定位城市版块带。
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

OUT = HERE / "liuyan-city-band-scan.json"
SAMPLE = ["800", "900", "1000", "1100", "1200", "1500", "2000", "2500", "3000", "4000"]


def main() -> int:
    import httpx

    rows = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    done = {r["fid"] for r in rows}
    with httpx.Client(trust_env=False, timeout=20) as c:
        for fid in SAMPLE:
            if fid in done:
                continue
            path = "/v1/threads/list/df"
            param = {"fid": fid, "showUnAnswer": 0, "lastItem": "",
                     "position": 1, "rows": 2, "orderType": 2}
            rec = {"fid": fid}
            try:
                r = c.post(BASE + path, content=_envelope(path, param),
                           headers=_headers(f"{BASE}/threads/list?fid={fid}"))
                rec["status"] = r.status_code
                if "json" in r.headers.get("content-type", ""):
                    data = ((r.json().get("resultData") or {}).get("data")) or []
                    rec["n"] = len(data)
                    if data:
                        rec["p"] = data[0].get("pForumNames")
                        rec["forum"] = data[0].get("forumName")
                        rec["sample"] = (data[0].get("subject") or "")[:22]
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = type(e).__name__
            rows.append(rec)
            print(json.dumps(rec, ensure_ascii=False)[:190], flush=True)
            OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
            if rec.get("status") == 403:
                print("（403，停）")
                break
            time.sleep(2.0)
    return 0


if __name__ == "__main__":
    main()
