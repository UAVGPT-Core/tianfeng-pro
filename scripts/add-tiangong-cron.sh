#!/bin/bash
# Add gpu-gene-enrich cron on 天工 DGX1
cd ~/lgox-ops
mkdir -p logs
# Check if cron already exists
if crontab -l 2>/dev/null | grep -q gpu-gene-enrich; then
    echo "cron already exists"
else
    (crontab -l 2>/dev/null; echo "0 * * * * cd ~/lgox-ops && mkdir -p logs && python3 scripts/gpu-gene-enrich.py >> logs/gpu-enrich.log 2>&1") | crontab -
    echo "cron added"
    crontab -l | grep gpu-gene
fi
