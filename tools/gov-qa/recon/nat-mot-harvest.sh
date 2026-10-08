#!/usr/bin/env bash
# 交通部：IP 级反爬敏感（~30 请求即 403）⇒ 每批 500 条、批间歇 30 分钟、上限 5,000
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/nat-mot-harvest.log; : > "$LOG"
for pf in 1 26 51 76 101; do
  echo "### nat-mot page_from=$pf $(date +%H:%M:%S)" >> "$LOG"
  GOVQA_PAGE_FROM=$pf timeout 2400 "$P" tools/gov-qa/harvest.py --site nat-mot --limit 500 >> "$LOG" 2>&1
  echo "### page_from=$pf rc=$? $(date +%H:%M:%S)" >> "$LOG"
  sleep 1800
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
