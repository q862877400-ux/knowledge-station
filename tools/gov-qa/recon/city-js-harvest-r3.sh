#!/usr/bin/env bash
# 江苏 5 个零数据地市（本对话线；独立日志，不与 city-js-harvest.sh 共用）
# 背景：江苏 10 市适配器已建，前 5 市（南京/无锡/徐州/苏州/南通）已有数据，
#       后 5 市（盐城/扬州/镇江/泰州/宿迁）零数据 —— 本脚本只补这 5 个。
# 实测：单条约 2s（jact 系）；宿迁列表即含正文，明显更快。
# ★ timeout 必须 > limit × 单条耗时（harvest.py 只在跑完时落盘）。
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/city-js-harvest-r3.log; : > "$LOG"
echo "### START $(date '+%m-%d %H:%M:%S')" >> "$LOG"
for spec in "js-suqian 1400 3600" "js-zhenjiang 460 2400" "js-yancheng 500 2400" "js-taizhou 500 2400" "js-yangzhou 500 2400"; do
  set -- $spec
  echo "### $1 limit=$2 start $(date '+%H:%M:%S')" >> "$LOG"
  timeout "$3" "$P" tools/gov-qa/harvest.py --site "$1" --limit "$2" >> "$LOG" 2>&1
  echo "### $1 rc=$? end $(date '+%H:%M:%S')" >> "$LOG"
done
echo "### ALL DONE $(date '+%m-%d %H:%M:%S')" >> "$LOG"
