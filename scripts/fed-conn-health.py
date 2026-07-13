#!/usr/bin/env python3
"""LGOX联邦多路径连接健康监控 v1.1 - 含8766副桥"""
import subprocess, json, time, os, socket
from datetime import datetime

FED_BRIDGE = "http://100.100.89.2:8765"
LOG_FILE = os.path.expanduser("~/lgox-ops/logs/conn-health.log")
STATUS_FILE = os.path.expanduser("~/lgox-ops/data/conn-health.json")

NODE_PATHS = {
    "天枢": [
        {"name": "雷雳", "host": "192.168.3.3", "port": 22, "type": "tcp", "timeout": 3, "prio": 1},
        {"name": "WiFi", "host": "100.100.89.2", "port": 22, "type": "tcp", "timeout": 5, "prio": 2},
        {"name": "联邦桥8765", "host": "100.100.89.2", "port": 8765, "type": "http", "endpoint": "/health", "timeout": 5, "prio": 3},
        {"name": "副桥8766", "host": "100.100.89.2", "port": 8766, "type": "http", "endpoint": "/health", "timeout": 5, "prio": 4},
    ],
    "地枢": [
        {"name": "直连", "host": "100.116.0.29", "port": 22, "type": "tcp", "timeout": 5, "prio": 1},
        {"name": "跳板", "host": "100.116.0.29", "type": "ssh", "alias": "dgx2", "timeout": 10, "prio": 2},
        {"name": "LGE", "host": "100.116.0.29", "port": 8200, "type": "http", "endpoint": "/health", "timeout": 5, "prio": 3},
    ],
    "天工": [
        {"name": "直连", "host": "100.118.207.31", "port": 22, "type": "tcp", "timeout": 5, "prio": 1},
        {"name": "跳板", "host": "100.118.207.31", "type": "ssh", "alias": "dgx1", "timeout": 10, "prio": 2},
        {"name": "Ollama", "host": "100.118.207.31", "port": 11434, "type": "http", "endpoint": "/api/tags", "timeout": 5, "prio": 3},
    ],
    "织网": [
        {"name": "直连", "host": "100.127.112.128", "port": 22222, "type": "tcp", "timeout": 5, "prio": 1},
        {"name": "跳板", "host": "100.127.112.128", "type": "ssh", "alias": "zhiwang-via-tianshu", "timeout": 10, "prio": 2},
    ],
    "太一": [
        {"name": "SSH", "host": "100.103.193.98", "port": 22, "type": "tcp", "timeout": 3, "prio": 1},
    ],
    "天玑": [
        {"name": "跳板", "host": "100.122.142.74", "type": "ssh", "alias": "tianji-via-tianshu", "timeout": 10, "prio": 1},
    ],
}

def check_tcp(host, port, timeout=3):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True, None
    except Exception as e:
        return False, str(e)

def check_ssh(alias, timeout=5):
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", f"ConnectTimeout={timeout}",
             "-o", "BatchMode=yes", alias, "echo OK"],
            capture_output=True, text=True, timeout=timeout+5
        )
        return r.returncode == 0 and "OK" in r.stdout, r.stderr[:100] if r.stderr else None
    except Exception as e:
        return False, str(e)

def check_http(host, port, endpoint="/", timeout=5):
    import urllib.request
    try:
        url = f"http://{host}:{port}{endpoint}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, resp.status
    except Exception as e:
        return False, str(e)

def main():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    results = {}
    alerts = []
    node_status = {}
    
    for node_name, paths in NODE_PATHS.items():
        node_results = []
        alive_count = 0
        
        for path in paths:
            ptype = path["type"]
            ok, detail = False, "unknown"
            
            if ptype == "ssh":
                ok, detail = check_ssh(path["alias"], path.get("timeout", 5))
            elif ptype == "tcp":
                ok, detail = check_tcp(path["host"], path["port"], path.get("timeout", 3))
            elif ptype == "http":
                ok, detail = check_http(path["host"], path["port"], path.get("endpoint", "/"), path.get("timeout", 5))
            
            if ok:
                alive_count += 1
            
            node_results.append({
                "path": path["name"],
                "type": ptype,
                "ok": ok,
                "detail": str(detail)[:100] if detail else "",
            })
        
        results[node_name] = node_results
        total = len(paths)
        
        if alive_count == total:
            status = "🟢"
        elif alive_count >= 1:
            status = "🟡"
            alerts.append(f"{node_name}: {alive_count}/{total}路径存活")
        else:
            status = "🔴"
            alerts.append(f"🚨{node_name}: 0/{total}全部断裂!")
        
        node_status[node_name] = {"status": status, "alive": alive_count, "total": total}
    
    with open(STATUS_FILE, "w") as f:
        json.dump({"timestamp": now, "nodes": node_status, "details": results, "alerts": alerts},
                  f, ensure_ascii=False, indent=2)
    
    summary = " | ".join([f"{n}{s['status']}{s['alive']}/{s['total']}" for n, s in node_status.items()])
    with open(LOG_FILE, "a") as f:
        f.write(f"[{now}] {summary}\n")
        for a in alerts:
            f.write(f"  {a}\n")
    
    if alerts:
        try:
            import urllib.request
            alert_msg = f"🔗连接告警 [{now}]\n" + "\n".join(alerts)
            data = json.dumps({"to": "天枢", "from": "灵龙", "content": alert_msg}).encode()
            req = urllib.request.Request(f"{FED_BRIDGE}/messages/send", data=data,
                                        headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except:
            pass
    
    print(f"LGOX连接健康 {now}")
    for node_name, s in node_status.items():
        paths_str = " ".join(["✅" if r["ok"] else "❌" for r in results[node_name]])
        print(f"  {s['status']} {node_name:6s} {s['alive']}/{s['total']} [{paths_str}]")
    print(f"\n{'🟢 全绿' if not alerts else f'⚠️ {len(alerts)}条告警'}")

if __name__ == "__main__":
    main()
