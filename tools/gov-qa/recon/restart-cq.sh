#!/usr/bin/env bash
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/restart-cq.log; echo "### cq-igi $(date +%H:%M:%S)" >> "$LOG"
timeout 60000 "$P" $R/igi-chunked-harvest.py cq_igi >> "$LOG" 2>&1
echo "### rc=$? $(date +%H:%M:%S)" >> "$LOG"
