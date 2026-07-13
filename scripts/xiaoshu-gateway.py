#!/usr/bin/env python3
"""
小枢 · 联邦门面网关 (第9节点) — v1.0
运行于天枢 StockAgent:8001 (role=xiaoshu)
职能: 联邦公开展示·量化灯塔·低空经济门户·引流阵地

用法:
  python3 xiaoshu-gateway.py --refresh    # 刷新公开展示内容
  python3 xiaoshu-gateway.py --check       # 验证仪表盘+金字塔可达
  python3 xiaoshu-gateway.py --visitors    # 收集访问统计
  python3 xiaoshu-gateway.py --health      # 健康自检
"""

import json, sys, os, time
import urllib.request, urllib.error

BASE = "http://localhost:8001"
WIND_BASE = "http://localhost:18770"  # 天枢Wind金融引擎·SSH隧道
FACTS_URL = f"{BASE}/api/facts"
HEALTH_URL = f"{BASE}/health"
PYRAMID_URL = f"{BASE}/api/pyramid-status"
VISITOR_URL = f"{BASE}/api/visitor/stats"
FACTS_FILE = "/Users/a1/stockagent-backend/facts.json"

# 公网URL(用于验证)
PUBLIC_BASE = "https://stock.uavgpt.com"
PUBLIC_HEALTH = f"{PUBLIC_BASE}/health"
PUBLIC_PYRAMID = f"{PUBLIC_BASE}/pyramid"
PUBLIC_CONSTITUTION = f"{PUBLIC_BASE}/constitution"

def http_get(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LGOX-Xiaoshu/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode(), r.status
    except Exception as e:
        return str(e), 0

def cmd_refresh():
    """刷新公开展示: 检查facts.json + 推送新鲜数据"""
    results = {}
    
    # 1. 检查本地facts.json
    if os.path.exists(FACTS_FILE):
        try:
            with open(FACTS_FILE) as f:
                facts = json.load(f)
            results["facts_file"] = f"OK ({len(str(facts))} chars)"
        except Exception as e:
            results["facts_file"] = f"PARSE_ERR: {e}"
    else:
        results["facts_file"] = "MISSING"
    
    # 2. API facts端点
    data, code = http_get(FACTS_URL)
    results["facts_api"] = f"HTTP {code}" if code else f"ERR: {data[:80]}"
    
    # 3. 检查金字塔状态
    data, code = http_get(PYRAMID_URL)
    if code == 200:
        try:
            ps = json.loads(data)
            levels = ps.get("levels", {}) if isinstance(ps, dict) else {}
            active = sum(1 for v in levels.values() if isinstance(v, dict) and v.get("status") == "active")
            results["pyramid"] = f"OK ({len(levels)}层, {active}活跃)"
        except:
            results["pyramid"] = f"HTTP 200 (非JSON)"
    else:
        results["pyramid"] = f"HTTP {code}"
    
    # 4. 公网可达性
    _, code = http_get(PUBLIC_HEALTH)
    results["public_reachable"] = f"HTTP {code}" if code else "UNREACHABLE"
    
    # 输出
    print(json.dumps({"node": "小枢", "action": "refresh", "results": results, 
                      "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")},
                     ensure_ascii=False, indent=2))
    
    # 推送联邦桥
    _push_to_bridge("小枢", "facts_refreshed", results)
    return 0

def cmd_check():
    """验证仪表盘+金字塔公网可达"""
    checks = {}
    
    endpoints = {
        "health": PUBLIC_HEALTH,
        "pyramid": PUBLIC_PYRAMID,
        "constitution": PUBLIC_CONSTITUTION,
    }
    
    for name, url in endpoints.items():
        _, code = http_get(url, timeout=10)
        checks[name] = "OK" if code == 200 else f"HTTP {code or 'ERR'}"
    
    all_ok = all(v == "OK" for v in checks.values())
    print(json.dumps({
        "node": "小枢", "action": "check", "checks": checks,
        "status": "🟢" if all_ok else "🔴",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }, ensure_ascii=False, indent=2))
    
    if not all_ok:
        _push_to_bridge("小枢", "display_alert", checks)
    
    return 0 if all_ok else 1

def cmd_visitors():
    """收集访问统计"""
    data, code = http_get(VISITOR_URL)
    if code == 200:
        try:
            print(json.dumps({"node": "小枢", "action": "visitors", "data": json.loads(data),
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")},
                           ensure_ascii=False, indent=2))
        except:
            print(json.dumps({"node": "小枢", "action": "visitors", "raw": data[:200],
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")},
                           ensure_ascii=False))
    else:
        print(json.dumps({"node": "小枢", "action": "visitors", "error": f"HTTP {code}",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")},
                       ensure_ascii=False))

def cmd_health():
    """自检"""
    data, code = http_get(HEALTH_URL)
    status = "OK" if code == 200 else f"DOWN (HTTP {code})"
    print(json.dumps({
        "node": "小枢", "role": "联邦门面·第9节点·AI灯塔",
        "backing": "天枢 StockAgent:8001 (role=xiaoshu)",
        "status": status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }, ensure_ascii=False, indent=2))
    return 0 if code == 200 else 1

def _push_to_bridge(node, event_type, data):
    """推送事件到联邦桥"""
    try:
        payload = json.dumps({
            "type": event_type,
            "node": node,
            "data": data,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }).encode()
        req = urllib.request.Request("http://100.100.89.2:8765/push",
                                     data=payload,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except:
        pass  # 联邦桥不可达不影响主功能

if __name__ == "__main__":
    if "--refresh" in sys.argv:
        sys.exit(cmd_refresh())
    elif "--check" in sys.argv:
        sys.exit(cmd_check())
    elif "--visitors" in sys.argv:
        cmd_visitors()
    elif "--health" in sys.argv:
        sys.exit(cmd_health())
    else:
        print("用法: xiaoshu-gateway.py --refresh|--check|--visitors|--health")
        sys.exit(1)
