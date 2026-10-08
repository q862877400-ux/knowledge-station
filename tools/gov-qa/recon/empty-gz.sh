#!/usr/bin/env bash
# 贵州省直空适配器首采（6 站）
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/empty-gz.log; : > "$LOG"
JOBS="gz-jdglj gz-jkj gz-jyglj gz-stymj gz-wsb gz-wsg"
for s in $JOBS; do
  echo "### $s limit=300 timeout=900s $(date +%H:%M:%S)" >> "$LOG"
  timeout 900 "$P" tools/gov-qa/harvest.py --site "$s" --limit 300 >> "$LOG" 2>&1
  echo "### $s rc=$? $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
