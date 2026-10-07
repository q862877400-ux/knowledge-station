"""补全省级版块 fid 扫描（556~600），产出「省 → 书记/省长 fid」映射表。

背景：已知 539/540=北京、541/542=天津、…、555=上海市委书记，
省级版块按行政区划顺序两两编号。本脚本扫完 556~600，
并把 539~600 的结果整理成 recon/liuyan-province-fids.json。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import BASE, _envelope, _headers  # noqa: E402

SCAN_FILE = HERE / "liuyan-province-fid-scan.json"
OUT = HERE / "liuyan-province-fids.json"
TITLE_RE = re.compile(r"^(.*?(?:省|市|自治区|特别行政区))")


def fetch_one(c, fid: str) -> dict:
    path = "/v1/threads/list/df"
    param = {"fid": fid, "showUnAnswer": 0, "lastItem": "",
             "position": 1, "rows": 2, "orderType": 2}
    r = c.post(BASE + path, content=_envelope(path, param),
               headers=_headers(f"{BASE}/threads/list?fid={fid}"))
    rec = {"fid": fid, "status": r.status_code}
    if "json" in r.headers.get("content-type", ""):
        data = ((r.json().get("resultData") or {}).get("data")) or []
        rec["n"] = len(data)
        if data:
            rec["forum"] = data[0].get("forumName")
            rec["p"] = data[0].get("pForumNames")
    return rec


def main() -> int:
    import httpx

    rows = json.loads(SCAN_FILE.read_text(encoding="utf-8")) if SCAN_FILE.exists() else []
    done = {r["fid"] for r in rows}
    with httpx.Client(trust_env=False, timeout=20) as c:
        for n in range(539, 601):
            fid = str(n)
            if fid in done:
                continue
            try:
                rec = fetch_one(c, fid)
            except Exception as e:                                          # noqa: BLE001
                rec = {"fid": fid, "error": type(e).__name__}
            rows.append(rec)
            if rec.get("status") != 200:
                print(f"fid={fid} → {rec.get('status', rec.get('error'))}（停）", flush=True)
                if rec.get("status") == 403:
                    break
            else:
                print(f"fid={fid} → {rec.get('p')} / {rec.get('forum')}", flush=True)
            SCAN_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
            time.sleep(2.0)

    # 整理：省 → {书记 fid, 省长 fid}
    prov_map: dict[str, dict] = {}
    for rec in rows:
        if rec.get("status") != 200 or not rec.get("p"):
            continue
        prov = rec["p"][0]
        forum = rec.get("forum") or ""
        role = "书记" if ("书记" in forum) else ("省/市长" if any(
            k in forum for k in ("省长", "市长", "主席", "自治区主席")) else "其他")
        slot = "secretary" if role == "书记" else ("governor" if role == "省/市长" else "other")
        item = prov_map.setdefault(prov, {"province": prov})
        if slot in item:
            slot = "other"
        item[slot] = rec["fid"]
        item.setdefault("fids", []).append({"fid": rec["fid"], "forum": forum, "role": role})
    out = sorted(prov_map.values(), key=lambda x: int(x.get("secretary") or x.get("fids")[0]["fid"]))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[map] 省级单位 {len(out)} 个 → {OUT.name}")
    for it in out:
        print(f"   {it['province']}: 书记 {it.get('secretary')} / 省长 {it.get('governor')}")
    return 0


if __name__ == "__main__":
    main()
