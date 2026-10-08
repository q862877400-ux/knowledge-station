#!/usr/bin/env bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/xz-harvest.log
: > "$LOG"
echo "### xz-igi limit=400 timeout=900s $(date +%H:%M:%S)" >> "$LOG"
timeout 900 "$P" tools/gov-qa/harvest.py --site xz-igi --limit 400 >> "$LOG" 2>&1
echo "### xz-igi 退出码=$? $(date +%H:%M:%S)" >> "$LOG"
