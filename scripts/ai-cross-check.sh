#!/bin/bash
# ai-cross-check.sh — AI服务交叉验证
# 检查灵龙各AI端点是否正常响应，对比响应质量
# 创建: 2026-07-20 灵龙 cron fix

LOG_DIR="$HOME/lgox-ops/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/ai-cross-check.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] AI cross-check starting..." | tee -a "$LOG"

# Check local LLM endpoints
ENDPOINTS=(
    "http://localhost:18666/v1/chat/completions|DeepSeek-Flash"
    "http://localhost:11434/api/tags|Ollama"
    "http://100.116.0.29:8200/health|LGE"
    "http://100.100.89.2:8765/health|Fed-Bridge"
)

FAILURES=0
for entry in "${ENDPOINTS[@]}"; do
    IFS='|' read -r url name <<< "$entry"
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null | grep -q '^2'; then
        echo "  ✅ $name OK" | tee -a "$LOG"
    else
        echo "  ❌ $name FAILED ($url)" | tee -a "$LOG"
        FAILURES=$((FAILURES + 1))
    fi
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cross-check done. Failures: $FAILURES" | tee -a "$LOG"

# Keep log trim
tail -500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
