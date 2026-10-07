"""调吉林真实接口（haiyun.jl.gov.cn/IGI/nbhd/openGovmsgbox.do），看字段与规模。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

API = ("https://haiyun.jl.gov.cn/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
       "&siteId=117&order=1&appId=96&groupId=172&pageIndex={p}&pageSize={n}")
OUT = HERE / "jl-api-sample.json"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, timeout=25, follow_redirects=True) as c:
        r = c.get(API.format(p=1, n=5))
        text = r.text or ""
        print("status", r.status_code, "ct", r.headers.get("content-type"), "len", len(text))
        OUT.write_text(text[:20000], encoding="utf-8")
        try:
            j = r.json()
            print("顶层键:", list(j)[:10])
            d = j.get("datas") or {}
            print("datas 键:", list(d)[:8] if isinstance(d, dict) else type(d))
            rows = (d.get("data") if isinstance(d, dict) else None) or []
            print("条数:", len(rows))
            if rows:
                print("字段:", list(rows[0])[:30])
                print("样例:", json.dumps(rows[0], ensure_ascii=False)[:600])
        except Exception as e:                                              # noqa: BLE001
            print("非 JSON：", type(e).__name__, text[:200])
    return 0


if __name__ == "__main__":
    main()
