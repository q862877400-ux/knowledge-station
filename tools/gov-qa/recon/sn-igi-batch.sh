#!/usr/bin/env bash
# 陕西 sn-igi 续采批处理（2026-10-09 早场，作者=自动化定时任务对话）。
#
# 上游 totalResults=4097，已落 810 ⇒ 还差约 3,287 条。
# IGI 明细 ≈1.3s/条；另每轮要从第 1 页重扫到新数据起点（已知 id 跳过明细、只费列表请求）。
# harvest.py **只在跑完时落盘** ⇒ 必须分块，每块独立 timeout，块内跑完即写盘。
# 单块 600 条 ≈ 15 分钟；timeout 2400s 留足余量（> 600 × 2.3s + 重扫开销）。
cd "D:/AI/work space/zcode" || exit 1
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/sn-igi-batch.log
DATA="tools/gov-qa/data/sn-igi-陕西省·我向省长说句话（IGI）.jsonl"
: > "$LOG"
for i in 1 2 3 4 5 6; do
  echo "### chunk $i limit=600 start $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
  timeout 2400 "$P" tools/gov-qa/harvest.py --site sn-igi --limit 600 >> "$LOG" 2>&1
  rc=$?
  echo "### chunk $i rc=$rc end $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
  if [ "$rc" -ne 0 ]; then
    echo "### chunk $i 非 0 退出（rc=$rc）⇒ 停批，避免空转" >> "$LOG"
    break
  fi
  sleep 3
done
echo "### ALL DONE $(date +%H:%M:%S) lines=$(wc -l < "$DATA")" >> "$LOG"
