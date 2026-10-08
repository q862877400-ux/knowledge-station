#!/usr/bin/env bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/hb-harvest.log
: > "$LOG"
JOBS="hb-hdjl:150:600 hb-wuhan:200:900"
for job in $JOBS; do
  s=${job%%:*}; rest=${job#*:}; lim=${rest%%:*}; to=${rest#*:}
  echo "### $s limit=$lim timeout=${to}s $(date +%H:%M:%S)" >> "$LOG"
  timeout "$to" "$P" tools/gov-qa/harvest.py --site "$s" --limit "$lim" >> "$LOG" 2>&1
  echo "### $s 退出码=$? $(date +%H:%M:%S)" >> "$LOG"
done
echo "=== 湖北完成 $(date) ===" >> "$LOG"
