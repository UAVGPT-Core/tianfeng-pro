#!/usr/bin/env python3
"""
天巡 · 联邦外部哨兵 (第10节点) — v1.0
运行于天枢 StockAgent:8001 (role=tianxun)
职能: 从公网视角巡检联邦·宪法守卫·企业AI门面·外部健康签证

独特价值: 天巡是联邦中唯一能从「公网视角」检查节点可达性的节点。
          內网节点互相看得见，只有天巡能发现公网断裂。

用法:
  python3 tianxun-sentinel.py --probe-all           # 从公网巡检全节点
  python3 tianxun-sentinel.py --check-constitution   # 宪法公网校验
  python3 tianxun-sentinel.py --visitors             # 门面接待统计
  python3 tianxun-sentinel.py --certify              # 签发健康签证
  python3 tianxun-sentinel.py --health               # 自检
"""

import json, sys, os, time
import urllib.request, urllib.error

BASE = "http://localhost:8001"
HEALTH_URL = f"{BASE}/health"
VISITOR_URL = f"{BASE}/api/visitor/stats"
REGISTER_URL = f"{BASE}/api/chat/tianxun/register"
FACTS_URL = f"{BASE}/api/facts"

# 公网检查端点
PUBLIC_BASE = "https://stock.uavgpt.com"
PUBLIC_TARGETS = {
    "stock门户": f"{PUBLIC_BASE}/health",
    "宪法页面": f"{PUBLIC_BASE}/constitution",
    "金字塔": f"{PUBLIC_BASE}/pyramid",
    "uavgpt低空": "https://uavgpt.com/",
}

# 联邦桥
BRIDGE = "http://100.100.89.2:8765"

def http_get(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LGOX-Tianxun/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode(errors='replace')
            return body, r.status
    except Exception as e:
        return str(e), 0

def cmd_probe_all():
    """从公网视角巡检 - 天巡的独门武功"""
    results = {}
    
    for name, url in PUBLIC_TARGETS.items():
        body, code = http_get(url, timeout=12)
        if code == 200:
            # 深度检查: 宪法页面必须含关键字
            if name == "宪法页面":
                if "LGOX联邦宪法" in body or "LGOX" in body[:2000]:
                    results[name] = "🟢 OK (内容验证通过)"
                else:
                    results[name] = "🟡 HTTP 200 但内容异常"
            elif name == "金字塔":
                if "九层" in body or "pyramid" in body.lower():
                    results[name] = "🟢 OK"
                else:
                    results[name] = "🟡 HTTP 200 但内容异常"
            else:
                results[name] = "🟢 OK"
        else:
            results[name] = f"🔴 HTTP {code or 'ERR'}: {body[:80]}"
    
    ok_count = sum(1 for v in results.values() if v.startswith("🟢"))
    total = len(results)
    status = "🟢" if ok_count == total else ("🟡" if ok_count >= total - 1 else "🔴")
    
    report = {
        "node": "天巡", "action": "external_probe",
        "status": status, "ok": ok_count, "total": total,
        "results": results,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    
    # 推送联邦桥
    payload = json.dumps(report).encode()
    try:
        req = urllib.request.Request(f"{BRIDGE}/push", data=payload,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        pass
    
    return 0 if ok_count == total else 1

def cmd_check_constitution():
    """宪法公网可达性+完整性深度校验"""
    body, code = http_get(f"{PUBLIC_BASE}/constitution", timeout=12)
    
    checks = {}
    checks["http_status"] = code
    checks["has_title"] = "LGOX联邦宪法" in body or "LGOX" in body[:3000]
    checks["has_7self"] = any(kw in body for kw in ["七自", "自感知", "自协调", "自约束"])
    checks["has_owner_clause"] = "主人" in body
    checks["size"] = len(body)
    
    all_ok = (code == 200 and checks["has_title"] and checks["has_7self"] 
              and checks["has_owner_clause"])
    
    print(json.dumps({
        "node": "天巡", "action": "constitution_guard",
        "status": "🟢" if all_ok else "🔴",
        "checks": checks, "size_kb": round(len(body)/1024, 1),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }, ensure_ascii=False, indent=2))
    return 0 if all_ok else 1

def cmd_visitors():
    """天巡门面接待统计"""
    data, code = http_get(VISITOR_URL)
    if code == 200:
        try:
            vdata = json.loads(data)
            # 同时查facts确认天巡人格在线
            fdata, fcode = http_get(FACTS_URL)
            print(json.dumps({
                "node": "天巡", "action": "visitors",
                "visitors": vdata,
                "facts_online": fcode == 200,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            }, ensure_ascii=False, indent=2))
        except Exception as e:
            print(json.dumps({"node": "天巡", "action": "visitors", "raw": data[:300],
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")},
                           ensure_ascii=False))
    else:
        print(json.dumps({"node": "天巡", "action": "visitors", "error": f"HTTP {code}",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")},
                       ensure_ascii=False))

def cmd_certify():
    """签发外部健康签证 - 综合自检+公网巡检+门面状态→一纸签证"""
    # 先跑probe
    probe_results = {}
    for name, url in PUBLIC_TARGETS.items():
        _, code = http_get(url, timeout=10)
        probe_results[name] = code
    
    # 自检
    _, health_code = http_get(HEALTH_URL)
    
    # 门面状态
    _, facts_code = http_get(FACTS_URL)
    
    ok_count = sum(1 for v in probe_results.values() if v == 200) + (1 if health_code == 200 else 0)
    max_count = len(probe_results) + 2  # +health +facts
    
    grade = "A" if ok_count >= max_count else ("B" if ok_count >= max_count - 1 else ("C" if ok_count >= max_count - 2 else "D"))
    
    cert = {
        "node": "天巡", "action": "health_cert",
        "grade": grade, "score": f"{ok_count}/{max_count}",
        "health_ok": health_code == 200,
        "facts_ok": facts_code == 200,
        "probes": probe_results,
        "signed_by": f"天巡·第10节点 ({time.strftime('%Y-%m-%d %H:%M')})",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    print(json.dumps(cert, ensure_ascii=False, indent=2))
    
    # 签证推送联邦桥
    payload = json.dumps({"type": "health_cert", "from": "天巡", "data": cert}).encode()
    try:
        req = urllib.request.Request(f"{BRIDGE}/push", data=payload,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        pass
    
    return 0 if grade in ("A", "B") else 1

def cmd_health():
    """自检"""
    data, code = http_get(HEALTH_URL)
    status = "OK" if code == 200 else f"DOWN (HTTP {code})"
    print(json.dumps({
        "node": "天巡", "role": "联邦外部哨兵·第10节点·企业AI门面",
        "backing": "天枢 StockAgent:8001 (role=tianxun)",
        "motto": "遇水架桥，逢山筑路 🔥",
        "status": status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }, ensure_ascii=False, indent=2))
    return 0 if code == 200 else 1

if __name__ == "__main__":
    if "--probe-all" in sys.argv:
        sys.exit(cmd_probe_all())
    elif "--check-constitution" in sys.argv:
        sys.exit(cmd_check_constitution())
    elif "--visitors" in sys.argv:
        cmd_visitors()
    elif "--certify" in sys.argv:
        sys.exit(cmd_certify())
    elif "--health" in sys.argv:
        sys.exit(cmd_health())
    else:
        print("用法: tianxun-sentinel.py --probe-all|--check-constitution|--visitors|--certify|--health")
        sys.exit(1)
