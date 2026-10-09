#!/usr/bin/env bash
# 扬州分块采（count=7837，pageSize=20 ⇒ 392 页）
# ⚠ 上次裸跑 24000s 被 timeout 杀掉、零产出 ⇒ 改按 100 页一块，每块跑完即落盘
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/js-yangzhou-chunk.log; : > "$LOG"
for pf in 1 101 201 301; do
  echo "### js-yangzhou page_from=$pf limit=2000 $(date +%H:%M:%S)" >> "$LOG"
  GOVQA_PAGE_FROM=$pf timeout 9000 "$P" tools/gov-qa/harvest.py --site js-yangzhou --limit 2000 >> "$LOG" 2>&1
  echo "### page_from=$pf rc=$? 落盘 $(wc -l < "tools/gov-qa/data/js-yangzhou-扬州市·政民互动·信件选登（jpaas-jact）.jsonl" 2>/dev/null || echo 0) 条 $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
