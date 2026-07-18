#!/bin/bash
cd /Users/a112233/lgox-ops/scripts
for i in $(seq 1 40); do
  /opt/homebrew/bin/python3 roundtest.py 2>&1 | tail -5
done
