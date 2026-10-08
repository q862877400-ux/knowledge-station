#!/usr/bin/env bash
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/gap-misc.log; : > "$LOG"
for job in "heb-szj:1100:2400" "xj-dchs:300:600"; do
  s=${job%%:*}; rest=${job#*:}; lim=${rest%%:*}; to=${rest#*:}
  echo "### $s limit=$lim timeout=${to}s $(date +%H:%M:%S)" >> "$LOG"
  timeout "$to" "$P" tools/gov-qa/harvest.py --site "$s" --limit "$lim" >> "$LOG" 2>&1
  echo "### $s rc=$? $(date +%H:%M:%S)" >> "$LOG"
done
