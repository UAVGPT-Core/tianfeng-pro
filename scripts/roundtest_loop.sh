#!/bin/bash
# 小枢↔天巡 轮测持续循环 · 100回合后自动重置
PYTHON="/opt/homebrew/bin/python3"
SCRIPT="/Users/a112233/lgox-ops/scripts/roundtest.py"
LOG="/tmp/tx-xs-roundtest-100.log"

echo "[$(date)] Starting continuous roundtest loop..." > "$LOG"

while true; do
  for i in $(seq 1 100); do
    echo "[$(date)] Round $i/100..." >> "$LOG"
    $PYTHON "$SCRIPT" >> "$LOG" 2>&1
    sleep 2
  done
  echo "[$(date)] ===== 100 ROUNDS COMPLETE, AUTO-RESET ======" >> "$LOG"
done
