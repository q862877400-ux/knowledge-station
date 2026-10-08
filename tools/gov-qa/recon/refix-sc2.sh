#!/usr/bin/env bash
# 恢复被重采脚本误删的绵阳/内江数据（用已修复 answered_at 的适配器重采）
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/refix-sc2.log; : > "$LOG"
for j in "sc-mianyang:3000:7200" "sc-neijiang:3000:7200"; do
  s=${j%%:*}; rest=${j#*:}; lim=${rest%%:*}; to=${rest#*:}
  echo "### $s limit=$lim $(date +%H:%M:%S)" >> "$LOG"
  timeout "$to" "$P" tools/gov-qa/harvest.py --site "$s" --limit "$lim" >> "$LOG" 2>&1
  echo "### $s rc=$? $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
