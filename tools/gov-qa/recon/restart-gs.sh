#!/usr/bin/env bash
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/restart-gs.log; echo "### gs-zhangye $(date +%H:%M:%S)" >> "$LOG"
timeout 30000 "$P" $R/igi-chunked-harvest.py gs_zhangye >> "$LOG" 2>&1
echo "### zhangye rc=$? $(date +%H:%M:%S)" >> "$LOG"
echo "### gs-dingxi $(date +%H:%M:%S)" >> "$LOG"
timeout 4000 "$P" tools/gov-qa/harvest.py --site gs-dingxi --limit 800 >> "$LOG" 2>&1
echo "### dingxi rc=$? $(date +%H:%M:%S)" >> "$LOG"
echo "### gs-baiyin $(date +%H:%M:%S)" >> "$LOG"
timeout 9000 "$P" tools/gov-qa/harvest.py --site gs-baiyin --limit 2000 >> "$LOG" 2>&1
echo "### baiyin rc=$? $(date +%H:%M:%S)" >> "$LOG"
