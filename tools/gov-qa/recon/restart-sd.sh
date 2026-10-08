#!/usr/bin/env bash
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/restart-sd.log; echo "### sd-dongying $(date +%H:%M:%S)" >> "$LOG"
timeout 43200 "$P" tools/gov-qa/harvest.py --site sd-dongying --limit 30000 >> "$LOG" 2>&1
echo "### rc=$? $(date +%H:%M:%S)" >> "$LOG"
