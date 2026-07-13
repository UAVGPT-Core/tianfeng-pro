#!/bin/bash
# 小枢↔天巡 100回合轮测 · 后台持续运行
PYTHON="/opt/homebrew/bin/python3"
SCRIPT="/Users/a112233/lgox-ops/scripts/roundtest.py"
STATE="/tmp/tx-xs-roundtest-state.json"
LOG="/tmp/tx-xs-roundtest-100.log"

echo "[$(date)] Starting 100-round cycle..." > "$LOG"
rm -f "$STATE"

for i in $(seq 1 100); do
  echo "[$(date)] Round $i/100..." >> "$LOG"
  $PYTHON "$SCRIPT" >> "$LOG" 2>&1
  RC=$?
  sleep 3
done

echo "[$(date)] ===== 100 ROUNDS COMPLETE =====" >> "$LOG"
echo "Last 5 lines:" >> "$LOG"
tail -5 "$LOG" >> "$LOG"
