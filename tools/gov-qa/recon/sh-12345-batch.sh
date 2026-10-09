#!/usr/bin/env bash
# 上海 sh-12345（12345 诉求公开）续采批处理（2026-10-09 早场，作者=自动化定时任务对话）。
#
# 上游 count=7248（每页 15 条 ⇒ 484 页），存量 610 ⇒ 还差约 6,638 条。
# 适配器 2026-10-09 补了 skip_ids（见 sh_12345.py 注释）：每轮从第 1 页重扫、已知 rpid 不计入 limit。
# 列表页已带问题+答复全文 ⇒ **无逐条明细请求**，整轮 ≈ 484 页 × ~1.3s ≈ 11 分钟。
# harvest.py **只在跑完时落盘** ⇒ 仍分块，块内跑完即写盘。
cd "D:/AI/work space/zcode" || exit 1
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/sh-12345-batch.log
DATA="tools/gov-qa/data/sh-12345-上海市·12345热线诉求公开.jsonl"
: > "$LOG"
for i in 1 2 3; do
  echo "### chunk $i limit=2500 start $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
  timeout 2400 "$P" tools/gov-qa/harvest.py --site sh-12345 --limit 2500 >> "$LOG" 2>&1
  rc=$?
  echo "### chunk $i rc=$rc end $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
  if [ "$rc" -ne 0 ]; then
    echo "### chunk $i 非 0 退出（rc=$rc）⇒ 停批" >> "$LOG"
    break
  fi
  sleep 3
done
echo "### ALL DONE $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
