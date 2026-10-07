"""试 `/v1/forum/substation` 带参数：能否拿到某省下的地市/区县版块清单。

背景：不带参数时返回 `{"hasColumnConfig": false}`；若能带 fid/省份 取到下级版块，
市级/县级覆盖就能从"扫号"变成"按省列举"。
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

PATHS = ["/v1/forum/substation", "/v1/forum/subSite", "/v1/forum/list",
         "/v1/forum/getSubForums", "/v1/forum/subForumList"]
PARAMS = [
    {"fid": "575"},              # 广东省委书记
    {"parentId": "575"},
    {"pid": "575"},
    {"provinceId": "575"},
    {"id": "575"},
    {"fid": "575", "type": "df"},
]


def main() -> int:
    import httpx

    out = []
    with httpx.Client(trust_env=False, timeout=15) as c:
        for path in PATHS:
            for param in PARAMS[:3]:
                rec = {"path": path, "param": param}
                try:
                    r = c.post(BASE + path, content=_envelope(path, param),
                               headers=_headers(f"{BASE}/threads/localList"))
                    rec["status"] = r.status_code
                    ct = r.headers.get("content-type", "")
                    if "json" in ct:
                        j = r.json()
                        rd = j.get("resultData")
                        rec["result"] = str(j.get("result"))[:60]
                        s = json.dumps(rd, ensure_ascii=False) if rd is not None else ""
                        rec["rd_len"] = len(s)
                        rec["rd_head"] = s[:200]
                    else:
                        rec["head"] = r.text[:80]
                except Exception as e:                                      # noqa: BLE001
                    rec["error"] = type(e).__name__
                out.append(rec)
                interesting = rec.get("rd_len", 0) > 40
                print(f"{path} {list(param)} → {rec.get('status')} "
                      f"rd_len={rec.get('rd_len')} {rec.get('rd_head', '')[:80]}",
                      flush=True)
                if interesting:
                    print("   ★ 有内容，停止试探")
                    (HERE / "liuyan-substation-probe2.json").write_text(
                        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
                    return 0
                time.sleep(1.5)
                if rec.get("status") == 403:
                    print("（403，停）")
                    (HERE / "liuyan-substation-probe2.json").write_text(
                        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
                    return 0
    (HERE / "liuyan-substation-probe2.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[probe2] 全部无内容 → 该接口不是「按省列下级版块」的入口")
    return 0


if __name__ == "__main__":
    main()
