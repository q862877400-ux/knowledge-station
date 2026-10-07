"""调吉林厅「留言选登」开放接口，看返回格式与字段。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

BASE = "https://sthjt.jl.gov.cn"
URL = (BASE + "/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
       "&siteId=117&order=1&appId=96&groupId=172&pageIndex=1&pageSize=5")
OUT = HERE / "jl-lyxd-api-sample.txt"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA, "Referer": BASE + "/zmhd/tzxx/lyxd/"},
                      trust_env=False, timeout=20, follow_redirects=True) as c:
        r = c.get(URL)
        text = r.text or ""
        with OUT.open("w", encoding="utf-8") as f:
            f.write(f"status={r.status_code} ct={r.headers.get('content-type')} len={len(text)}\n\n")
            f.write(text[:2500])
        print("written", OUT, "len", len(text))
    return 0


if __name__ == "__main__":
    main()
