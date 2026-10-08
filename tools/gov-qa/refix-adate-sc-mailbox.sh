#!/usr/bin/env bash
# 重采 内江/绵阳 以补 answered_at（2026-10-09 worker-city）
# 背景：这两个「通信平台 api-mailbox」源首批采集时适配器硬编码 answered_at=None，
#       已修（commit 64eff42，取 replyContents[].replyTime）。此处重采覆盖旧文件。
# 安全姿势：旧文件先备份到 /tmp（不进代码树）→ 重采 → 新文件条数不足则回滚。
set -u
cd "$(dirname "$0")"
PY="../../.venv/Scripts/python.exe"
D="data"
BK="/tmp/sc-adate-backup"
mkdir -p "$BK"

reharvest() {
  local key="$1" file="$2"
  if [ ! -f "$file" ]; then echo "!! 缺 $file"; return 1; fi
  local old_n; old_n=$(wc -l < "$file")
  local bak="$BK/$(basename "$file").pre-adate"
  mv "$file" "$bak"
  echo "== $key 旧 $old_n 条已备份 → $bak"
  timeout 7200 "$PY" harvest.py --site "$key" --limit 3000
  local new_n; new_n=$(wc -l < "$file" 2>/dev/null || echo 0)
  if [ "$new_n" -lt "$old_n" ]; then
    echo "!! $key 重采 $new_n < 原 $old_n —— 回滚到备份"
    rm -f "$file"; mv "$bak" "$file"
  else
    echo "== $key 重采成功 $new_n 条（原 $old_n；备份保留 $bak）"
  fi
}

reharvest sc-neijiang "$D/sc-neijiang-内江市·互动交流·书记市长网上政务信箱.jsonl"
reharvest sc-mianyang "$D/sc-mianyang-绵阳市·互动交流·书记市长信箱.jsonl"
echo "==== adate 重采结束 ===="
