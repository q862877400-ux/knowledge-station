#!/usr/bin/env bash
# 续采 山西/广西/宁夏 IGI（分片驱动，逐 siteId 落盘，中断只损失当前 siteId）
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
R=tools/gov-qa/recon
LOG=$R/igi-resume.log
: > "$LOG"
run() {  # name sites-json limit timeout
  local n=$1 sj=$2 lim=$3 to=$4
  echo "### $n limit=$lim timeout=${to}s $(date +%H:%M:%S)" >> "$LOG"
  timeout "$to" "$P" "$R/igi-chunked.py" "$n" --sites-json "$sj" --limit "$lim" >> "$LOG" 2>&1
  echo "### $n rc=$? $(date +%H:%M:%S)" >> "$LOG"
}
# 单源上限 2 万（边际价值在多样性，不在体量）
run sx_igi igi-siteid-shanxi.json   20000 90000
run gx_igi igi-siteid-guangxi.json  20000 90000
run nx_igi igi-siteid-ningxia.json  14000 60000
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
