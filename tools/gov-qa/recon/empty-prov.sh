#!/usr/bin/env bash
# 省级门户空适配器首采（9 站）
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/empty-prov.log; : > "$LOG"
JOBS="bj-hdjl cq-hdjl fj-hdjl hlj-hdjl hn-hdjl nmg-xinxiang jx-zf yn-xf zj-mhww"
for s in $JOBS; do
  echo "### $s limit=500 timeout=1800s $(date +%H:%M:%S)" >> "$LOG"
  timeout 1800 "$P" tools/gov-qa/harvest.py --site "$s" --limit 500 >> "$LOG" 2>&1
  echo "### $s rc=$? $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
