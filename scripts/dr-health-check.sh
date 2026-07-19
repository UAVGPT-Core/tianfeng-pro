#!/bin/bash
# ============================================================================
# LGOX联邦容灾巡检 (DR Health Check)
# Cron: 每5分钟执行
# 功能: 本机联邦桥(:8765)+知识API(:8769)健康检测 → 自愈 → 冷备切换
# 2026-07-03 1deMac-Studio 创建
# ============================================================================
set -e

# === 配置 ===
STATE_FILE="$HOME/lgox-ops/data/dr-fail-count.json"
LOG_FILE="$HOME/lgox-ops/logs/dr-health-check.log"
LINGLONG_SSH="linglong"
LINGLONG_IP="100.120.20.52"
BRIDGE_HEALTH="http://127.0.0.1:8765/health"
KNOWLEDGE_HEALTH="http://127.0.0.1:8769/health"
MAX_FAILURES=5
RECOVERY_WINDOW=120  # 恢复后需持续2分钟才停止冷备
NOW=$(date '+%Y-%m-%d %H:%M:%S')

# === 工具函数 ===
log() { echo "[$NOW] $*" >> "$LOG_FILE"; }

init_state() {
    if [ ! -f "$STATE_FILE" ]; then
        mkdir -p "$(dirname "$STATE_FILE")"
        cat > "$STATE_FILE" <<'EOF'
{"consecutive_failures": 0, "standby_active": false, "standby_since": "", "last_health": "", "last_action": "init"}
EOF
    fi
}

read_state() {
    python3 -c "
import json,sys
with open('$STATE_FILE') as f:
    d = json.load(f)
for k in ['consecutive_failures','standby_active','standby_since','last_health','last_action']:
    print(f'{k}={d.get(k,\"\")}')
"
}

write_state() {
    local cf=$1
    local sa=$2  # "True" or "False"
    local ss=$3
    local lh=$4
    local la=$5
    python3 <<PYEOF
import json
d = json.load(open('$STATE_FILE'))
d['consecutive_failures'] = $cf
d['standby_active'] = $sa
d['standby_since'] = "$ss"
d['last_health'] = "$lh"
d['last_action'] = "$la"
json.dump(d, open('$STATE_FILE','w'), ensure_ascii=False, indent=2)
PYEOF
}

# === 健康检测 ===
check_health() {
    local bridge_ok=false knowledge_ok=false

    # 检测联邦桥
    local bridge_resp
    bridge_resp=$(curl -s --max-time 5 "$BRIDGE_HEALTH" 2>/dev/null || echo "")
    if echo "$bridge_resp" | grep -qE '"status"\s*:\s*"ok"'; then
        bridge_ok=true
    fi

    # 检测知识API
    local knowledge_resp
    knowledge_resp=$(curl -s --max-time 5 "$KNOWLEDGE_HEALTH" 2>/dev/null || echo "")
    if echo "$knowledge_resp" | grep -qE '"status"\s*:\s*"ok"'; then
        knowledge_ok=true
    fi

    if $bridge_ok && $knowledge_ok; then
        echo "healthy"
    elif $bridge_ok || $knowledge_ok; then
        echo "degraded"
    else
        echo "down"
    fi
}

# === 本地自愈 ===
self_heal() {
    local healed=false

    # 尝试 kickstart 联邦桥
    if ! curl -s --max-time 3 "$BRIDGE_HEALTH" 2>/dev/null | grep -qE '"status"\s*:\s*"ok"'; then
        log "自愈: kickstart ai.logent.fed-search-bridge"
        launchctl kickstart gui/$(id -u)/ai.logent.fed-search-bridge 2>/dev/null || \
        launchctl kickstart system/ai.logent.fed-search-bridge 2>/dev/null || true
        sleep 3
        if curl -s --max-time 3 "$BRIDGE_HEALTH" 2>/dev/null | grep -q '"status":"ok"'; then
            log "自愈: fed-search-bridge 已恢复"
            healed=true
        fi
    fi

    # 尝试 kickstart 知识API
    if ! curl -s --max-time 3 "$KNOWLEDGE_HEALTH" 2>/dev/null | grep -q '"status":"ok"'; then
        log "自愈: kickstart ai.lgox.unified-query"
        launchctl kickstart gui/$(id -u)/ai.lgox.unified-query 2>/dev/null || \
        launchctl kickstart system/ai.lgox.unified-query 2>/dev/null || true
        sleep 3
        if curl -s --max-time 3 "$KNOWLEDGE_HEALTH" 2>/dev/null | grep -q '"status":"ok"'; then
            log "自愈: unified-query 已恢复"
            healed=true
        fi
    fi

    $healed && return 0 || return 1
}

# === 灵龙冷备操作 ===
activate_standby() {
    log "🔴 触发灵龙冷备切换 (连续失败已达$MAX_FAILURES次)"
    if ssh -o ConnectTimeout=10 -o BatchMode=yes "$LINGLONG_SSH" \
        "cd ~/lgox-ops/standby 2>/dev/null && bash standby-watchdog.sh --force 2>&1" 2>/dev/null; then
        log "✅ 灵龙冷备已激活"
        return 0
    else
        log "❌ 灵龙冷备激活失败"
        return 1
    fi
}

deactivate_standby() {
    log "🟢 主节点已恢复${RECOVERY_WINDOW}秒，停止灵龙冷备"
    ssh -o ConnectTimeout=10 -o BatchMode=yes "$LINGLONG_SSH" \
        "cd ~/lgox-ops/standby 2>/dev/null && bash standby-watchdog.sh stop 2>&1" 2>/dev/null || true
}

sync_to_linglong() {
    # 同步关键脚本到灵龙
    local synced=0
    for f in \
        "$HOME/lgox-ops/scripts/fed-search-bridge-v3.py" \
        "$HOME/lgox-ops/scripts/unified-query-api.py" \
        "$HOME/.hermes/scripts/dr-health-check.sh"
    do
        if [ -f "$f" ]; then
            local remote_path
            remote_path=$(echo "$f" | sed "s|$HOME|~|")
            if scp -o ConnectTimeout=10 -o BatchMode=yes "$f" "${LINGLONG_SSH}:${remote_path}" 2>/dev/null; then
                synced=$((synced + 1))
            fi
        fi
    done
    [ $synced -gt 0 ] && log "同步灵龙: ${synced}个文件"
}

# === 主流程 ===
init_state
eval $(read_state)  # 加载 consecutive_failures, standby_active, standby_since, last_health, last_action

HEALTH=$(check_health)

case "$HEALTH" in
    healthy)
        # 健康状态: 重置失败计数
        if [ "$consecutive_failures" != "0" ]; then
            log "🟢 服务恢复健康 (之前失败${consecutive_failures}次)"
        fi

        # 如果冷备处于激活状态，检查已恢复时长
        if [ "$standby_active" = "True" ]; then
            if [ -n "$standby_since" ]; then
                STANDBY_EPOCH=$(date -j -f "%Y-%m-%d %H:%M:%S" "$standby_since" +%s 2>/dev/null || echo 0)
                NOW_EPOCH=$(date +%s)
                ELAPSED=$((NOW_EPOCH - STANDBY_EPOCH))
                if [ "$last_health" = "healthy" ]; then
                    # 连续两次healthy→确认恢复
                    if [ "$ELAPSED" -gt "$RECOVERY_WINDOW" ]; then
                        deactivate_standby
                        write_state 0 False "" "$HEALTH" "deactivate_standby"
                        log "✅ 主节点稳定恢复，冷备已停止"
                    else
                        write_state 0 "$standby_active" "$standby_since" "$HEALTH" "recovering"
                        log "🟡 主节点恢复中(${ELAPSED}s/$RECOVERY_WINDOWs)，冷备保持"
                    fi
                else
                    # 首次恢复
                    write_state 0 "$standby_active" "$standby_since" "$HEALTH" "first_recovery"
                    log "🟡 主节点首次恢复，等待${RECOVERY_WINDOW}s后停止冷备"
                fi
            else
                write_state 0 "$standby_active" "$(date '+%Y-%m-%d %H:%M:%S')" "$HEALTH" "recovery_start"
            fi
        else
            # 正常: 同步配置到灵龙
            sync_to_linglong
            write_state 0 False "" "$HEALTH" "healthy_sync"
        fi
        ;;

    degraded)
        # 部分故障: 计数+1，尝试自愈
        new_fail=$((consecutive_failures + 1))
        log "🟡 部分故障 (${new_fail}/${MAX_FAILURES})"
        self_heal || true
        write_state "$new_fail" "$standby_active" "$standby_since" "$HEALTH" "self_heal_attempt"
        ;;

    down)
        # 全部故障
        new_fail=$((consecutive_failures + 1))
        log "🔴 全部故障 (${new_fail}/${MAX_FAILURES})"

        if [ "$new_fail" -ge "$MAX_FAILURES" ] && [ "$standby_active" != "True" ]; then
            # 触发冷备
            if activate_standby; then
                write_state "$new_fail" True "$(date '+%Y-%m-%d %H:%M:%S')" "$HEALTH" "activate_standby"
            else
                write_state "$new_fail" False "" "$HEALTH" "standby_failed"
                log "🚨 冷备激活失败，需人工介入"
            fi
        else
            # 自愈尝试
            if [ "$new_fail" -ge 2 ]; then
                self_heal || true
            fi
            write_state "$new_fail" "$standby_active" "$standby_since" "$HEALTH" "fail_count_$new_fail"
        fi
        ;;
esac

# === 输出异常报告 ===
eval $(read_state)  # 重新读取最新状态

if [ "$consecutive_failures" -gt 0 ] || [ "$standby_active" = "True" ]; then
    echo "========== LGOX联邦容灾巡检 [$NOW] =========="
    echo "健康状态: $HEALTH"
    echo "连续失败: ${consecutive_failures}/${MAX_FAILURES}"
    echo "冷备状态: $([ "$standby_active" = "True" ] && echo "🔴 已激活 ($standby_since)" || echo "🟢 未激活")"
    echo "上次动作: $last_action"
    echo "=============================================="
else
    # 健康状态，不输出（静默）
    :
fi
