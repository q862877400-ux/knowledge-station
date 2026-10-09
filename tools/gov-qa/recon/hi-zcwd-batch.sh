#!/usr/bin/env bash
# 海南 hi-zcwd（政策问答）续采批处理（2026-10-09 早场，作者=自动化定时任务对话）。
#
# 上游 allRow=2243 / totalPage=75，存量 205 ⇒ 还差约 2,038 条。
# 适配器 2026-10-09 补了 skip_ids（见 hi_zcwd.py 注释）：每轮从第 0 页重扫、已知 id 跳过明细。
# harvest.py **只在跑完时落盘** ⇒ 分块，每块独立 timeout，块内跑完即写盘。
# 单块 500 条 ≈ 16 分钟（明细 ≈1.8s/条 + 重扫 75 页开销）；timeout 2400s 留足余量。
cd "D:/AI/work space/zcode" || exit 1
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/hi-zcwd-batch.log
DATA="tools/gov-qa/data/hi-zcwd-海南省人民政府·政策问答.jsonl"
: > "$LOG"
for i in 1 2 3 4 5; do
  echo "### chunk $i limit=500 start $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
  timeout 2400 "$P" tools/gov-qa/harvest.py --site hi-zcwd --limit 500 >> "$LOG" 2>&1
  rc=$?
  echo "### chunk $i rc=$rc end $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
  if [ "$rc" -ne 0 ]; then
    echo "### chunk $i 非 0 退出（rc=$rc）⇒ 停批" >> "$LOG"
    break
  fi
  sleep 3
done
echo "### ALL DONE $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
