"""一次性状态修复：把被 `MineruCloudError` 宽判误标 `fatal=True` 的文档放回云重投路径。

背景（2026-09-16）：`vlm_ocr.run_cloud` 曾把**所有** `MineruCloudError` 当"云能力边界"
→ `fatal=True` → 路由进本地 VLM 队列（慢约 20 倍、串行独占 GPU）。而该异常同时承载
`429 Too Many Requests` / `retry limit reached` 这类**瞬时**错误——它们云侧能做，
只是此刻不行，**必须重投云**（本项目自己的告警早就写明这一点）。

本脚本只改**被判错的那批**：
  · 判据：`fatal=True` **且** `channel=="cloud"` **且** `status in (failed, pending-local)`
          **且** 页数 **≤ 200**（真能力边界是"页数超限"，故 >200 的一律不动）；
  · 动作：`fatal=False`、`status="failed"`（→ 下一个批次由 `_carry_over` 带回、重投云）；
  · 台账：向 `evolve/instrument_fixes.jsonl` 追加一条 append-only 记录；
  · **只读校验**：先打印将被修改的清单与计数，`--apply` 才落盘。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(r"D:\AI\work space\zcode\var\ocr-loop")
STATE = HERE / "vlm_ocr_state.json"
OVERSIZE = 200
APPLY = "--apply" in sys.argv

st = json.loads(STATE.read_text(encoding="utf-8"))
targets = []
for k, v in st.items():
    if not isinstance(v, dict):
        continue
    if not v.get("fatal"):
        continue
    if v.get("channel") != "cloud":
        continue
    if v.get("status") not in ("failed", "pending-local"):
        continue
    pg = int(v.get("pages") or 0)
    if pg > OVERSIZE:
        continue                      # 真·巨型文档：保持原状
    targets.append((k, v))

print(f"将要修复 {len(targets)} 条（fatal=True 且 channel=cloud 且 ≤{OVERSIZE} 页）")
print(f"其中 status=pending-local 的 {sum(1 for _, v in targets if v['status'] == 'pending-local')} 条")
if targets:
    pages = sorted(int(v.get("pages") or 0) for _, v in targets)
    print(f"页数：min {pages[0]} 中位 {pages[len(pages) // 2]} max {pages[-1]}")
    print("样例：")
    for k, v in targets[:5]:
        print(f"   {k[:52]}  {v.get('pages')}页  {str(v.get('msg'))[:56]}")

# 反向核对：**不该动**的记录
keep = [v for v in st.values() if isinstance(v, dict) and v.get("fatal")
        and int(v.get("pages") or 0) > OVERSIZE]
print(f"\n反向核对：fatal=True 且 >{OVERSIZE} 页（真巨型，**保持原状**）{len(keep)} 条")
for v in keep[:5]:
    print(f"   {(v.get('std_no') or '')[:50]}  {v.get('pages')}页")

if not APPLY:
    print("\n（预演，未写入。加 --apply 落盘）")
    raise SystemExit(0)

for _k, v in targets:
    v["fatal"] = False
    v["status"] = "failed"
    v["msg"] = ("（瞬时错误误判修复）原判 fatal=True 系 `MineruCloudError` 宽判所致；"
                "429/retry-limit 类属瞬时，改回重投云。原消息：" + str(v.get("msg"))[:90])
STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n已修复 {len(targets)} 条 → fatal=False / status=failed（下批带回归云重投）")

import time  # noqa: E402

fx = HERE / "evolve" / "instrument_fixes.jsonl"
with fx.open("a", encoding="utf-8") as f:
    f.write(json.dumps({
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kind": "state_repair", "cls": "-", "file": "var/ocr-loop/vlm_ocr.py",
        "why": "把被 `MineruCloudError` 宽判误标 fatal 的文档放回云重投路径",
        "evidence": {"repaired": len(targets),
                     "rule": f"fatal=True 且 channel=cloud 且 status∈(failed,pending-local) 且 ≤{OVERSIZE}页",
                     "cost_if_unfixed": "转本地 VLM（慢约 20 倍、串行独占）"},
        "reinstatement_condition": "-",
    }, ensure_ascii=False) + "\n")
print("已登记 instrument_fixes.jsonl")
