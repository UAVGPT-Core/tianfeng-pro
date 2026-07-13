#!/usr/bin/env python3
"""秒改秒见·dashboard注入: 灵龙bridge直接served dashboard-v6.2"""
import http.client, json, os, time

DASHBOARD_PATH = "/Users/a112233/lgox-ops/web/dashboard-v6.2.json"

# 1. 先跑一轮FCPF同步最新dashboard
os.system(f"cd /Users/a112233/lgox-ops/scripts && python3 fed-comm-flywheel.py 2>/dev/null")

# 2. 读合并后的dashboard
with open(DASHBOARD_PATH) as f:
    dash = json.load(f)

# 3. 直接POST到天枢小枢的dashboard-refresh端点(GET)
try:
    # 小枢有/sync/dashboard 和 /dashboard/refresh
    conn = http.client.HTTPConnection("100.100.89.2", 8001, timeout=5)
    conn.request("GET", "/dashboard/refresh")
    resp = conn.getresponse()
    print(f"小枢refresh: {resp.status}")
    conn.close()
except Exception as e:
    print(f"小枢refresh: {e}")

# 4. 通过bridge发送完整dashboard给天枢
payload = json.dumps({
    "from": "灵龙",
    "to": "天枢",
    "content": f"🔄 秒改秒见·dashboard-v6.2自动推送\n"
               f"飞轮: {len(dash.get('flywheels',{}))}个\n"
               f"版本: v6.2\n"
               f"通讯飞轮: {dash.get('flywheels',{}).get('通讯','?')}\n"
               f"flywheel_comm数据见下方JSON\n\n"
               f"DASHBOARD_MERGE:{json.dumps(dash.get('flywheel_comm',{}), ensure_ascii=False)}\n"
               f"VERSION:v6.2"
}, ensure_ascii=False)

try:
    conn = http.client.HTTPConnection("100.100.89.2", 8765, timeout=5)
    conn.request("POST", "/messages/send", payload.encode(), 
                 {"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = json.loads(resp.read())
    print(f"桥推送: {data.get('status','?')} id={data.get('message_id','?')}")
    conn.close()
except Exception as e:
    print(f"桥推送: {e}")

# 5. 验证当前版本
try:
    conn = http.client.HTTPConnection("stock.uavgpt.com", 80, timeout=5)
    conn.request("GET", "/dashboard.json")
    resp = conn.getresponse()
    d = json.loads(resp.read())
    print(f"当前在线版本: {d.get('version','?')}")
    print(f"飞轮数: {len(d.get('flywheels',{}))}")
    print(f"通讯飞轮: {d.get('flywheels',{}).get('通讯','?') or '🔴缺失'}")
    conn.close()
except Exception as e:
    print(f"在线检查: {e}")

print(f"\n本地v6.2: {DASHBOARD_PATH}")
