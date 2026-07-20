#!/bin/bash
# heal-gray-nodes.sh — 灰度节点自愈巡检
# 调用 healer_v2.py 扫描并修复已知故障模式
# 创建: 2026-07-20 灵龙 cron fix

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$HOME/lgox-ops/logs"
mkdir -p "$LOG_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] heal-gray-nodes starting..."

# Run healer v2
if [ -f "$SCRIPT_DIR/healer_v2.py" ]; then
    python3 "$SCRIPT_DIR/healer_v2.py" --scan 2>&1
else
    echo "WARN: healer_v2.py not found at $SCRIPT_DIR/healer_v2.py"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] heal-gray-nodes done."
