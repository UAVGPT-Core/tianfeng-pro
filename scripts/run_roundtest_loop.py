#!/usr/bin/env python3
"""Run roundtest continuously until 100 rounds, then auto-reset."""
import json, os, subprocess, time, sys

STATE_FILE = "/tmp/tx-xs-roundtest-state.json"
SCRIPT = "/Users/a112233/lgox-ops/scripts/roundtest.py"
LOG_FILE = "/tmp/tx-xs-roundtest.log"
MAX = 100

def run_once():
    """Run one roundtest round, return round number."""
    result = subprocess.run(
        ["/opt/homebrew/bin/python3", SCRIPT],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        print(f"ERR: {result.stderr[:200]}")
    for line in result.stdout.split("\n"):
        if any(k in line for k in ["══════", "累计", "自愈", "错误", "基因", "胜", "健康", "漂移"]):
            print(f"  {line}")
    # Read state
    try:
        with open(STATE_FILE) as f:
            st = json.load(f)
        return st.get("round", 0), st
    except:
        return 0, {}

# Main loop
cycle = 0
while True:
    cycle += 1
    try:
        with open(STATE_FILE) as f:
            st = json.load(f)
    except:
        st = {"round": 0}
    
    current = st.get("round", 0)
    
    if current >= MAX:
        print(f"\n{'='*50}")
        print(f"✅ 已完成{MAX}回合! 自动重置...")
        print(f"{'='*50}")
        # Let roundtest.py handle the reset
        r, st = run_once()
        print(f"重置后状态: 回合{r}")
        # Continue to next cycle
    
    r, st = run_once()
    print(f"[cycle {cycle}] 回合 {r}/{MAX} | 天巡{st.get('tx_wins',0)}胜 小枢{st.get('xs_wins',0)}胜 | 自愈{st.get('heals',0)}次")
    
    # Print last 5 log lines every 10 rounds
    if r % 10 == 0:
        print(f"\n--- 最后5行日志 (回合{r}) ---")
        if os.path.exists(LOG_FILE):
            result = subprocess.run(["tail", "-5", LOG_FILE], capture_output=True, text=True)
            for line in result.stdout.strip().split("\n"):
                print(f"  {line}")
        print("---")
    
    time.sleep(1)
