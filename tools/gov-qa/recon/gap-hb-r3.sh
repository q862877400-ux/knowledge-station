#!/usr/bin/env bash
# 湖北深度补采（第 3 轮）——hb-hdjl 与 hb-wuhan 是**两个独立域名**，可并行。
# 背景：两个适配器原来**不传 skip_ids** ⇒ IGI 无游标列表每轮从第 1 页重跑、
#       limit 被旧条目吃掉、恒 0 新增（实测 hb-hdjl --limit 5 → 新增 0）。
#       2026-10-09 已修（同 sn_igi/xz_igi 的修法）；本脚本在修好之后跑。
# ★ timeout 必须 > limit × 单条耗时：实测含跳页开销约 1.5~2s/新条 ⇒ 留 2.5 倍余量。
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon

timeout 6600 "$P" tools/gov-qa/harvest.py --site hb-hdjl --limit 2200 \
  > "$R/gap-hb-hdjl-r3.log" 2>&1 &
PID1=$!
timeout 9000 "$P" tools/gov-qa/harvest.py --site hb-wuhan --limit 3000 \
  > "$R/gap-hb-wuhan-r3.log" 2>&1 &
PID2=$!

echo "### started $(date '+%m-%d %H:%M:%S') pids=$PID1,$PID2"
wait $PID1; echo "### hb-hdjl rc=$? end $(date '+%H:%M:%S')"
wait $PID2; echo "### hb-wuhan rc=$? end $(date '+%H:%M:%S')"
echo "### ALL DONE $(date '+%m-%d %H:%M:%S')"
