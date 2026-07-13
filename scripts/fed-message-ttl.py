#!/usr/bin/env python3
"""
联邦消息TTL清理器 v1.0
每小时清理过期消息，轻量化铁律执行工具
"""
import json, time, os, sys
from pathlib import Path
from urllib.request import Request, urlopen

BRIDGE = "http://100.100.89.2:8765"
TTL_MAP = {
    "constitution": 604800,  # 7天
    "broadcast": 604800,     # 7天
    "task": 86400,           # 24h
    "knowledge": 259200,     # 72h
    "heartbeat": 3600,       # 1h
    "health": 3600,          # 1h
}

def clean():
    now = time.time()
    cleaned = 0
    
    try:
        # 请求联邦桥清理过期消息
        data = json.dumps({
            "action": "clean_expired",
            "ttl_map": TTL_MAP,
            "timestamp": now
        }).encode()
        
        req = Request(f"{BRIDGE}/messages/clean", data=data,
                      headers={"Content-Type": "application/json"},
                      method="POST")
        with urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            cleaned = resp.get("cleaned", 0)
    except Exception as e:
        print(f"TTL clean error: {e}", file=sys.stderr)
        return 1
    
    if cleaned > 0:
        print(f"[TTL] 清理 {cleaned} 条过期消息")
    return 0

if __name__ == "__main__":
    sys.exit(clean())
