#!/usr/bin/env bash
# 扬州补采「前 100 页」（首块 9000s 超时只拿到 400 条）⇒ 拆成 4 个 25 页的小块
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/js-yangzhou-head.log; : > "$LOG"
F="tools/gov-qa/data/js-yangzhou-扬州市·政民互动·信件选登（jpaas-jact）.jsonl"
for pf in 1 26 51 76; do
  echo "### pf=$pf limit=500 $(date +%H:%M:%S)" >> "$LOG"
  GOVQA_PAGE_FROM=$pf timeout 5000 "$P" tools/gov-qa/harvest.py --site js-yangzhou --limit 500 >> "$LOG" 2>&1
  echo "### pf=$pf rc=$? 落盘 $(wc -l < "$F" 2>/dev/null || echo 0) $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
