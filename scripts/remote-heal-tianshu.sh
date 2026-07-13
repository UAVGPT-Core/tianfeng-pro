#!/bin/bash
# ============================================================
# remote-heal-tianshu.sh — 天枢远程巡检 + 灵龙联检
# 使用: bash scripts/remote-heal-tianshu.sh
# 部署: 放 ~/.hermes/scripts/ 下，cron 每 30min 触发
# 创建: 2026-07-13 cron 实战，从兜底巡检模式提取
# ============================================================
set -euo pipefail

TIANSHU="100.100.89.2"
LOCAL="127.0.0.1"
LOG="/tmp/tianshu-remote-heal.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "=== 天枢远程巡检 $TIMESTAMP ===" | tee "$LOG"

# ---- 1. SSH 连通性 ----
echo -n "[1/5] SSH连通: " | tee -a "$LOG"
if ssh -o ConnectTimeout=8 -o BatchMode=yes a1@$TIANSHU 'echo OK' 2>/dev/null; then
    echo "✅" | tee -a "$LOG"
    SSH_OK=true
else
    echo "❌ SSH不通" | tee -a "$LOG"
    SSH_OK=false
fi

# ---- 2. 核心端口矩阵 (本地Python探针，避免cron curl裸IP拦截) ----
echo -n "[2/5] 端口矩阵: " | tee -a "$LOG"
python3 << 'PYEOF' | tee -a "$LOG"
import urllib.request, json

ports = {
    "天枢:8001(StockAgent)": "http://100.100.89.2:8001/health",
    "天枢:8760(Gateway)": "http://100.100.89.2:8760/health",
    "天枢:8765(联邦桥)": "http://100.100.89.2:8765/health",
    "天枢:8778(融合网关)": "http://100.100.89.2:8778/health",
    "天枢:8779(小枢)": "http://100.100.89.2:8779/health",
    "灵龙:8780(超级智能体)": "http://127.0.0.1:8780/health",
    "灵龙:8210(LGE镜像)": "http://127.0.0.1:8210/health",
    "灵龙:8788(Memory)": "http://127.0.0.1:8788/health",
    "地枢:8200(LGE)": "http://100.116.0.29:8200/health",
    "公网:stock首页": "https://stock.uavgpt.com/",
}

ok = 0
total = len(ports)
for label, url in ports.items():
    try:
        urllib.request.urlopen(url, timeout=8)
        ok += 1
    except:
        print(f"  ❌ {label}")
        continue

print(f"  {ok}/{total} 通")
PYEOF

# ---- 3. DGX2 状态 ----
echo -n "[3/5] DGX2: " | tee -a "$LOG"
DGX2_STATUS=$(tailscale status 2>/dev/null | grep spark-5438 | awk '{print $5, $6, $7}' || echo "unknown")
echo "$DGX2_STATUS" | tee -a "$LOG"
if echo "$DGX2_STATUS" | grep -q "offline"; then
    echo "  ⚠️ DGX2离线，8780将级联挂死" | tee -a "$LOG"
fi

# ---- 4. 天枢 launchd 异常过滤 ----
if $SSH_OK; then
    echo "[4/5] 天枢launchd异常: " | tee -a "$LOG"
    ssh a1@$TIANSHU 'launchctl list 2>/dev/null | awk '"'"'$2 != "0" && $2 != "" {print $0}'"'"'' 2>/dev/null | tee -a "$LOG" || echo "  SSH查询失败" | tee -a "$LOG"
else
    echo "[4/5] 天枢launchd: ⏭️ SSH不通，跳过" | tee -a "$LOG"
fi

# ---- 5. 灵龙 8780 自愈 ----
echo -n "[5/5] 8780自愈: " | tee -a "$LOG"
if python3 -c "
import urllib.request
try:
    urllib.request.urlopen('http://127.0.0.1:8780/health', timeout=5)
    print('OK')
except:
    print('DEAD')
" 2>/dev/null | grep -q OK; then
    echo "✅ 正常" | tee -a "$LOG"
else
    echo "🔴 尝试恢复..." | tee -a "$LOG"
    MYUID=$(id -u)
    launchctl bootout gui/$MYUID/com.lgox.super-agent 2>/dev/null || true
    sleep 2
    # kill残留PID
    for pid in $(lsof -ti:8780 2>/dev/null); do
        kill -9 $pid 2>/dev/null || true
    done
    sleep 2
    launchctl bootstrap gui/$MYUID ~/Library/LaunchAgents/com.lgox.super-agent.plist 2>/dev/null || true
    sleep 5
    if python3 -c "
import urllib.request
try:
    urllib.request.urlopen('http://127.0.0.1:8780/health', timeout=10)
    print('OK')
except:
    print('STILL_DEAD')
" 2>/dev/null | grep -q OK; then
        echo "✅ 已恢复" | tee -a "$LOG"
    else
        # 检查是否DGX2离线级联
        if tailscale status 2>/dev/null | grep spark-5438 | grep -q offline; then
            echo "⛔ DGX2离线级联挂死·无法自愈·等DGX2恢复" | tee -a "$LOG"
        else
            echo "❌ 恢复失败" | tee -a "$LOG"
        fi
    fi
fi

echo "=== 巡检完成 $TIMESTAMP ===" | tee -a "$LOG"
