#!/usr/bin/env bash
# 浙江地市·民呼我为 —— 第 3 轮（本对话线）
#
# ⚠ 2026-10-09 02:3x 现场避让记录：
#   另一个对话在 00:53 启动了 recon/city-zj-harvest.sh（limit 3000/市），
#   杭州 02:23 完成（3000 条），随后按**固定顺序**推进：
#     杭州→宁波→温州→嘉兴→湖州→绍兴→金华→衢州→舟山→台州→丽水
#   每市约 83 分钟（limit 3000 且总量够）。
#   ⇒ 本脚本**只跑它 4 小时之后才会轮到的市**，且每市 10 分钟内跑完，
#     时间窗不重叠（最早冲突点：嘉兴，它 05:09 才到；本脚本 03:3x 收工）。
#   ⇒ 它已覆盖的杭州/宁波/温州（03:46 前到）本脚本一律不碰；
#     嘉兴它 05:09 才到、本脚本 03:3x 收工（余量 1.5h），故保留；
#     舟山/湖州已由本轮先落地（370 / 350 条），不重复。
#
# ★ harvest.py 只在跑完时落盘 ⇒ timeout 必须 > limit × 单条耗时（实测 1.75s/条）。
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/city-zj-harvest-r3.log
: > "$LOG"
echo "### START(r3-remainder) $(date '+%m-%d %H:%M:%S')" >> "$LOG"
for c in taizhou lishui quzhou shaoxing jinhua jiaxing; do
  echo "### zj-$c start $(date '+%H:%M:%S')" >> "$LOG"
  timeout 1200 "$P" tools/gov-qa/harvest.py --site "zj-$c" --limit 350 >> "$LOG" 2>&1
  echo "### zj-$c rc=$? end $(date '+%H:%M:%S')" >> "$LOG"
done
echo "### ALL DONE $(date '+%m-%d %H:%M:%S')" >> "$LOG"
