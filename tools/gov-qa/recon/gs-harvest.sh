#!/usr/bin/env bash
# 甘肃 4 市州全量采集（worker-gansu）。
# 逐站独立 timeout，4 站**并行**（分属 4 个不同域名，各自适配器已按 ≥1.5s/条 限速）。
# ⚠ harvest.py 只在跑完时落盘 ⇒ timeout 必须 > 条数 × 单条耗时，否则整站零产出。
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOGDIR=tools/gov-qa/recon
run_one() {
  local s="$1" lim="$2" to="$3"
  local log="$LOGDIR/gs-harvest-$s.log"
  : > "$log"
  echo "### $s limit=$lim timeout=${to}s start=$(date +%H:%M:%S)" >> "$log"
  timeout "$to" "$P" -u tools/gov-qa/harvest.py --site "$s" --limit "$lim" >> "$log" 2>&1
  echo "### $s rc=$? end=$(date +%H:%M:%S)" >> "$log"
}
run_one gs-zhangye 8000  18000 &
run_one gs-baiyin  2000   7200 &
run_one gs-dingxi   800   3600 &
run_one gs-longnan  500    900 &
wait
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOGDIR/gs-harvest-ALL.log"
