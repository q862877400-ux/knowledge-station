#!/usr/bin/env bash
# 四川地市州补采（2026-10-09 worker-city）
# 背景：第二批后台采集未落盘（内江/资阳/广安/甘孜/南充/遂宁/阿坝/绵阳/宜宾/攀枝花
#       只有 --limit 3~20 的测试数据）。本脚本逐市重跑，每市独立 timeout。
set -u
cd "$(dirname "$0")"
PY="../../.venv/Scripts/python.exe"
SITES="sc-mianyang sc-neijiang sc-ziyang sc-guangan sc-ganzi sc-nanchong sc-suining sc-aba sc-yibin sc-panzhihua"
for k in $SITES; do
  echo "==================== $k ===================="
  timeout 7200 "$PY" harvest.py --site "$k" --limit 3000
  echo "---- $k exit=$? ----"
done
echo "==== 补采全部结束 ===="
