#!/bin/bash
# roundtest 永动包装器 — 持续运行，永不停止
LOGFILE="/Users/a112233/lgox-ops/logs/roundtest-loop.log"
PIDFILE="/tmp/roundtest-loop.pid"

echo $$ > "$PIDFILE"

while true; do
    echo "[$(date '+%m-%d %H:%M:%S')] ====== 启动新轮次 ======" >> "$LOGFILE"
    /opt/homebrew/bin/python3 -u /Users/a112233/lgox-ops/scripts/roundtest.py >> "$LOGFILE" 2>&1
    EXIT_CODE=$?
    echo "[$(date '+%m-%d %H:%M:%S')] ⚠️ roundtest.py 退出(code=$EXIT_CODE), 3秒后重启..." >> "$LOGFILE"
    sleep 3
done
