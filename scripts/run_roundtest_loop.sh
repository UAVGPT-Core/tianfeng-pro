#!/bin/bash
# 轮测引擎循环启动脚本 — 自动重启直到100回合

count=0
while [ $count -lt 7 ]; do
    echo "=== Run batch $((count+1)) ==="
    /opt/homebrew/bin/python3 /Users/a112233/lgox-ops/scripts/roundtest.py 2>&1
    echo ""
    count=$((count+1))
done
echo "=== 循环完成(7批≈100回合) ==="
