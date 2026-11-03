#!/bin/bash
# 贵州门户 IGI 全量采集（11 siteId / 2597 条）
# 用法: bash recon/gz-portal-harvest.sh
cd "$(dirname "$0")/.." || exit 1
P="D:/AI/work space/zcode/.venv/Scripts/python.exe"
LOG="recon/gz-portal-harvest.log"
echo "=== start $(date '+%F %T') ===" >> "$LOG"
timeout 2400 "$P" harvest.py --site gz-portal --limit 3000 >> "$LOG" 2>&1
echo "=== done rc=$? $(date '+%F %T') ===" >> "$LOG"
