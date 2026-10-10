#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# check.sh —— D:/AI 政务问答项目的验收闸门（供 Stop hook 调用）
#
# 退出码：0 = 全部通过；1 = 有红项（Stop hook 据此阻止会话停止）
#
# 为什么需要这个脚本：GOAL.md 里原本那些「验收」是**展示命令**，用了 `| head` /
# `| tail`，会把管道退出码吃掉，永远返回 0 —— 等于没有闸门。
# 真正的判据必须落在**退出码**上，所以统一收进这里。
#
# ⚠ 2026-10-10 重写：原版用 `sed` 匹配**中文**（「数据总条数」「重复合计」）来解析，
#   而 **sed 的中文匹配依赖 locale/编码** —— 在 Stop hook 的执行环境里会失配，
#   于是解析不到 ⇒ 误判「执行失败」⇒ **闸门永远红**（排查了很久）。
#   ⇒ 现在改为：python 侧输出**纯 ASCII** 的 `KEY=VALUE`（`audit-coverage.py --gate`），
#     bash 侧只做 `grep`+`cut`，**完全不碰中文**。
# ---------------------------------------------------------------------------

set -uo pipefail

PROJ="D:/AI/work space/zcode"
P=".venv/Scripts/python.exe"

TRACE="/d/AI/output/check-trace.log"
_trace() { printf '%s\n' "$*" >> "$TRACE" 2>/dev/null || true; }

_trace "=== check.sh invoked at $(date '+%F %T') cwd=$(pwd) PROJ=$([ -d "$PROJ" ] && echo ok || echo MISSING) ==="

cd "$PROJ" 2>/dev/null || { echo "❌ 项目目录不存在：$PROJ" >&2; exit 1; }
[ -x "$P" ] || { echo "❌ 解释器不存在：$PROJ/$P" >&2; exit 1; }

FAIL=0
ok(){   printf '  ✅ %s\n' "$1" >&2; }
bad(){  printf '  ❌ %s\n' "$1" >&2; FAIL=1; }

# ---- 0) 自愈：**仅当覆盖率不足时**才补标签 ---------------------------------
# ⚠ 教训（2026-10-10，排查了很久）：label-classify.py --apply 每次都要
#   **训练 SVM 模型（约 2.5 分钟）**。如果无条件放在这里，hook 的 300s 超时会被打满
#   ⇒ 脚本被杀死 ⇒ 判为失败 ⇒ 闸门永远红（追踪日志里表现为「没有 parsed: 行」）。
#   ⇒ 先花 ~3s 测覆盖率，**只有 <90% 才补**。正常情况这一步是零成本的。
if ! "$P" tools/gov-qa/recon/label-coverage.py --gate 90 --quiet >/dev/null 2>&1; then
  _trace "  coverage <90% -> running label-classify --apply"
  "$P" tools/gov-qa/recon/label-classify.py --apply >/dev/null 2>&1 || true
fi

# ---- 取一次纯 ASCII 的机器可读指标 -----------------------------------------
GATE=$("$P" tools/gov-qa/recon/audit-coverage.py --gate 2>/dev/null || true)
getv(){ printf '%s\n' "$GATE" | grep "^$1=" | head -1 | cut -d= -f2 | tr -dc '0-9'; }

TOTAL=$(getv TOTAL)
EMPTY=$(getv EMPTY)
DUPS=$(getv DUPS)
ADAPTERS=$(getv ADAPTERS)
FLOOR=$(tr -dc '0-9' < .round-floor 2>/dev/null)
[ -z "$FLOOR" ] && FLOOR=0

_trace "  parsed: TOTAL=${TOTAL:-<empty>} EMPTY=${EMPTY:-<empty>} DUPS=${DUPS:-<empty>} ADAPTERS=${ADAPTERS:-<empty>} FLOOR=$FLOOR"

# ---- 0) 适配器注册表必须真的读到了（spec 005 T104 修的**假绿**）-------------
# ⚠ 2026-10-10：此前 `import adapters` 抛异常时，指标源打出 `ADAPTERS_ERR=...`
#   但 `EMPTY=0`；而本脚本只 `grep '^EMPTY='` ⇒ **判据②在注册表整体失效时仍报绿**。
#   实测复现：注入 `raise ImportError` ⇒ `ADAPTERS=0` + `EMPTY=0` ⇒ 全绿。
#   两道防线：① 指标源侧把 EMPTY 输出成非数字哨兵 `ERR`（已修）；
#             ② 这里显式要求 ADAPTERS>0 且无 ADAPTERS_ERR（本段）。
#   两道都要，因为任一侧被改回旧写法都会重新打开这个洞。
if printf '%s\n' "$GATE" | grep -q '^ADAPTERS_ERR='; then
  bad "适配器注册表读取失败（$(printf '%s\n' "$GATE" | grep '^ADAPTERS_ERR=' | head -1)）—— 判据②无从判定"
elif [ -z "$ADAPTERS" ] || [ "$ADAPTERS" -eq 0 ]; then
  bad "适配器数为 0（注册表读不到或为空）—— 判据②无从判定，不许当作「无零数据适配器」"
else
  ok "适配器注册表可读（$ADAPTERS 个）"
fi

# ---- 1) 数据总数不降（防空转闸门） -----------------------------------------
if [ -z "$TOTAL" ]; then
  bad "拿不到数据总数（audit-coverage.py --gate 执行失败）"
elif [ "$TOTAL" -lt "$FLOOR" ]; then
  bad "数据在退：$TOTAL < 地板 $FLOOR —— 先查是不是有文件被删/损坏"
else
  ok "数据总数 $TOTAL ≥ 地板 $FLOOR"
fi

# ---- 2) 没有「建好没采」的适配器 -------------------------------------------
if [ -z "$EMPTY" ]; then
  bad "拿不到零数据适配器数（--gate 执行失败）"
elif [ "$EMPTY" -gt 0 ]; then
  bad "有 $EMPTY 个零数据适配器（跑 --empty 看清单，先跑它们）"
else
  ok "无零数据适配器"
fi

# ---- 3) 没有重复 id 污染 ---------------------------------------------------
if [ -z "$DUPS" ]; then
  bad "拿不到重复统计（--gate 执行失败）"
elif [ "$DUPS" -gt 0 ]; then
  bad "有 $DUPS 行重复 id（跑 --dups 看是哪些源）"
else
  ok "无重复 id"
fi

# ---- 4) 标签覆盖率 ≥90%（M3 目标） -----------------------------------------
# ⚠ 用 --quiet：输出**纯 ASCII 的 COVERAGE=<pct>**。
#   原版直接跑 --gate 会打印中文，而 Stop hook 的执行环境 stdout 编码不是 UTF-8
#   ⇒ UnicodeEncodeError ⇒ rc=1 ⇒ 覆盖率明明是 100% 却判据④ 假红（2026-10-10 定位到）。
LBL_OUT=$("$P" tools/gov-qa/recon/label-coverage.py --gate 90 --quiet 2>&1)
LBL_RC=$?
COV=$(printf '%s' "$LBL_OUT" | grep '^COVERAGE=' | head -1 | cut -d= -f2)
_trace "  label-coverage rc=$LBL_RC cov=${COV:-<none>} raw=$(printf '%s' "$LBL_OUT" | head -1)"
if [ "$LBL_RC" -eq 0 ]; then
  ok "标签覆盖率 ${COV:-?}% ≥90%"
else
  bad "标签覆盖率 ${COV:-?}% <90%（rc=$LBL_RC）"
fi

# ---- 5) 数据质量四项（spec 005 T102/T103）-----------------------------------
# 为什么加：前四条判据**都不覆盖「字段非空但内容是垃圾」**。2026-10-10 独立诊断实测：
#   `xz-lasa` 全源 1,030 条答复为空、8,470 条内容重复（id 不同）、20,131 条时间倒置
#   —— 旧闸门在这份数据上照样报「质量全绿」。
# 口径：`gate-quality.py` 是这四项的**唯一数字源**；默认走**棘轮**模式
#   （缺陷不许恶化），`--strict` 才判绝对阈值。过渡态说明见该脚本模块文档。
# 退出码：0 = 棘轮全过 / 1 = 有指标恶化 / 2 = 执行失败。
Q_OUT=$("$P" tools/gov-qa/recon/gate-quality.py --quiet 2>&1)
Q_RC=$?
Q_DUPS=$(printf '%s' "$Q_OUT" | grep '^CONTENT_DUPS=' | head -1 | cut -d= -f2)
Q_INV=$(printf '%s' "$Q_OUT" | grep '^TIME_INVERTED=' | head -1 | cut -d= -f2)
Q_EMPTY=$(printf '%s' "$Q_OUT" | grep '^ANSWER_EMPTY=' | head -1 | cut -d= -f2)
Q_MODE=$(printf '%s' "$Q_OUT" | grep '^MODE=' | head -1 | cut -d= -f2)
_trace "  gate-quality rc=$Q_RC mode=${Q_MODE:-<none>} dups=${Q_DUPS:-<none>} inv=${Q_INV:-<none>} empty=${Q_EMPTY:-<none>}"
if [ "$Q_RC" -eq 2 ]; then
  bad "数据质量闸门执行失败（rc=2）"
elif [ "$Q_RC" -eq 0 ]; then
  ok "数据质量（棘轮）：重复 ${Q_DUPS:-?} · 倒置 ${Q_INV:-?} · 空答复 ${Q_EMPTY:-?}（未恶化）"
else
  bad "数据质量**恶化**：重复 ${Q_DUPS:-?} · 倒置 ${Q_INV:-?} · 空答复 ${Q_EMPTY:-?}（跑 gate-quality.py 看明细）"
fi

# ---- 结论：**质量全绿 + 连续工作 ≥24h，两个都满足才放行** -------------------
# 用户的停止条件逐字：「以工作连续时长达到 24 小时为一个闸门，
#   就是前面说的质量和 24 小时的连续工作时间**必须同时满足**之后才能够停下来」。
#
# 起点记在 output/.work-start-ts（首次运行时创建）。这是**连续**时长 ——
# 只统计「本链条」的运行时间；闸门每次调用都会刷新这个文件的时间戳以外的
# 一个 heartbeat，用来判断链条是否还活着（见下）。
START_FILE="output/.work-start-ts"
HB_FILE="output/.work-heartbeat"
NOW=$(date +%s)
if [ ! -f "$START_FILE" ]; then
  echo "$NOW" > "$START_FILE" 2>/dev/null || true
  _trace "  初始化工作起点 $(date '+%F %T')"
fi
START_TS=$(tr -dc '0-9' < "$START_FILE" 2>/dev/null)
[ -z "$START_TS" ] && START_TS=$NOW

# 链条存活判定：距上次心跳 >30 分钟 ⇒ 视为「断了」，重新计时
if [ -f "$HB_FILE" ]; then
  LAST_HB=$(tr -dc '0-9' < "$HB_FILE" 2>/dev/null)
  if [ -n "$LAST_HB" ] && [ $((NOW - LAST_HB)) -gt 1800 ]; then
    _trace "  心跳中断 $(( (NOW - LAST_HB) / 60 )) 分钟 -> 重新计时"
    echo "$NOW" > "$START_FILE" 2>/dev/null || true
    START_TS=$NOW
  fi
fi
echo "$NOW" > "$HB_FILE" 2>/dev/null || true

ELAPSED=$((NOW - START_TS))
HOURS=$((ELAPSED / 3600))
MINS=$(( (ELAPSED % 3600) / 60 ))
TARGET=86400          # 24 小时

_trace "  RESULT: FAIL=$FAIL  elapsed=${HOURS}h${MINS}m/24h"

if [ "$FAIL" -eq 0 ] && [ "$ELAPSED" -ge "$TARGET" ]; then
  echo "✅ 双条件满足：质量全绿 + 连续工作 ${HOURS}h${MINS}m ≥ 24h。允许停止。" >&2
  exit 0
fi

if [ "$FAIL" -ne 0 ]; then
  echo "❌ 质量未达标（见上）。已连续工作 ${HOURS}h${MINS}m / 24h。" >&2
fi
if [ "$ELAPSED" -lt "$TARGET" ]; then
  echo "⏳ 连续工作时长未满：${HOURS}h${MINS}m / 24h（还需 $(( (TARGET - ELAPSED) / 3600 ))h$(( ((TARGET - ELAPSED) % 3600) / 60 ))m）。" >&2
fi
echo "按 GOAL.md 第五节继续推进 —— 下一轮挑最该做的那件。" >&2
exit 1
