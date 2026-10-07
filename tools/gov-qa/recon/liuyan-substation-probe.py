"""试 /v1/forum/substation —— 拿地方分站（省/市）清单与 fid。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import BASE, _envelope, _headers  # noqa: E402

PATHS = ["/v1/forum/substation", "/v1/forum/getTopDfForums", "/v1/forum/getDfForums"]


def main() -> int:
    import httpx

    with httpx.Client(trust_env=False, timeout=20) as c:
        for path in PATHS:
            for param in ({}, {"_t": 1791389000000}):
                try:
                    r = c.post(BASE + path, content=_envelope(path, param),
                               headers=_headers(f"{BASE}/threads/localList"))
                except Exception as e:                                      # noqa: BLE001
                    print(path, "ERR", type(e).__name__)
                    continue
                ct = r.headers.get("content-type", "")
                print(f"{path} param={list(param)} → {r.status_code} {ct} len={len(r.text)}")
                if "json" in ct:
                    j = r.json()
                    rd = j.get("resultData")
                    print("   result:", str(j.get("result"))[:80])
                    if rd is not None:
                        s = json.dumps(rd, ensure_ascii=False)
                        print("   resultData 头 400 字:", s[:400])
                        Path(HERE / f"liuyan-substation{path.replace('/', '_')}.json").write_text(
                            s, encoding="utf-8")
                else:
                    print("   head:", r.text[:120].replace("\n", " "))
    return 0


if __name__ == "__main__":
    main()
