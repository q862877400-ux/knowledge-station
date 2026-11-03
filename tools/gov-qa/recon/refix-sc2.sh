#!/usr/bin/env bash
# 绵阳/内江 重采（用已修复 answered_at 的适配器；旧文件已 commit 到 git 后再删）
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/refix-sc2.log; : > "$LOG"
for j in "sc-mianyang:6000:14000" "sc-neijiang:4000:9000"; do
  s=${j%%:*}; rest=${j#*:}; lim=${rest%%:*}; to=${rest#*:}
  echo "### $s limit=$lim timeout=${to}s $(date +%H:%M:%S)" >> "$LOG"
  timeout "$to" "$P" tools/gov-qa/harvest.py --site "$s" --limit "$lim" >> "$LOG" 2>&1
  echo "### $s rc=$? $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
