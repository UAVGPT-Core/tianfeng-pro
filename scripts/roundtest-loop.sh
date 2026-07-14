#!/bin/bash
# 轮测持续包装器 — 循环执行roundtest.py直到100回合后自动重置
STATE_FILE="/tmp/tx-xs-roundtest-state.json"

echo "[循环启动] 开始持续轮测..."
while true; do
    /opt/homebrew/bin/python3 /Users/a112233/lgox-ops/scripts/roundtest.py 2>&1
    
    # 检查状态
    if [ -f "$STATE_FILE" ]; then
        ROUND=$(python3 -c "import json; print(json.load(open('$STATE_FILE'))['round'])")
        echo "[循环] 当前回合: $ROUND/100"
        if [ "$ROUND" -ge 100 ]; then
            echo "[重置] 100回合完成，重置计数器..."
            rm -f "$STATE_FILE"
        fi
    fi
    
    # 每轮间隔 5 秒再跑下一轮，避免API被打满
    sleep 5
done
