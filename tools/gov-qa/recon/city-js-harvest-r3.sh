#!/usr/bin/env bash
# 江苏地市 —— 第 3 轮（本对话线）
#
# ⚠ 2026-10-09 02:3x 现场避让记录：
#   另一个对话在跑 recon/city-js-harvest.sh（limit 3000/市），固定顺序：
#     南京→无锡→徐州→苏州→南通→盐城→扬州→镇江→泰州→宿迁
#   02:30 现场确认它正在跑 `js-yancheng --limit 3000`（第 6 个）。
#   ⇒ 本脚本**不碰盐城**（正被它跑）、不碰南京/无锡/徐州/苏州/南通（已有数据）；
#     只补 泰州（它第 9 个）、扬州（第 7 个），时间窗不重叠：
#       它扬州 03:32 起、泰州 05:27 起；本脚本 02:4x 前收工。
#
# 已落盘：宿迁 41（该站接口实际只暴露 40 条唯一记录，见台账）、镇江 460。
# ★ timeout 必须 > limit × 单条耗时（实测 jact 系约 2s/条）。
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/city-js-harvest-r3.log
: > "$LOG"
echo "### START(r3-remainder) $(date '+%m-%d %H:%M:%S')" >> "$LOG"
for spec in "js-taizhou 500 1800" "js-yangzhou 400 1800"; do
  set -- $spec
  echo "### $1 limit=$2 start $(date '+%H:%M:%S')" >> "$LOG"
  timeout "$3" "$P" tools/gov-qa/harvest.py --site "$1" --limit "$2" >> "$LOG" 2>&1
  echo "### $1 rc=$? end $(date '+%H:%M:%S')" >> "$LOG"
done
echo "### ALL DONE $(date '+%m-%d %H:%M:%S')" >> "$LOG"
