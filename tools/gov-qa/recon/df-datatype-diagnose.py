"""诊断：地方流（df）详情 contentList 里，哪种 dataType 才是【官方答复】。

背景：部委流（bw）实测 dataType==9 = 官方答复；地方流照搬该假设采了 5 条，
但答复读起来像**网友跟帖**（如「支持业主提议，……」）。
本脚本取一条 df 留言，打印 contentList 每条的 dataType / 长度 / 首 60 字，
并对照 bw 一条已知官方答复的形态，判定正确 dataType。
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
from adapters._liuyan_common import (  # noqa: E402
    BASE, _clean, _envelope, _headers)

DATA = HERE.parent / "data"


class _W:
    def __init__(self, client):
        self._c = client

    def post(self, *a, **k):
        return self._c.post(*a, **k)


def fetch_detail(w, tid: int) -> list[dict]:
    path = "/v1/threads/content"
    r = w.post(BASE + path, content=_envelope(path, {"tid": tid}),
               headers=_headers(f"{BASE}/threads/content?tid={tid}"))
    if r.status_code != 200:
        print("  HTTP", r.status_code, r.text[:80])
        return []
    return ((r.json().get("resultData") or {}).get("contentList")) or []


def dump(label: str, items: list[dict]) -> None:
    print(f"\n== {label}（contentList {len(items)} 条）")
    for i, it in enumerate(items):
        c = _clean(it.get("content") or "")
        print(f"  [{i}] dataType={it.get('dataType')} len={len(c)} "
              f"dateline={it.get('dateline')} :: {c[:70]}")


def main() -> int:
    import httpx

    # 取一条 df 已采记录 + 一条 bw 已采记录的 tid
    df_tid = bw_tid = None
    for p in DATA.glob("people-liuyan-df-*.jsonl"):
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        if rows:
            df_tid = rows[0]["id"]
    for p in DATA.glob("people-liuyan-*.jsonl"):
        if "df" in p.name:
            continue
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        if rows:
            bw_tid = rows[0]["id"]
    print("df tid:", df_tid, "| bw tid:", bw_tid)

    with httpx.Client(trust_env=False, timeout=20) as c:
        w = _W(c)
        if df_tid:
            dump(f"地方流 df tid={df_tid}", fetch_detail(w, int(df_tid)))
            time.sleep(2)
        if bw_tid:
            dump(f"部委流 bw tid={bw_tid}（对照）", fetch_detail(w, int(bw_tid)))
    return 0


if __name__ == "__main__":
    main()
