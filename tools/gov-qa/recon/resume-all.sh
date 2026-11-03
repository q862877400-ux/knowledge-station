#!/usr/bin/env bash
# 重启后总续跑（2026-10-09 23:0x）—— 按「接近完成 → 未启动 → 大源」排序
# ⚠ harvest.py 只在跑完时落盘 ⇒ 一律分块/逐市，中断只损失当前块
cd "D:/AI/work space/zcode"; P=.venv/Scripts/python.exe; R=tools/gov-qa/recon
LOG=$R/resume-all.log; : > "$LOG"
say() { echo "### $* $(date '+%m-%d %H:%M:%S')" >> "$LOG"; }

# ① 烟台：差最后 2 块（15907/20000）
Y="tools/gov-qa/data/sd-yantai-烟台市·互动交流·网上民声（jact网关）.jsonl"
say "① 烟台 续 pf=849,955"
for pf in 849 955; do
  GOVQA_PAGE_FROM=$pf timeout 9000 "$P" tools/gov-qa/harvest.py --site sd-yantai --limit 2000 >> "$LOG" 2>&1
  say "   烟台 pf=$pf rc=$? 落盘 $(wc -l < "$Y" 2>/dev/null || echo 0)"
done

# ② 济宁：从未正式采（20/6909）
J=$(ls tools/gov-qa/data/sd-jining-*.jsonl 2>/dev/null | head -1)
say "② 济宁 4 块"
for pf in 1 107 213 319; do
  GOVQA_PAGE_FROM=$pf timeout 9000 "$P" tools/gov-qa/harvest.py --site sd-jining --limit 2000 >> "$LOG" 2>&1
  say "   济宁 pf=$pf rc=$? 落盘 $(wc -l < "$J" 2>/dev/null || echo 0)"
done

# ③ 广西 IGI（分片驱动，增量续采；上限 2 万）
say "③ 广西 IGI"
timeout 90000 "$P" "$R/igi-chunked.py" gx_igi --sites-json igi-siteid-guangxi.json --limit 20000 >> "$LOG" 2>&1
say "   广西 rc=$? 落盘 $(cat tools/gov-qa/data/gx-igi-*.jsonl 2>/dev/null | wc -l)"

# ④ 宁夏 IGI（13014）
say "④ 宁夏 IGI"
timeout 60000 "$P" "$R/igi-chunked.py" nx_igi --sites-json igi-siteid-ningxia.json --limit 14000 >> "$LOG" 2>&1
say "   宁夏 rc=$? 落盘 $(cat tools/gov-qa/data/nx-igi-*.jsonl 2>/dev/null | wc -l)"

# ⑤ 重庆 IGI（无上限，续采到 32580）
say "⑤ 重庆 IGI 续"
timeout 90000 "$P" "$R/igi-chunked.py" cq_igi --limit 33000 >> "$LOG" 2>&1
say "   重庆 rc=$? 落盘 $(cat tools/gov-qa/data/cq-igi-*.jsonl 2>/dev/null | wc -l)"

say "ALL DONE"
