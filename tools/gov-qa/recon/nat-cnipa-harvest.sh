#!/usr/bin/env bash
# 知识产权局：上限约 20,000 条。先小 sysid（12/16）再大 sysid（11），sysid 6(13.7万) 不采
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/nat-cnipa-harvest.log; : > "$LOG"
run() { echo "### cnipa sysid=$1 pf=$2 $(date +%H:%M:%S)" >> "$LOG"
  GOVQA_CNIPA_SYSIDS=$1 GOVQA_PAGE_FROM=$2 timeout 7000 "$P" tools/gov-qa/harvest.py --site nat-cnipa --limit 2000 >> "$LOG" 2>&1
  echo "### rc=$? $(date +%H:%M:%S)" >> "$LOG"; }
run 12 1                                    # 464 条，一次采完
run 16 1; run 16 101; run 16 201            # 5,947
run 11 1; run 11 101; run 11 201; run 11 301; run 11 401; run 11 501; run 11 601   # 14,369
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
