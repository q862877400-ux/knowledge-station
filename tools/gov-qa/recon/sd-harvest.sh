#!/usr/bin/env bash
# 山东地市全量采集（逐站独立 timeout，卡住即跳过）。
# ⚠ harvest.py 跑完才落盘：timeout 必须 > limit × 单条耗时(1.6-2.3s)，否则整站零产出。
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/sd-harvest.log
JOBS="sd-dongying:30000:43200"
for job in $JOBS; do
  s=${job%%:*}; rest=${job#*:}; lim=${rest%%:*}; to=${rest#*:}
  echo "### $s limit=$lim timeout=${to}s $(date +%F_%H:%M:%S)" >> "$LOG"
  timeout "$to" "$P" tools/gov-qa/harvest.py --site "$s" --limit "$lim" >> "$LOG" 2>&1
  echo "### $s rc=$? $(date +%F_%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%F_%H:%M:%S)" >> "$LOG"
