#!/usr/bin/env bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/hb-wuhan-harvest.log
: > "$LOG"
echo "### hb-wuhan limit=300 timeout=1200s $(date +%H:%M:%S)" >> "$LOG"
timeout 1200 "$P" tools/gov-qa/harvest.py --site hb-wuhan --limit 300 >> "$LOG" 2>&1
echo "### hb-wuhan 退出码=$? $(date +%H:%M:%S)" >> "$LOG"
