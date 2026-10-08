#!/usr/bin/env bash
# 江苏 12 个「已登记 / status=ok / 零数据」厅局首采。
# 硬约束：harvest.py 只在跑完时落盘 ⇒ timeout 必须 > limit × 单条耗时（实测 ~1.5s/条）。
#   limit=200 ⇒ 300s 采数 + 列表分页 ~20s；留 3 倍余量 ⇒ timeout=900s。
# 站点按实测 totalRecord 从小到大排，先落盘小站、再啃大站。
# 证据/名册：recon/js-jact-hunt.txt
cd "D:/AI/work space/zcode" || exit 1
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/js-zero-batch.log
: > "$LOG"

# key:实测 totalRecord
JOBS="js-jtyst2 js-tj js-mzt js-nynct js-ybj2 js-jyt2 js-sthjt js-jswater js-tj2 js-ybj js-jyt js-jtyst"

for s in $JOBS; do
  echo "### $s limit=200 timeout=900s start $(date +%H:%M:%S)" >> "$LOG"
  timeout 900 "$P" tools/gov-qa/harvest.py --site "$s" --limit 200 >> "$LOG" 2>&1
  echo "### $s rc=$? end $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
