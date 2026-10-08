#!/usr/bin/env bash
# 稳健批量采集：每站独立超时，卡住即跳过
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/batch-harvest.log
: > "$LOG"
# 格式：site:limit:timeout秒
JOBS="heb-czt:100:300 heb-szj:150:600 gx-mailbox:200:400 sd-12345:100:300 qh-wsxf:200:500 hi-zcwd:200:600 xj-dchs:100:400"
for job in $JOBS; do
  s=${job%%:*}; rest=${job#*:}; lim=${rest%%:*}; to=${rest#*:}
  echo "### $s limit=$lim timeout=${to}s $(date +%H:%M:%S)" >> "$LOG"
  timeout "$to" "$P" tools/gov-qa/harvest.py --site "$s" --limit "$lim" >> "$LOG" 2>&1
  rc=$?
  echo "### $s 退出码=$rc $(date +%H:%M:%S)" >> "$LOG"
done
echo "=== 全部完成 $(date) ===" >> "$LOG"
