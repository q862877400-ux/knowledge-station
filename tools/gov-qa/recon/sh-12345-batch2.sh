#!/usr/bin/env bash
# 上海 sh-12345 续采批处理 第 2 批（2026-10-09 早场，作者=自动化定时任务对话）。
#
# 上游 count=7248；第 1 批 3 块后存量 5020 ⇒ 还差约 2,228 条。
# 第 1 批实测：单块 2500 条约 9.5 分钟（约 335 页 × ~1.3s，含重扫已落盘页）。
# 本批 2 块 × 1500，覆盖剩余量并留余量；timeout 2400s/块。
cd "D:/AI/work space/zcode" || exit 1
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/sh-12345-batch2.log
DATA="tools/gov-qa/data/sh-12345-上海市·12345热线诉求公开.jsonl"
: > "$LOG"
for i in 1 2; do
  echo "### chunk $i limit=1500 start $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
  timeout 2400 "$P" tools/gov-qa/harvest.py --site sh-12345 --limit 1500 >> "$LOG" 2>&1
  rc=$?
  echo "### chunk $i rc=$rc end $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
  if [ "$rc" -ne 0 ]; then
    echo "### chunk $i 非 0 退出（rc=$rc）⇒ 停批" >> "$LOG"
    break
  fi
  sleep 3
done
echo "### ALL DONE $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
