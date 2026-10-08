#!/usr/bin/env bash
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/gap-hb-hdjl.log; : > "$LOG"
echo "### hb-hdjl limit=3600 timeout=7000s $(date +%H:%M:%S)" >> "$LOG"
timeout 7000 "$P" tools/gov-qa/harvest.py --site hb-hdjl --limit 3600 >> "$LOG" 2>&1
echo "### rc=$? $(date +%H:%M:%S)" >> "$LOG"
