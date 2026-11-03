#!/usr/bin/env bash
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/heb-szj-full.log; : > "$LOG"
echo "### heb-szj limit=1200 timeout=4500s $(date +%H:%M:%S)" >> "$LOG"
timeout 4500 "$P" tools/gov-qa/harvest.py --site heb-szj --limit 1200 >> "$LOG" 2>&1
echo "### rc=$? $(date +%H:%M:%S)" >> "$LOG"
