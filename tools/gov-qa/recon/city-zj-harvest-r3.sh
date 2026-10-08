#!/usr/bin/env bash
# 浙江 11 地市·民呼我为·办理公开 —— 第 3 轮（本对话线，不与 city-zj-harvest.sh 共用日志）
# 背景：3a36909 建好 11 个适配器 + 抽验，但从未全量跑 ⇒ 11 个源零数据。
# 单条实测 1.75s（PAUSE 1.5s + 明细）；limit 350 ⇒ 约 620s/市，timeout 1800s 留足余量。
# ★ harvest.py 只在跑完时落盘 ⇒ timeout 必须 > limit × 单条耗时（踩过：被杀 = 整站零产出）。
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/city-zj-harvest-r3.log; : > "$LOG"
echo "### START $(date '+%m-%d %H:%M:%S')" >> "$LOG"
for c in zhoushan huzhou taizhou lishui quzhou shaoxing jiaxing jinhua wenzhou ningbo hangzhou; do
  echo "### zj-$c start $(date '+%H:%M:%S')" >> "$LOG"
  timeout 1800 "$P" tools/gov-qa/harvest.py --site "zj-$c" --limit 350 >> "$LOG" 2>&1
  echo "### zj-$c rc=$? end $(date '+%H:%M:%S')" >> "$LOG"
done
echo "### ALL DONE $(date '+%m-%d %H:%M:%S')" >> "$LOG"
