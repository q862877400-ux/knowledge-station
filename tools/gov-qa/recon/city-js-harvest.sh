#!/usr/bin/env bash
# 江苏 10 市（各自独立域名 ⇒ 串行但与其他省可并行）
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/city-js-harvest.log; : > "$LOG"
for c in nanjing wuxi xuzhou suzhou nantong yancheng yangzhou zhenjiang taizhou suqian; do
  echo "### js-$c $(date +%H:%M:%S)" >> "$LOG"
  timeout 7200 "$P" tools/gov-qa/harvest.py --site "js-$c" --limit 3000 >> "$LOG" 2>&1
  echo "### js-$c rc=$? $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
