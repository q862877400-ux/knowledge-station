"""适配器：**人民网领导留言板 · 定向版块**（按 fid 深采某省/某市/某领导的留言）。

## 为什么有它（2026-10-07 实测）
`POST /v1/threads/list/df` 支持 `fid` 参数：`fid=540`（北京市长版块）返回该版块自己的留言
（证据 `recon/df-fid-target-test.json`）。而每条已采记录都带 `extra.fid` + `extra.pForumNames`
（省→市→县），所以：
 · **广度**：不带 fid 的时间流（`people-liuyan-df`）跑多批，累积出「省市 → fid」映射；
 · **深度**：本适配器按映射表逐个版块采满。
映射表由 `recon/build-fid-map.py` 从 `data/` 生成到 `recon/liuyan-fid-map.json`。

## 配置
`recon/liuyan-fid-map.json` 形如：
```json
[{"fid": "540", "label": "北京市市长", "province": "北京市", "city": null}, …]
```
文件不存在时**只采前 N 个**（N=`MAX_FIDS_PER_RUN`）并打印提示。

## 限流
同基座：每请求 ≥2.5s；单次运行总量受配额限制（每窗约 40 次调用），建议 `--limit` 控制。
"""
from __future__ import annotations

import json
from pathlib import Path

from adapters._liuyan_common import harvest_liuyan

SITE = {
    "key": "people-liuyan-fid",
    "name": "人民网领导留言板·定向版块",
    "kind": "api",
    "level": "mixed",
    "entry": "https://liuyan.people.com.cn/threads/localList",
    "status": "ok",
    "note": "按 fid 定向深采（fid 从 extra.fid + pForumNames 累积）；广度走时间流、深度走定向",
}

MAP_FILE = Path(__file__).resolve().parent.parent / "recon" / "liuyan-fid-map.json"
CURSOR_DIR = Path(__file__).resolve().parent.parent / "data"
MAX_FIDS_PER_RUN = 5


def _load_fids() -> list[dict]:
    if not MAP_FILE.exists():
        print(f"    [{SITE['key']}] 缺 {MAP_FILE.name}（先跑 recon/build-fid-map.py）")
        return []
    rows = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    return rows[:MAX_FIDS_PER_RUN]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按映射表逐个版块采（每个版块采满已办理且有官方答复的留言）。

    ⚠ **每个版块一个游标**（`data/.people-liuyan-fid-<fid>.cursor`）：版块列表同样按时间倒序，
    没有游标就会每次重读版块头部、被去重全挡（与时间流同一个坑，已踩过一次）。
    """
    out: list[dict] = []
    for row in _load_fids():
        fid = str(row.get("fid") or "")
        if not fid:
            continue
        label = row.get("label") or row.get("province") or fid
        print(f"    [{SITE['key']}] 定向版块 fid={fid}（{label}）")
        cursor = CURSOR_DIR / f".people-liuyan-fid-{fid}.cursor"
        rows = harvest_liuyan(fetch, SITE=SITE, stream="df", fid=fid,
                              limit=limit, cursor_file=cursor)
        for r in rows:
            r.setdefault("extra", {})["fid_label"] = label
        out += rows
        if limit and len(out) >= limit:
            return out[:limit]
    return out
