#!/usr/bin/env bash
# 甘肃首批剩余（白银/定西）重跑（worker-gansu）。前次被环境中止，零产出。
# 张掖 7776 条 >2000，按 team-lead 要求先不裸跑，待商量分块策略。
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOGDIR=tools/gov-qa/recon
run_one() {
  local s="$1" lim="$2" to="$3"
  local log="$LOGDIR/gs2-harvest-$s.log"
  : > "$log"
  echo "### $s limit=$lim timeout=${to}s start=$(date +%H:%M:%S)" >> "$log"
  timeout "$to" "$P" -u tools/gov-qa/harvest.py --site "$s" --limit "$lim" >> "$log" 2>&1
  echo "### $s rc=$? end=$(date +%H:%M:%S)" >> "$log"
}
run_one gs-baiyin 2000 7200 &
run_one gs-dingxi  800 3600 &
wait
echo "### DONE $(date +%H:%M:%S)" >> "$LOGDIR/gs2-harvest-ALL.log"
