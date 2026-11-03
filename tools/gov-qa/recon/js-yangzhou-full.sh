#!/usr/bin/env bash
# 扬州全量（7837 条，jpaas-jact）。上次 7200s 超时 ⇒ 本次给 24000s
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/js-yangzhou-full.log; : > "$LOG"
echo "### js-yangzhou limit=8000 timeout=24000s $(date +%H:%M:%S)" >> "$LOG"
timeout 24000 "$P" tools/gov-qa/harvest.py --site js-yangzhou --limit 8000 >> "$LOG" 2>&1
echo "### rc=$? $(date +%H:%M:%S)" >> "$LOG"
