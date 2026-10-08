#!/usr/bin/env bash
# 浙江 11 市（民呼我为统一平台，同一域名 ⇒ 必须串行）
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/city-zj-harvest.log; : > "$LOG"
for c in hangzhou ningbo wenzhou jiaxing huzhou shaoxing jinhua quzhou zhoushan taizhou lishui; do
  echo "### zj-$c $(date +%H:%M:%S)" >> "$LOG"
  timeout 7200 "$P" tools/gov-qa/harvest.py --site "zj-$c" --limit 3000 >> "$LOG" 2>&1
  echo "### zj-$c rc=$? $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
