"""验证：df 流是否支持按 fid 定向（拿某个地方领导版块的全部已办理留言）。

若能，全国覆盖就从「时间流随机采样」变成「按省市 fid 定向采集」。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import BASE, _envelope, _headers  # noqa: E402

TEST_FIDS = [("539", "北京市委书记"), ("540", "北京市长")]


def main() -> int:
    import httpx

    out = []
    with httpx.Client(trust_env=False, timeout=20) as c:
        for fid, label in TEST_FIDS:
            path = "/v1/threads/list/df"
            param = {"fid": fid, "showUnAnswer": 0, "lastItem": "",
                     "position": 1, "rows": 10, "orderType": 2}
            r = c.post(BASE + path, content=_envelope(path, param),
                       headers=_headers(f"{BASE}/threads/list?fid={fid}"))
            rec = {"fid": fid, "label": label, "status": r.status_code}
            ct = r.headers.get("content-type", "")
            if "json" in ct:
                j = r.json()
                rd = j.get("resultData") or {}
                data = rd.get("data") or []
                rec["total"] = rd.get("total")
                rec["n"] = len(data)
                rec["sample"] = [
                    {"tid": x.get("tid"), "title": (x.get("subject") or "")[:40],
                     "forum": x.get("forumName"), "p": x.get("pForumNames")}
                    for x in data[:3]]
            else:
                rec["head"] = r.text[:100]
            print(json.dumps(rec, ensure_ascii=False)[:400])
            out.append(rec)
    (HERE / "df-fid-target-test.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    main()
