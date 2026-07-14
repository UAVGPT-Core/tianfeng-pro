#!/bin/bash
# 轮测引擎持续循环包装器
cd /Users/a112233/lgox-ops/scripts
while true; do
    /opt/homebrew/bin/python3 roundtest.py 2>&1
    sleep 30
done
