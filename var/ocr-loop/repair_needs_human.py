"""⚠ **已被取代（2026-09-16）——不要再在有 worker 跑的时候用它**。

`needs-human` 的复归已改为**进程内机制**：`batch_advance._carry_over` +
`_terminal_human_reason()` + `READMIT_HARD_CAP` / `READMIT_QUOTA`（详见
HANDOFF §10.26）。**请优先用那条路径**，它自愈、每批自动执行、无需人工介入。

**为什么这个脚本不可靠**（实测，留着只为存档）：
本脚本是**外部**修改 `vlm_ocr_state.json`，而 `vlm_ocr.commit_rec` 是
**整体读改写**（`state[key] = rec; save_json(STATE, state)`）：worker 把 state
读进内存后，每次提交都用内存那份**整份覆盖文件** → 本脚本的修改
**只活到 worker 下一次提交为止**（秒级），却被**自报成功**。
实测 `--apply` 跑了**两次**、各自报 `repaired=37`，复查 state 仍是 37 部
`needs-human`（`ts` 未变）。故：对一个被活跃进程整体读改写的文件做外部修补，
等于写进一个会被覆盖的缓存。

若确实要在无 worker、无 driver 的静止状态下手工核对，本脚本仍可读（预演模式）。

---

状态修复：把 `needs-human` 中**纯临时失败**的文档放回携带队列。

背景（2026-09-16 实测）：批 10 有 37 部转 `needs-human`，msg 全是"云侧超时"、
页数 7–79（远低于 200 页硬限）。拿 6 部当场重测 **5 部成功**（6–32 秒）
→ 证明它们只是撞了降级窗口就被 `MAX_CARRY=3` 判了终态，属**内容缺口**。

判据（窄）：`status == needs-human` **且** msg 含"云侧超时" **且** 页数 ≤ 200。
  · 不含"能力边界"类（页数超限/格式不支持）——那些转人工是对的，**不动**；
  · 页数 > 200 的**不动**（真巨型，另有台账）。
动作：`status = failed`（→ 下批由 `_carry_over` 带回重跑）。
台账：向 `evolve/instrument_fixes.jsonl` 追加 append-only 记录。
用法：先预演，`--apply` 落盘。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(r"D:\AI\work space\zcode\var\ocr-loop")
STATE = HERE / "vlm_ocr_state.json"
APPLY = "--apply" in sys.argv
OVERSIZE = 200

st = json.loads(STATE.read_text(encoding="utf-8"))
targets, keep = [], []
for k, v in st.items():
    if not isinstance(v, dict) or v.get("status") != "needs-human":
        continue
    msg = str(v.get("msg") or "")
    pg = int(v.get("pages") or 0)
    if pg > OVERSIZE:
        keep.append((k, v, "页数 >200（真巨型）"))
    elif "云侧超时" in msg or "云解析失败" in msg:
        targets.append((k, v))
    else:
        keep.append((k, v, "非超时类（可能是能力边界）"))

print(f"将放回重跑：{len(targets)} 部（needs-human + 云超时 + ≤{OVERSIZE} 页）")
for k, v in targets[:6]:
    print(f"   {v.get('pages'):>4}页  {str(v.get('std_no'))[:44]}")
print(f"\n**保持不动**：{len(keep)} 部")
for k, v, why in keep[:8]:
    print(f"   {v.get('pages'):>4}页  {why}  {str(v.get('std_no'))[:36]}")

if not APPLY:
    print("\n（预演，未写入。加 --apply 落盘）")
    raise SystemExit(0)

for _k, v in targets:
    v["status"] = "failed"
    v["msg"] = ("（MAX_CARRY 3→8 修复）原判 needs-human 系纯云侧超时被 3 次携带误判为终态；"
                "实测 6 部中 5 部当场可成。原消息：" + str(v.get("msg"))[:100])
STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n已放回 {len(targets)} 部 → status=failed（下批 _carry_over 带回重跑）")

with (HERE / "evolve" / "instrument_fixes.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps({
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kind": "state_repair", "cls": "-", "file": "var/ocr-loop/batch_advance.py",
        "why": "把 needs-human 里**纯云侧超时**的文档放回携带队列（MAX_CARRY 3→8 的存量修复）",
        "evidence": {
            "repaired": len(targets),
            "kept": [{"std_no": str(v.get("std_no"))[:40], "pages": v.get("pages"), "why": w}
                     for _k, v, w in keep[:10]],
            "probe": "probe_needs_human.py：6 部实测 **5 部成功**（6.0/9.8/21.6/26.1/31.9 秒）",
            "rule": f"needs-human 且 msg 含云侧超时 且 页数 ≤{OVERSIZE}",
        },
        "reinstatement_condition": "-",
    }, ensure_ascii=False) + "\n")
print("已登记 instrument_fixes.jsonl")
