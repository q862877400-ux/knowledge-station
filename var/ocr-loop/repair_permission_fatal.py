"""状态修复：把 `PermissionError`（临时文件占用）误标 fatal 的记录放回重做路径。

与 `repair_fatal_misclass.py` 同类，但针对**云阶段异常**那一支：
`_safe_stage` 原先把**所有**异常都标 `fatal=True` → 转本地 VLM（慢约 20 倍、串行独占）。
实测 34 条 `PermissionError`（`WinError 32 另一个程序正在使用此文件` / `Errno 13`）
被误标——它们重试即可，与"云能力边界"无关。

判据：`fatal=True` 且 msg 含 `云阶段异常` 且含 `PermissionError`。
动作：`fatal=False`、`status="failed"`。用法：先预演，`--apply` 落盘。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(r"D:\AI\work space\zcode\var\ocr-loop")
STATE = HERE / "vlm_ocr_state.json"
APPLY = "--apply" in sys.argv

st = json.loads(STATE.read_text(encoding="utf-8"))
targets = []
for k, v in st.items():
    if not isinstance(v, dict) or not v.get("fatal"):
        continue
    m = str(v.get("msg") or "")
    if "云阶段异常" in m and "PermissionError" in m:
        targets.append((k, v))

print(f"将要修复 {len(targets)} 条（云阶段异常 + PermissionError 被误标 fatal）")
for k, v in targets[:5]:
    print(f"   {k[:50]} | {str(v.get('msg'))[:72]}")
if not APPLY:
    print("\n（预演，未写入。加 --apply 落盘）")
    raise SystemExit(0)

for _k, v in targets:
    v["fatal"] = False
    v["status"] = "failed"
    v["msg"] = ("（可重试异常误判修复）PermissionError=临时文件占用，本应重试；"
                "原消息：" + str(v.get("msg"))[:90])
STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n已修复 {len(targets)} 条")

with (HERE / "evolve" / "instrument_fixes.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps({
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kind": "state_repair", "cls": "-", "file": "var/ocr-loop/vlm_ocr.py",
        "why": "`_safe_stage` 把所有异常一律标 fatal=True，把 PermissionError（临时文件占用）"
               "也送去本地 VLM（慢约 20 倍）",
        "evidence": {"repaired": len(targets),
                     "rule": "fatal=True 且 msg 含『云阶段异常』且含 PermissionError",
                     "fix": "异常分支按类型分可重试/不可重试，只有不可重试才标 fatal"},
        "reinstatement_condition": "-",
    }, ensure_ascii=False) + "\n")
print("已登记 instrument_fixes.jsonl")
