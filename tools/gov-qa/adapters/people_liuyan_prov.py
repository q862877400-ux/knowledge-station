"""适配器：**人民网领导留言板 · 按省定向**（全国 31 个省级单位，逐个采省委书记/省长版块）。

## 机制（2026-10-07 发现并实扫验证）
留言板的**省级版块按行政区划顺序两两连续编号**：
`书记 fid = 539 + 2×序号`、`省长/市长/主席 fid = 书记 + 1`（北京 539/540 … 河南 569/570 …）。
实扫确认 16 个省（见 `recon/liuyan-province-fid-scan.json`），其余按规律推算
（`recon/liuyan-province-fids.json` 里带 `confirmed` 标记，**推算项用前需实扫确认**）。
⇒ **想采哪个省就采哪个省**，不再受"时间流随机采样"限制。

## 与另两个留言板适配器的关系
 · `people-liuyan`      —— 部委版块（国家级）
 · `people-liuyan-df`   —— 地方**时间流**（广度：自动发现新省/市/县的 fid）
 · `people-liuyan-fid`  —— 按**已发现**的 fid 轮转深采（深度）
 · **`people-liuyan-prov`（本适配器）** —— 按**省级编号规律**直接采 31 个省（广度+深度一步到位）
"""
from __future__ import annotations

import json
from pathlib import Path

from adapters._liuyan_common import harvest_liuyan

SITE = {
    "key": "people-liuyan-prov",
    "name": "人民网领导留言板·分省",
    "kind": "api",
    "level": "province",
    "entry": "https://liuyan.people.com.cn/threads/localList",
    "status": "ok",
    "note": "按省级 fid 规律（书记=539+2i、省长=+1）逐省采；31 省映射见 recon/liuyan-province-fids.json",
}

MAP_FILE = Path(__file__).resolve().parent.parent / "recon" / "liuyan-province-fids.json"
CURSOR_DIR = Path(__file__).resolve().parent.parent / "data"
ROTATION_FILE = CURSOR_DIR / ".people-liuyan-prov.rotation"
#: 每轮采几个省（配额约 40 次调用/窗：一个省 2 个版块 ≈ 2 次列表 + N 次详情）
PROVINCES_PER_RUN = 3


def _provinces() -> list[dict]:
    if not MAP_FILE.exists():
        print(f"    [{SITE['key']}] 缺 {MAP_FILE.name}（先跑 recon/liuyan-province-fids-build.py）")
        return []
    rows = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    if not rows:
        return []
    start = 0
    if ROTATION_FILE.exists():
        try:
            start = int(ROTATION_FILE.read_text(encoding="utf-8").strip() or 0)
        except ValueError:
            start = 0
    start %= len(rows)
    picked = [rows[(start + i) % len(rows)]
              for i in range(min(PROVINCES_PER_RUN, len(rows)))]
    ROTATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    ROTATION_FILE.write_text(str((start + len(picked)) % len(rows)), encoding="utf-8")
    return picked


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """逐省采（每省两个版块：省委书记 / 省长），配额均分、带版块游标与省份轮转。"""
    out: list[dict] = []
    provs = _provinces()
    if not provs:
        return out
    per_board = max(1, (limit or 20) // max(1, len(provs) * 2)) if limit else None
    for p in provs:
        for slot, label in (("secretary", "省委书记"), ("governor", "省长/主席/市长")):
            fid = str(p.get(slot) or "")
            if not fid:
                continue
            name = f"{p['province']}{label}"
            print(f"    [{SITE['key']}] {name}（fid={fid}）配额 {per_board}")
            cursor = CURSOR_DIR / f".people-liuyan-prov-{fid}.cursor"
            rows = harvest_liuyan(fetch, SITE=SITE, stream="df", fid=fid,
                                  limit=per_board, cursor_file=cursor)
            for r in rows:
                r.setdefault("extra", {})["fid_label"] = name
                r["extra"]["province_declared"] = p["province"]
            out += rows
            if limit and len(out) >= limit:
                return out[:limit]
    return out
