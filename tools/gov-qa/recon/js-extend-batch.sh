#!/usr/bin/env bash
# 江苏「已有 200 条但存量更大」厅局的续采（与 js-zero-batch.sh 并行，目标 host 不同，互不影响）。
# 机制：jact 基座无「跳过已落盘 id」逻辑 ⇒ 从第 1 页重跑、由 harvest.py 按 (source,id) 去重，
#       故 limit 必须 >= 存量上限 + 本轮目标新增。timeout = limit × 2s + 120s 余量。
# 名册/实测 totalRecord：recon/js-jact-hunt.txt
cd "D:/AI/work space/zcode" || exit 1
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/js-extend-batch.log
: > "$LOG"

# key:limit:timeout
JOBS="js-da:720:1800 js-czt:460:1400 js-doc:400:1300"

for job in $JOBS; do
  s=${job%%:*}; rest=${job#*:}; lim=${rest%%:*}; to=${rest#*:}
  echo "### $s limit=$lim timeout=${to}s start $(date +%H:%M:%S)" >> "$LOG"
  timeout "$to" "$P" tools/gov-qa/harvest.py --site "$s" --limit "$lim" >> "$LOG" 2>&1
  echo "### $s rc=$? end $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
