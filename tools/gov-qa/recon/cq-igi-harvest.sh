#!/usr/bin/env bash
# 重庆 IGI 全量采集（75 site / 约 3.26 万条，约 13-15 小时）
# 用分片驱动：逐 siteId 落盘，中断只损失当前一个 siteId（harvest.py 会零产出）
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
LOG=tools/gov-qa/recon/cq-igi-harvest.log
echo "### cq-igi 全量 $(date +%H:%M:%S) ===" >> "$LOG"
timeout 60000 "$P" tools/gov-qa/recon/igi-chunked-harvest.py cq_igi >> "$LOG" 2>&1
echo "### rc=$? $(date +%H:%M:%S)" >> "$LOG"
