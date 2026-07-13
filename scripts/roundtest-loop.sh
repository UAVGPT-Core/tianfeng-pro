#!/bin/bash
# 小枢↔天巡轮测引擎 — 持续循环执行
LOGFILE="/tmp/tx-xs-roundtest-loop.log"
cd /Users/a112233/lgox-ops
while true; do
  /opt/homebrew/bin/python3 scripts/roundtest.py >> "$LOGFILE" 2>&1
  RC=$?
  echo "[$(date '+%m-%d %H:%M:%S')] roundtest exit code=$RC, restarting..." >> "$LOGFILE"
  sleep 30
done
