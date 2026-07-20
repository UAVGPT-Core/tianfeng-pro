#!/bin/bash
# Wrapper to run roundtest continuously through all 100 rounds
set -e
PY="/opt/homebrew/bin/python3"
SCRIPT="/Users/a112233/lgox-ops/scripts/roundtest.py"
MAX_CYCLES=1  # Run until we complete one full cycle

for cycle in $(seq 1 $MAX_CYCLES); do
  echo "=== Cycle $cycle ==="
  
  for i in $(seq 1 100); do
    $PY "$SCRIPT" 2>&1
    
    # Read state after each round
    state=$(cat /tmp/tx-xs-roundtest-state.json 2>/dev/null || echo '{"round":0}')
    r=$(echo "$state" | $PY -c "import sys,json; print(json.load(sys.stdin).get('round',0))" 2>/dev/null)
    
    # If we wrapped around (round=100 was just completed, now round=1)
    if [ "$r" -le 1 ] && [ "$i" -gt 2 ]; then
      echo "=== Cycle COMPLETE! Round reset detected ==="
      break
    fi
    
    # Brief pause between rounds
    sleep 1
  done
done

echo ""
echo "=== FINAL STATE ==="
cat /tmp/tx-xs-roundtest-state.json 2>/dev/null || echo "No state file"
echo ""
echo "=== LAST 5 LOG LINES ==="
tail -5 /tmp/tx-xs-roundtest.log 2>/dev/null || echo "No log file"
