#!/usr/bin/env bash
# 待办采集：贵州门户 / 陕西 IGI / 西藏 IGI（逐站独立 timeout，卡住即跳过）
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/pending-harvest.log
: > "$LOG"
JOBS="gz-portal:3000:3000 sn-igi:4000:5400 xz-igi:400:900"
for job in $JOBS; do
  s=${job%%:*}; rest=${job#*:}; lim=${rest%%:*}; to=${rest#*:}
  echo "### $s limit=$lim timeout=${to}s $(date +%H:%M:%S)" >> "$LOG"
  timeout "$to" "$P" tools/gov-qa/harvest.py --site "$s" --limit "$lim" >> "$LOG" 2>&1
  echo "### $s rc=$? $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
