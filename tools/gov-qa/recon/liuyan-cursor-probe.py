"""人民网留言板 · 全站流翻页行为探测（带退避重试）。

背景：正式采集在扫过 54 条后光标提前耗尽（只收 30 条）。本脚本用 rows=50
走 4 页，逐页记录 n / lastItem / hasData，判断「流就这么长」还是「翻页参数错」。
礼貌：请求间隔 2.5s，非 JSON 退避 5s 重试一次。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD_ROOT = HERE.parent
sys.path.insert(0, str(MOD_ROOT))     # 让 `import adapters` 生效（本脚本在 recon/ 下）

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

from adapters._liuyan_common import BASE, _envelope, _headers  # noqa: E402


def main() -> int:
    import httpx

    with httpx.Client(trust_env=False, timeout=20) as c:
        path = "/v1/threads/list/bw"
        last, pos = "", 1
        lines = []
        for page in range(1, 5):
            param = {"showUnAnswer": 0, "lastItem": last, "position": pos,
                     "rows": 50, "orderType": 2}
            r = c.post(BASE + path, content=_envelope(path, param),
                       headers=_headers(f"{BASE}/index"))
            text = r.text or ""
            if "json" not in (r.headers.get("content-type") or ""):
                print(f"page={page} HTTP {r.status_code} 非 JSON（len={len(text)}），"
                      f"退避重试…")
                time.sleep(5)
                r = c.post(BASE + path, content=_envelope(path, param),
                           headers=_headers(f"{BASE}/index"))
                text = r.text or ""
            try:
                rd = (r.json().get("resultData") or {})
            except Exception as e:                                          # noqa: BLE001
                line = f"page={page} 仍非 JSON：{type(e).__name__} head={text[:120]!r}"
                print(line)
                lines.append(line)
                break
            data = rd.get("data") or []
            line = (f"page={page} n={len(data)} "
                    f"lastItem={rd.get('lastItem')} hasData={rd.get('hasData')} "
                    f"keys={list(rd.keys())}")
            print(line)
            lines.append(line)
            last = rd.get("lastItem") or ""
            if not data or not last:
                break
            pos += 1
            time.sleep(2.5)

    (HERE / "liuyan-sitewide-cursor.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    main()
