#!/usr/bin/env bash
# 烟台(目标 2 万) + 济宁(6909) —— 两者此前都只有抽验的 20 条
# ⚠ 必须分块：harvest.py 跑完才落盘，裸跑会被 timeout 杀掉 ⇒ 零产出
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/sd-bigcity.log; : > "$LOG"
Y=tools/gov-qa/data/sd-yantai-烟台市·互动交流·网上民声（jact网关）.jsonl
J=$(ls tools/gov-qa/data/sd-jining-*.jsonl 2>/dev/null | head -1)

echo "### 烟台 10 块 × 2000（上限 2 万）$(date +%H:%M:%S)" >> "$LOG"
for pf in 1 107 213 319 425 531 637 743 849 955; do
  GOVQA_PAGE_FROM=$pf timeout 9000 "$P" tools/gov-qa/harvest.py --site sd-yantai --limit 2000 >> "$LOG" 2>&1
  echo "### 烟台 pf=$pf rc=$? 落盘 $(wc -l < "$Y" 2>/dev/null || echo 0) $(date +%H:%M:%S)" >> "$LOG"
done

echo "### 济宁 4 块 × 2000 $(date +%H:%M:%S)" >> "$LOG"
for pf in 1 107 213 319; do
  GOVQA_PAGE_FROM=$pf timeout 9000 "$P" tools/gov-qa/harvest.py --site sd-jining --limit 2000 >> "$LOG" 2>&1
  echo "### 济宁 pf=$pf rc=$? 落盘 $(wc -l < "$J" 2>/dev/null || echo 0) $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
