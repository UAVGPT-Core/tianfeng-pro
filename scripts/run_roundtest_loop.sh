#!/bin/bash
# 轮测循环包装器 - 持续运行直到100回合
cd /Users/a112233/lgox-ops

while true; do
  # 检查当前回合数
  if [ -f /tmp/tx-xs-roundtest-state.json ]; then
    ROUND=$(/opt/homebrew/bin/python3 -c "import json; print(json.load(open('/tmp/tx-xs-roundtest-state.json'))['round'])")
  else
    ROUND=0
  fi
  
  if [ "$ROUND" -ge 100 ]; then
    echo "✅ 已完成100回合! 重置..."
    rm -f /tmp/tx-xs-roundtest-state.json
  fi
  
  /opt/homebrew/bin/python3 scripts/roundtest.py 2>&1
  LAST_LINE=$(tail -1 /tmp/tx-xs-roundtest.log 2>/dev/null)
  echo "[$(date '+%H:%M:%S')] $LAST_LINE"
  sleep 2
done
