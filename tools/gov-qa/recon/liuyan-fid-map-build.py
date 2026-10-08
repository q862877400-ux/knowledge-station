"""把多路 fid 密集扫描的结果合并成**全国版块地图**。

背景：`liuyan-fid-dense-scan.py` 支持多路并行（每路写自己的 jsonl），
本脚本负责把 `liuyan-fid-dense-scan*.jsonl` **合并去重**，产出：

- `liuyan-fid-national-map.json` —— `{fid: {province, city, forum, sample}}`（机器可读）
- `liuyan-fid-national-map.md`   —— 按省汇总（省 → 市/区县数 + fid 区间），人看
- `liuyan-fid-map.json`          —— **适配器输入格式**（`[{fid,label,province,city}]`），
  与既有的 `build-fid-map.py` 产物**合并**（保留它从时间流累积出来的条目），
  这样 `adapters/people_liuyan_fid.py` 不用改就能吃到全国版块表。

用法：python recon/liuyan-fid-map-build.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_JSON = HERE / "liuyan-fid-national-map.json"
OUT_MD = HERE / "liuyan-fid-national-map.md"
ADAPTER_MAP = HERE / "liuyan-fid-map.json"      # adapters/people_liuyan_fid.py 读这个


def main() -> int:
    rows: dict[str, dict] = {}
    files = sorted(HERE.glob("liuyan-fid-dense-scan*.jsonl"))
    bad = 0
    for f in files:
        for ln in f.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                r = json.loads(ln)
            except Exception:                                           # noqa: BLE001
                bad += 1
                continue
            fid = str(r.get("fid"))
            # 后来的覆盖先前的，但**只覆盖「有数据」的**（避免一次失败把已命中的抹掉）
            if fid not in rows or r.get("n"):
                rows[fid] = r

    hit = {k: v for k, v in rows.items() if v.get("n")}
    m: dict[str, dict] = {}
    by_prov: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for fid, r in hit.items():
        p = (r.get("p") or [])
        prov = p[0] if p else "(未知省)"
        city = p[1] if len(p) > 1 else ""
        m[fid] = {"province": prov, "city": city,
                  "forum": r.get("forum"), "sample": r.get("sample")}
        by_prov[prov].append((int(fid), city, r.get("forum") or ""))

    OUT_JSON.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [f"# 留言板全国版块地图（{len(m)} 个版块 / {len(by_prov)} 个省级单位）", "",
             f"> 由 `recon/liuyan-fid-map-build.py` 合并 {len(files)} 份扫描结果生成，**不要手改**。",
             f"> 已扫 fid {min(map(int, rows)) if rows else '-'}..{max(map(int, rows)) if rows else '-'}"
             f"（共 {len(rows)} 个，命中 {len(m)} 个，解析失败 {bad} 行）", "",
             "| 省级 | 版块数 | fid 区间 | 样例 |", "|---|---|---|---|"]
    for prov, items in sorted(by_prov.items(), key=lambda x: -len(x[1])):
        fs = sorted(i[0] for i in items)
        lines.append(f"| {prov} | {len(items)} | {fs[0]}~{fs[-1]} | "
                     f"{items[0][2][:20]} |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── 适配器输入格式：与既有 map 合并（保留 build-fid-map.py 从时间流累积的条目）──
    merged: dict[str, dict] = {}
    if ADAPTER_MAP.exists():
        try:
            for r in json.loads(ADAPTER_MAP.read_text(encoding="utf-8")):
                if r.get("fid"):
                    merged[str(r["fid"])] = r
        except Exception:                                               # noqa: BLE001
            pass
    for fid, v in m.items():
        old = merged.get(fid) or {}
        merged[fid] = {
            "fid": fid,
            "label": v.get("forum") or old.get("label") or v.get("city") or fid,
            "province": v.get("province") or old.get("province"),
            "city": v.get("city") or old.get("city"),
        }
    ADAPTER_MAP.write_text(
        json.dumps(sorted(merged.values(), key=lambda r: int(r["fid"])),
                   ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"合并 {len(files)} 份 → {len(rows)} 个 fid，命中 {len(m)} 个版块，"
          f"{len(by_prov)} 个省级单位")
    print(f"适配器映射表 liuyan-fid-map.json：{len(merged)} 个版块")
    for prov, items in sorted(by_prov.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  {prov}: {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
