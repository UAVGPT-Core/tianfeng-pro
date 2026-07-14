#!/bin/bash
# 批量轮测脚本 - 持续运行roundtest.py
SCRIPT="/Users/a112233/lgox-ops/scripts/roundtest.py"
PYTHON="/opt/homebrew/bin/python3"
MAX=${1:-60}  # 默认60回合

for ((i=1; i<=MAX; i++)); do
    $PYTHON $SCRIPT 2>&1
    if [ $? -ne 0 ]; then
        echo "[$(date +%H:%M:%S)] ❌ 第$i轮异常退出"
        break
    fi
    sleep 2
done
echo "[$(date +%H:%M:%S)] ✅ 批量$MAX回合完成"
