#!/bin/bash
# 小枢与天巡轮测循环引擎 - 持续运行直到100回合后自动重置
LOGFILE="/Users/a112233/lgox-ops/scripts/roundtest-loop.log"
cd /Users/a112233/lgox-ops/scripts
while true; do
  /opt/homebrew/bin/python3 roundtest.py >> "$LOGFILE" 2>&1
  sleep 3
done
