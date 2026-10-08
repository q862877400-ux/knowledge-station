#!/usr/bin/env bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/hb-rst-harvest.log
: > "$LOG"
echo "### hb-rst limit=100 timeout=300s $(date +%H:%M:%S)" >> "$LOG"
timeout 300 "$P" tools/gov-qa/harvest.py --site hb-rst --limit 100 >> "$LOG" 2>&1
echo "### hb-rst 退出码=$? $(date +%H:%M:%S)" >> "$LOG"
