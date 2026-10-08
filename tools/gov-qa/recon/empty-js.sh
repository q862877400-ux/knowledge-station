#!/usr/bin/env bash
# 江苏省厅局空适配器首采（21 站）
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/empty-js.log; : > "$LOG"
JOBS="js-credit js-czt js-czt2 js-da js-da2 js-doc js-fzggw js-gxt js-gxt2 js-jsdk js-jsgd js-jsip js-jsip2 js-jsstyj js-jsstyj2 js-jssxfj js-jswater js-jtyst js-jtyst2 js-jyt js-jyt2 js-mzt js-nynct js-sthjt js-tj js-tj2 js-ybj js-ybj2"
for s in $JOBS; do
  echo "### $s limit=200 timeout=600s $(date +%H:%M:%S)" >> "$LOG"
  timeout 600 "$P" tools/gov-qa/harvest.py --site "$s" --limit 200 >> "$LOG" 2>&1
  echo "### $s rc=$? $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
