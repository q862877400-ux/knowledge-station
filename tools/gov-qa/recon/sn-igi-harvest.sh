#!/usr/bin/env bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/sn-igi-harvest.log
: > "$LOG"
echo "### sn-igi limit=1500 timeout=3600s $(date +%H:%M:%S)" >> "$LOG"
timeout 3600 "$P" tools/gov-qa/harvest.py --site sn-igi --limit 1500 >> "$LOG" 2>&1
echo "### sn-igi 退出码=$? $(date +%H:%M:%S)" >> "$LOG"
