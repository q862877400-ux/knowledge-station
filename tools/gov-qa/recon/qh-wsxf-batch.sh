#!/usr/bin/env bash
# 青海 qh-wsxf（群众诉求回应）续采批处理（2026-10-09 早场，作者=自动化定时任务对话）。
#
# 上游 27 页 × ~19 条 ≈ 513；存量 205 ⇒ 还差约 308 条。
# 适配器 2026-10-09 补了 skip_ids（见 qh_wsxf.py 注释）：每轮从第 1 页重扫、已知 id 跳过明细。
# harvest.py **只在跑完时落盘** ⇒ 分块，每块独立 timeout，块内跑完即写盘。
# 单块 200 条 ≈ 6 分钟（明细 ≈1.5s/条 + 27 页重扫开销）；timeout 1800s 留足余量。
cd "D:/AI/work space/zcode" || exit 1
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/qh-wsxf-batch.log
DATA="tools/gov-qa/data/qh-wsxf-青海省·互动交流·群众诉求回应.jsonl"
: > "$LOG"
for i in 1 2; do
  echo "### chunk $i limit=200 start $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
  timeout 1800 "$P" tools/gov-qa/harvest.py --site qh-wsxf --limit 200 >> "$LOG" 2>&1
  rc=$?
  echo "### chunk $i rc=$rc end $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
  if [ "$rc" -ne 0 ]; then
    echo "### chunk $i 非 0 退出（rc=$rc）⇒ 停批" >> "$LOG"
    break
  fi
  sleep 3
done
echo "### ALL DONE $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
