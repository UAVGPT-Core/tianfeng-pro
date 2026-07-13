#!/usr/bin/env python3

"""LGOX联邦 • 灵龙心跳 — 由fed-skill-deploy v1.0.0自动部署"""
import json, urllib.request, os, sys
from datetime import datetime, timezone, timedelta

NODE = "灵龙"
BRIDGE = os.environ.get("FED_BRIDGE", "http://localhost:8765")
TZ = timezone(timedelta(hours=8))
LOG = os.path.expanduser("~/lgox-ops/logs/node-heartbeat.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)

# 导入信任分模块
sys.path.insert(0, os.path.expanduser("~/bin"))
try:
    from trust_score import get_trust_score
except ImportError:
    get_trust_score = lambda n="灵龙": 0.0

def heartbeat(bridge_url=None):
    """发送心跳到指定桥。多路冗余——本地桥+天枢桥。"""
    url = bridge_url or BRIDGE
    results = []
    try:
        ts_now = datetime.now(TZ).isoformat()
        # v2.3桥用"name", v4.0桥用"node" — 两个都发兼容
        data_v23 = json.dumps({"name": NODE, "ts": ts_now, "status": "alive",
                               "ip": "100.85.201.47", "hostname": "Mac-mini.local",
                               "os": "macOS 15.4"}).encode()
        data_v4 = json.dumps({"node": NODE, "name": NODE, "ts": ts_now, "status": "alive",
                              "node_id": "linglong", "role": "member"}).encode()
        
        for label, data in [("v2.3", data_v23), ("v4.0", data_v4)]:
            try:
                req = urllib.request.Request(f"{url}/heartbeat",
                    data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    results.append(f"{label}:{r.status}")
            except Exception as e:
                results.append(f"{label}:{type(e).__name__}")
        
        ok = any("200" in r for r in results)
        if not ok:
            raise Exception("|".join(results))
        return ok
    except Exception as e:
        ts = datetime.now(TZ).strftime("%m-%d %H:%M:%S")
        with open(LOG, "a") as f:
            f.write(f"[{ts}] ❤️ 心跳失败({url}): {e}\n")
        return False

# 多桥心跳地址
HEARTBEAT_BRIDGES = [
    "http://localhost:8765",         # 本地桥v2.3
    "http://100.100.89.2:8765",     # 天枢桥v4.0
]

if __name__ == "__main__":
    ok_count = 0
    for bridge_url in HEARTBEAT_BRIDGES:
        if heartbeat(bridge_url):
            ok_count += 1
    
    ts = datetime.now(TZ).strftime("%m-%d %H:%M:%S")
    with open(LOG, "a") as f:
        f.write(f"[{ts}] ❤️ 心跳完成: {ok_count}/{len(HEARTBEAT_BRIDGES)}路通\n")
    
    if ok_count == 0:
        sys.exit(1)
