#!/usr/bin/env bash
# 四川政务服务网「政民互动」20 市州补源 · 串行采集
# ---------------------------------------------------------------------------
# 20 市打**同一平台**（www.sczwfw.gov.cn）⇒ **必须串行**（PAUSE 保持默认 0.8s）。
# 逐市独立调用 harvest.py、独立 timeout：harvest.py 只在跑完时落盘，逐市跑
# 保证「中断只损失当前市」，已完成的市立刻落盘。
#
# 用法： bash tools/gov-qa/recon/sc-zwfw-harvest.sh [CAP]
#   CAP 每市上限（默认 3000，均大于各市总量）
# ---------------------------------------------------------------------------
set -u
cd "$(dirname "$0")/../../.." || exit 1          # → 仓库根（zcode）
P=".venv/Scripts/python.exe"
HARVEST="tools/gov-qa/harvest.py"
CAP="${1:-3000}"

KEYS=(
  sc-zigong-zwfw sc-panzhihua-zwfw sc-luzhou-zwfw sc-deyang-zwfw sc-mianyang-zwfw
  sc-guangyuan-zwfw sc-suining-zwfw sc-neijiang-zwfw sc-leshan-zwfw sc-nanchong-zwfw
  sc-meishan-zwfw sc-yibin-zwfw sc-guangan-zwfw sc-dazhou-zwfw sc-yaan-zwfw
  sc-bazhong-zwfw sc-ziyang-zwfw sc-aba-zwfw sc-ganzi-zwfw sc-liangshan-zwfw
)

echo "[sc-zwfw] ${#KEYS[@]} 市，CAP=$CAP，串行"
i=0
for k in "${KEYS[@]}"; do
  i=$((i + 1))
  echo "=== [$i/${#KEYS[@]}] $k ==="
  timeout 3600 "$P" "$HARVEST" --site "$k" --limit "$CAP"
  echo "=== $k done rc=$? ==="
  sleep 2
done
echo "[sc-zwfw] 全部完成"
