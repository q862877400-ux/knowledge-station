#!/usr/bin/env bash
# 贵州 3 个「卡在 600 条页数硬顶」的厅局续采（2026-10-09 第 3 轮）
# 背景：_igi_common 的 max_pages 旧默认 30（30×20=600 条硬顶）+ 续采恒 0 ⇒ 死锁。
#       本轮已修（45ce28b）；本脚本在新默认下把顶上之外的数据取回来。
# 实测（修后）：gz-zrzy --limit 20 → 跳过已落盘 598、翻到第 31 页、新增 20。
# ★ timeout 必须 > limit × 单条耗时：新条约 1.2s + 跳页扫描约 1.2s/页。
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/gz-igi-extend-r3.log
: > "$LOG"
echo "### START $(date '+%m-%d %H:%M:%S')" >> "$LOG"
for spec in "gz-zrzy 500 2400" "gz-portal 500 2400" "gz-whhly 500 2400"; do
  set -- $spec
  echo "### $1 limit=$2 start $(date '+%H:%M:%S')" >> "$LOG"
  timeout "$3" "$P" tools/gov-qa/harvest.py --site "$1" --limit "$2" >> "$LOG" 2>&1
  echo "### $1 rc=$? end $(date '+%H:%M:%S')" >> "$LOG"
done
echo "### ALL DONE $(date '+%m-%d %H:%M:%S')" >> "$LOG"
