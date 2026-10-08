#!/usr/bin/env bash
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/gap-hb-wuhan.log; : > "$LOG"
echo "### hb-wuhan limit=6600 timeout=11000s $(date +%H:%M:%S)" >> "$LOG"
timeout 11000 "$P" tools/gov-qa/harvest.py --site hb-wuhan --limit 6600 >> "$LOG" 2>&1
echo "### rc=$? $(date +%H:%M:%S)" >> "$LOG"
