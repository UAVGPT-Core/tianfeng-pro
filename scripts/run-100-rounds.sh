#!/bin/bash
# 小枢↔天巡 100回合轮测 · 持续运行 · 异常自动恢复
LOGFILE="/tmp/tx-xs-roundtest.log"
STATE="/tmp/tx-xs-roundtest-state.json"
PYTHON="/opt/homebrew/bin/python3"
SCRIPT="/Users/a112233/lgox-ops/scripts/roundtest.py"

# 重置状态(从round 1开始)
echo '{"round": 0, "tx_wins": 0, "xs_wins": 0, "heals": 0, "errors": 0}' > "$STATE"

for round in $(seq 1 100); do
  echo "[$(date '+%m-%d %H:%M:%S')] ⏳ Starting round $round/100..."
  $PYTHON "$SCRIPT"
  RC=$?
  
  # 检查是否卡死(超过120秒没进展)
  PREV=$(cat "$STATE" 2>/dev/null | $PYTHON -c "import sys,json; print(json.load(sys.stdin).get('round',0))" 2>/dev/null || echo "0")
  if [ "$PREV" = "0" ] || [ "$PREV" = "" ]; then PREV=0; fi
  if [ "$PREV" -lt "$round" ]; then
    echo "[$(date '+%m-%d %H:%M:%S')] ✅ Round $round completed (state: $PREV)"
  else
    echo "[$(date '+%m-%d %H:%M:%S')] ⚠️ Round $round did not advance state ($PREV), retrying..."
    sleep 5
    $PYTHON "$SCRIPT"
  fi
  
  # 检查是否达到100
  CUR=$(cat "$STATE" 2>/dev/null | $PYTHON -c "import sys,json; print(json.load(sys.stdin).get('round',0))" 2>/dev/null || echo "0")
  if [ "$CUR" -ge 100 ]; then
    echo "[$(date '+%m-%d %H:%M:%S')] 🎉 100 rounds completed! Resetting for next cycle..."
    echo '{"round": 0, "tx_wins": 0, "xs_wins": 0, "heals": 0, "errors": 0}' > "$STATE"
    break
  fi
  
  sleep 5
done

echo "[$(date '+%m-%d %H:%M:%S')] ===== 100 ROUNDS COMPLETE ====="
tail -5 "$LOGFILE"
