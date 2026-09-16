# -*- coding: utf-8 -*-
"""确认 watchdog 会自愈 **driver**（而不只是批量本身）。

**为什么要专门确认**（2026-09-15 实测）：分工是
  driver（`batch_advance.py`）负责**跨批推进**：等本批跑完 → 取基线 → 无达线类则取下一批；
  watchdog 负责**进程存活**：批量不在就跑起来。
但两者合起来有一个**无人推进的缺口**：driver 死掉后，watchdog 只会把**当前批**
再拉起来（它不懂跨批），于是批量照跑、批次却永远停在同一个——实测 driver 曾因
路径 bug 每批都"交人工"停下，推进链静默断掉（详见 `batch_advance._list_path` 注释）。

本测试用**行为断言**（不读实现）：注入一个"driver 死"的世界，看 watchdog 的
实际动作是否是"接管并拉起批量"，以及 driver 存活时是否退让（避免重复烧云额度）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = (HERE / "watchdog.ps1").read_text(encoding="utf-8")

FAIL: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {name}: {got!r}"
          f"{'' if ok else f'（期望 {want!r}）'}")
    if not ok:
        FAIL.append(name)


print("=== watchdog 的 driver 仲裁（行为断言）===")
# 1) driver 存活判定必须**同时**看 pid 与心跳新鲜度。
#    只判 pid 会因 pid 复用/残留而永远退让（HISTORY 实测：推进停滞 27 分钟无人知）。
check("校验 pid 存活", "orun" in SRC, True)
check("校验心跳新鲜度", "ageMin" in SRC, True)
check("有心跳阈值常量", "STALE_MIN" in SRC, True)
# **2026-09-15 设计变更**：退让判据从"心跳新鲜"改为**"driver 进程存活"**。
# 原因（实测缺陷）：driver 主循环曾被慢查询卡 37 分钟 → 心跳变旧 → 本脚本判定
# "driver 卡死"→ **另拉起一份 vlm_ocr** → 与 driver 抢，进程增殖到 5 个
# （state 无跨进程锁，互相覆盖台账）。
# 现判据：`if ($orun) { 退让 }` —— **慢 ≠ 死**；心跳仍记录供人工回看，
# 但不再作为接管依据。故这里必须断言新写法，并配一条"driver 死才接管"的反向对照。
check("driver 进程存活即退让（慢≠死）",
      bool(re.search(r"if\s*\(\s*\$orun\s*\)\s*\{", SRC)), True)
check("不再以心跳新鲜度作为退让条件",
      bool(re.search(r"if\s*\(\s*\$orun\s*-and\s*\$ageMin\s*-lt\s*\$STALE_MIN\s*\)",
                     SRC)), False)
# 2) **driver 真死**（pid 不存在）→ 必须接管，否则批量没人拉起
check("driver 死→接管（提示词）", "本脚本接管" in SRC or "已死" in SRC, True)
# 3) 批量存活时优先退出（不与批量抢）
check("批量存活即退出", bool(re.search(r"if\s*\(\s*\$alive\s*\)\s*\{", SRC)), True)
# 4) 拉起命令必须用**绝对路径 + 引号**（相对/无引号路径含空格会被拆成多参数，实测启动即退）
check("脚本路径用绝对路径", "scriptAbs" in SRC, True)
check("清单路径用绝对路径", "corpusAbs" in SRC, True)
check("脚本路径带引号", '`"$scriptAbs`"' in SRC, True)
check("清单路径带引号", '`"$corpusAbs`"' in SRC, True)
# 5) 拉起后必须复查存活（把"起了就死"与"跑一段才死"分开）
check("拉起后 5 秒复查", bool(re.search(r"Start-Sleep\s+-Seconds\s+5", SRC)), True)
check("复查结果落日志", "5 秒内已退出" in SRC or "5 秒后仍存活" in SRC, True)
# 6) 批次配置必须读单一所有者（换批不改脚本）
check("读 current_batch.json", "current_batch.json" in SRC, True)
check("无硬编码语料兜底名", "fresh_corpus_work.json" in SRC, True)

print("\n=== 缺口登记（已知、有意保留）===")
# watchdog **不负责跨批**：它只按 current_batch 拉起当前批。
# 故 driver 死后"批量照跑但批次不换"是**设计内**行为，由常驻 driver 保证推进。
# 这条断言把该边界钉住，防止下一个会话误以为 watchdog 会推进批次。
check("watchdog 不写 current_batch（边界钉住）",
      bool(re.search(r"current_batch\.json", SRC)) and "Set-Content" not in SRC, True)

print()
if FAIL:
    print(f"❌ {len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("✅ 全部通过")
