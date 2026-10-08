#!/usr/bin/env bash
# 四川地市级 第二批（2026-10-09 worker-city）：内江/资阳/广安/甘孜/南充/遂宁/阿坝。
# 每市一次 harvest.py 运行、独立 timeout（--limit 3000）。
set -u
PY="D:/AI/work space/zcode/.venv/Scripts/python.exe"
cd "$(dirname "$0")" || exit 1
for k in sc-neijiang sc-ziyang sc-guangan sc-ganzi sc-nanchong sc-suining sc-aba; do
  echo "===== $(date '+%H:%M:%S') $k ====="
  timeout 7200 "$PY" harvest.py --site "$k" --limit 3000 2>&1 | tail -6
done
echo "===== ALL DONE $(date '+%H:%M:%S') ====="
