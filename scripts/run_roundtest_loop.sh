#!/bin/bash
# Loop roundtest until 100 rounds
for i in $(seq 1 200); do
  /opt/homebrew/bin/python3 /Users/a112233/lgox-ops/scripts/roundtest.py
  r=$(python3 -c "import json; d=json.load(open('/tmp/tx-xs-roundtest-state.json')); print(d.get('round',0))" 2>/dev/null)
  [ -z "$r" ] && r=0
  if [ "$r" -ge 100 ] || [ "$r" -eq 0 ] 2>/dev/null; then
    echo "=== DONE: round=$r ==="
    tail -5 /tmp/tx-xs-roundtest.log
    break
  fi
  sleep 2
done
