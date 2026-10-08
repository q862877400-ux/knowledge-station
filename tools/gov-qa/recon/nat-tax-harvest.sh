#!/usr/bin/env bash
# 税务总局 12366：上限 20,000 条。pageSize 被服务端锁死为 8 ⇒ 2,000 条 = 250 页
# 10 批，每批一次 harvest.py 运行（跑完即落盘，中断只损失当前批）
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/nat-tax-harvest.log; : > "$LOG"
for pf in 1 251 501 751 1001 1251 1501 1751 2001 2251; do
  echo "### nat-tax page_from=$pf $(date +%H:%M:%S)" >> "$LOG"
  GOVQA_PAGE_FROM=$pf timeout 7000 "$P" tools/gov-qa/harvest.py --site nat-tax --limit 2000 >> "$LOG" 2>&1
  echo "### page_from=$pf rc=$? $(date +%H:%M:%S)" >> "$LOG"
done
echo "### ALL DONE $(date +%H:%M:%S)" >> "$LOG"
