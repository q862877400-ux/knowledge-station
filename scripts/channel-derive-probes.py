"""给「有台账、没探针目标」的渠道**机械派生**探针目标并实测（2026-11-02）。

## 为什么要这个脚本

台账 `update_channel` 有 **286** 条渠道，但探针目标表
（`channel_probes.json`）只有 **102** 条 ⇒ **184 条从来没被自动检测过**：
它们的 `state`/`verification` 是研究期的一次性结论，不是实测。

其中 **155 条**是真站点（标/法/地标/团标），且 `url` 就是**一条可直连的 http(s) 地址**。
这 155 条不需要人工研究就能测出真相：**连通 / 不通 / 被挡**。

## 口径（刻意保守，不造假判据）

- **只探连通性**：派生目标**不写 `expect`**（不发明"页面里应该出现什么字样"）。
  按 `channel_probe._validate_target` 的既有契约，无锚点会被如实记成
  `unknown / no_anchor_configured` —— 意思是"**通了，但没判据判它对不对**"，
  不是"假绿"。
- **`tool` 类不探**：那 17 条是 GitHub / npm 参考项目（`category=tool`），
  不是公告栏，探了也没有意义。
- 占位符 URL（`<标准号 标准名>`）、方法前缀（`GET …`）、非 http 的**不派生**，
  留给人工；脚本会把它们列出来。

## 用法

    .venv\\Scripts\\python.exe scripts/channel-derive-probes.py --dry
    .venv\\Scripts\\python.exe scripts/channel-derive-probes.py --apply
    .venv\\Scripts\\python.exe scripts/channel-derive-probes.py --probe

`--apply` 只写 `channel_probes.json`（版本控制内的接线产物），每条目标带
`note` 标明"派生、无锚点"，避免以后把它当人工锚点。
`--probe` 逐条实测并 `persist=True` 写回台账（`record_probe`）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.storage import channel_repo as cr  # noqa: E402
from src.core.update import channel_probe as cp  # noqa: E402

#: 这些类别的 `url` 是**参考项目**而不是公告栏，不派生探针
SKIP_CATEGORIES = {"tool"}

PLAIN_URL = re.compile(r"^https?://[^\s<>`]+$")


def candidates() -> tuple[list[dict], list[dict], list[dict]]:
    """(可派生, 跳过-tool, 需人工)。

    需人工 = 有 URL 但形态不可直连（占位符 / 方法前缀 / 非 http）。
    """
    targets = cp.load_targets()
    rows = cr.list_channels()
    can, tools, manual = [], [], []
    for r in rows:
        cid = str(r.get("channel_id"))
        if cid in targets:
            continue
        url = str(r.get("url") or "").strip()
        cat = str(r.get("category") or "")
        if cat in SKIP_CATEGORIES:
            tools.append(r)
            continue
        if PLAIN_URL.match(url):
            can.append(r)
        else:
            manual.append(r)
    return can, tools, manual


def build_target(row: dict) -> dict:
    """派生一条目标：**只有 url**（不写 expect，见模块 docstring 的口径）。"""
    return {
        "url": str(row["url"]).strip(),
        "note": ("派生（2026-11-02 自动化）：仅探连通性，**未配锚点**"
                 "—— state=unknown/no_anchor_configured 是如实结果，不是假绿"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只列，不写")
    ap.add_argument("--apply", action="store_true",
                    help="把派生目标写进 channel_probes.json")
    ap.add_argument("--probe", action="store_true", help="实测（写回台账）")
    ap.add_argument("--limit", type=int, default=0, help="只探前 N 条（0=全部）")
    args = ap.parse_args()

    can, tools, manual = candidates()
    print(f"可派生 {len(can)} / 跳过 tool {len(tools)} / 需人工 {len(manual)}")
    by_cat: dict[str, int] = {}
    for r in can:
        by_cat[str(r.get("category"))] = by_cat.get(str(r.get("category")), 0) + 1
    print("  可派生按类别：", dict(sorted(by_cat.items(), key=lambda kv: -kv[1])))

    if args.dry:
        for r in can[:12]:
            print(f"    {str(r.get('name'))[:22]:24} {str(r.get('url'))[:66]}")
        print(f"\n需人工 {len(manual)} 条：")
        for r in manual:
            print(f"    {str(r.get('name'))[:22]:24} {str(r.get('url'))[:60]}")
        return 0

    if args.apply:
        p = cp.PROBES_PATH
        data = json.loads(p.read_text(encoding="utf-8"))
        added = 0
        for r in can:
            cid = str(r["channel_id"])
            if cid in data["targets"]:
                continue
            tgt = build_target(r)
            cp._validate_target(cid, tgt)      # 写之前先按读表同一条判据校验
            data["targets"][cid] = tgt
            added += 1
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
        print(f"已写入 {added} 条派生目标 → {p.relative_to(ROOT)}"
              f"（现共 {len(data['targets'])} 条）")
        return 0

    if args.probe:
        ids = [str(r["channel_id"]) for r in can]
        # 只探**派生出来的**那些（人工锚点的已有结论，别拿无锚点覆盖它们）
        if args.limit:
            ids = ids[: args.limit]
        print(f"开始实测 {len(ids)} 条（逐条串行，20s 超时/条，"
              f"预计 ≤{len(ids) * 12 // 60} 分钟）")
        t0 = time.monotonic()
        out = cp.probe_channels(ids=ids, persist=True)
        dt = time.monotonic() - t0
        print(f"用时 {dt / 60:.1f} 分钟")
        print("state 分布：", dict(sorted(out["counts"].items(),
                                         key=lambda kv: -kv[1])))
        errs: dict[str, int] = {}
        for r in out["results"]:
            if r.get("error_code"):
                errs[r["error_code"]] = errs.get(r["error_code"], 0) + 1
        print("错误码分布：", dict(sorted(errs.items(), key=lambda kv: -kv[1])))
        rep = ROOT / "var" / "tmp" / "channel-derive-probe-report.json"
        rep.parent.mkdir(parents=True, exist_ok=True)
        rep.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"明细 → {rep.relative_to(ROOT)}")
        return 0

    print("没有动作：加 --dry / --apply / --probe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
