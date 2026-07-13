#!/opt/homebrew/bin/python3
"""
Logent Federation Heartbeat + Event Bus Agent v1.0
Uses 地枢 Redis pub/sub for real-time node communication.
Deploy on ALL federation nodes.

Heartbeat: every 180s via channel "logent:heartbeat"
Commands:  subscribe to "logent:command"
Events:    publish/receive via "logent:event"
Alerts:    publish via "logent:alert"
"""
import json
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import uuid

NODE_NAME = {
    "1mac-studio": "tianshu",
    "1deMac-Studio.local": "tianshu",
    "spark-5438": "dishu",
    "spark-abbd": "tiangong",
    "mac-mini": "linglong",
    "Mac-mini.local": "linglong",
}.get(platform.node(), platform.node())

# ── Config ──
REDIS_HOST = "100.116.0.29"
REDIS_HOST_LOCAL = "localhost"

# Auto-detect: if we are on 地枢, use localhost for Redis
_IS_DISHU_LOCAL = (
    platform.node() in ("spark-5438",)
    or
    NODE_NAME == "dishu"
)  # 地枢 is running Redis locally
REDIS_PORT = 6379
HEARTBEAT_INTERVAL = 180  # 3 minutes
MISS_THRESHOLD = 3

# ── Channels ──
CH_HEARTBEAT = "logent:heartbeat"
CH_COMMAND = "logent:command"
CH_EVENT = "logent:event"
CH_ALERT = "logent:alert"

# ── Node service map ──
NODE_SERVICES = {
    "tianshu": {
        "checks": [("Hermes GW", "tcp", "localhost", 8089),
                    ("StockAgent API", "tcp", "localhost", 8001),
                    ("HCI Panel", "tcp", "localhost", 8098)],
        "http_checks": [("信号面板", "http://localhost/signals")]
    },
    "dishu": {
        "checks": [("Onyx", "tcp", "localhost", 8088),
                    ("FAQ API", "tcp", "localhost", 8899),
                    ("Register API", "tcp", "localhost", 8898),
                    ("Redis", "tcp", "localhost", 6379)],
        "http_checks": [("Onyx", "http://localhost:8088"),
                        ("FAQ API", "http://localhost:8899/health"),
                        ("Reg API", "http://localhost:8898/health")]
    },
    "tiangong": {
        "checks": [("ds4 Inference", "tcp", "localhost", 8000)],
        "http_checks": [("ds4", "http://localhost:8000/v1/models")]
    },
    "linglong": {
        "checks": [("Hermes GW", "process", "hermes_cli.main gateway"),
                    ("Fed Agent", "process", "logent-federation-agent"),
                    ("Sentinel", "process", "logent-sentinel")],
        "http_checks": [("信号面板", "http://localhost/signals")]
    },
    "taiyi": {
        "checks": [("Fed Agent", "process", "logent-agent-taiyi")],
        "http_checks": [("信号面板", "http://localhost/signals")]
    }
}


def check_port(host, port, timeout=3):
    """TCP port check"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False


def check_http(url, timeout=5):
    """HTTP health check"""
    try:
        import urllib.request
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.status == 200
    except:
        return False


def check_process(proc_name, timeout=3):
    """Process check using pgrep"""
    try:
        r = subprocess.run(["pgrep", "-f", proc_name], capture_output=True, timeout=timeout)
        return r.returncode == 0
    except:
        return False


def get_system_health():
    """Get local system metrics"""
    health = {
        "node": NODE_NAME,
        "hostname": platform.node(),
        "timestamp": time.time(),
        "services": {},
        "load": None,
        "disk": None,
        "memory": None
    }
    
    # Service checks
    node_config = NODE_SERVICES.get(NODE_NAME, {"checks": [], "http_checks": []})
    for item in node_config["checks"]:
        if len(item) == 4:
            name, method, host, port = item
            if method == "tcp":
                health["services"][name] = check_port(host, port)
            else:
                health["services"][name] = False
        elif len(item) == 3:
            name, method, proc_name = item
            if method == "process":
                health["services"][name] = check_process(proc_name)
            else:
                health["services"][name] = False
    for name, url in node_config["http_checks"]:
        health["services"][name] = check_http(url)
    
    # System metrics
    try:
        if sys.platform == "darwin":
            load = os.getloadavg()
            health["load"] = {"1m": load[0], "5m": load[1], "15m": load[2]}
            
            # Memory (macOS)
            result = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=3)
            for line in result.stdout.split("\n"):
                if "free" in line.lower():
                    try:
                        free_pages = int(line.split(":")[1].strip().rstrip("."))
                        health["memory"] = f"{free_pages * 16384 / 1024 / 1024:.0f}MB free"
                    except:
                        pass
                    break
            
            # Disk
            result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=3)
            parts = result.stdout.split("\n")[1].split()
            if len(parts) >= 5:
                health["disk"] = f"{parts[4]} used"
        else:
            # Linux
            try:
                result = subprocess.run(["uptime"], capture_output=True, text=True, timeout=3)
                load_str = result.stdout.split("load average:")[-1].strip()
                health["load"] = load_str
            except:
                pass
            
            result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=3)
            parts = result.stdout.split("\n")[1].split()
            if len(parts) >= 5:
                health["disk"] = f"{parts[4]} used"
                
            result = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=3)
            for line in result.stdout.split("\n"):
                if "Mem:" in line:
                    health["memory"] = line.split()[1]
                    break
    except:
        pass
    
    return health


def publish_heartbeat(r):
    """Publish heartbeat to Redis + store as key"""
    health = get_system_health()
    message = json.dumps({
        "type": "heartbeat",
        "node": NODE_NAME,
        "node_id": f"{NODE_NAME}@{platform.node()}",
        "timestamp": time.time(),
        "health": health
    })
    try:
        # Pub/sub for real-time subscribers
        r.publish(CH_HEARTBEAT, message)
        # Stored key for health checkers (TTL = 2 heartbeat intervals)
        key = f"logent:heartbeat:{NODE_NAME}"
        r.setex(key, HEARTBEAT_INTERVAL * 2, message)
        return True
    except Exception as e:
        print(f"[LOGENT] Heartbeat publish failed: {e}", flush=True)
        return False


def handle_command(message):
    """Process a federation command"""
    try:
        data = json.loads(message["data"])
        cmd = data.get("command", "")
        source = data.get("source", "")
        
        print(f"[LOGENT] Command from {source}: {cmd}")
        
        if cmd == "ping":
            return {"type": "pong", "node": NODE_NAME, "timestamp": time.time()}
        elif cmd == "restart_service":
            service = data.get("service", "")
            print(f"[LOGENT] Restarting service: {service}")
            # Future: systemctl restart
        elif cmd == "sync_now":
            print(f"[LOGENT] Sync requested by {source}")
        elif cmd == "update_status":
            return get_system_health()
    except Exception as e:
        print(f"[LOGENT] Command error: {e}")
    return None


def subscribe_loop(r):
    """Subscribe to federation channels"""
    pubsub = r.pubsub()
    pubsub.subscribe(CH_COMMAND, CH_EVENT)
    
    print(f"[LOGENT] Subscribed to: {CH_COMMAND}, {CH_EVENT}")
    
    for message in pubsub.listen():
        if message["type"] == "message":
            channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
            
            if channel == CH_COMMAND:
                response = handle_command(message)
                if response:
                    r.publish(CH_EVENT, json.dumps(response))
            elif channel == CH_EVENT:
                # Log but don't react to our own events
                pass


def main():
    redis_host = REDIS_HOST_LOCAL if _IS_DISHU_LOCAL else REDIS_HOST
    print(f"═" * 50, flush=True)
    print(f"🔷 Logent Federation Agent v1.0", flush=True)
    print(f"   Node: {NODE_NAME}", flush=True)
    print(f"   Redis: {redis_host}:{REDIS_PORT}", flush=True)
    print(f"═" * 50, flush=True)
    
    # Connect to Redis
    try:
        import redis
        r = redis.Redis(host=redis_host, port=REDIS_PORT, db=0, socket_timeout=5, socket_connect_timeout=5)
        r.ping()
        print(f"[LOGENT] Redis connected ✅", flush=True)
    except ImportError:
        print(f"[LOGENT] redis-py not installed. Install: pip install redis", flush=True)
        # Start heartbeat-only mode without Redis
        _heartbeat_no_redis()
        return
    except Exception as e:
        print(f"[LOGENT] Redis connection failed: {e}")
        _heartbeat_no_redis()
        return
    
    # Start subscription thread
    sub_thread = threading.Thread(target=subscribe_loop, args=(r,), daemon=True)
    sub_thread.start()
    
    # Main heartbeat loop
    print(f"[LOGENT] Heartbeat every {HEARTBEAT_INTERVAL}s")
    cycle = 0
    
    try:
        while True:
            cycle += 1
            # Publish heartbeat
            ok = publish_heartbeat(r)
            print(f"[{time.strftime('%H:%M:%S')}] ♥ Cycle {cycle} | Published: {ok}")
            
            # Check Redis connection health
            try:
                r.ping()
            except:
                print(f"[LOGENT] ⚠️ Redis lost, reconnecting...")
                try:
                    r = redis.Redis(host=redis_host, port=REDIS_PORT, db=0)
                    r.ping()
                except:
                    print(f"[LOGENT] ❌ Redis still down")
            
            time.sleep(HEARTBEAT_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n[LOGENT] Shutting down")


def _heartbeat_no_redis():
    """Fallback: log heartbeat to file when Redis is unavailable"""
    print(f"[LOGENT] Running in file-log mode (no Redis)")
    log_dir = "/tmp/logent"
    os.makedirs(log_dir, exist_ok=True)
    
    try:
        while True:
            health = get_system_health()
            log_entry = json.dumps(health)
            
            with open(f"{log_dir}/heartbeat-{NODE_NAME}.log", "a") as f:
                f.write(log_entry + "\n")
            
            print(f"[{time.strftime('%H:%M:%S')}] ♥ {NODE_NAME} | Services: {sum(health['services'].values())}/{len(health['services'])}")
            time.sleep(HEARTBEAT_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n[LOGENT] Shutting down")


if __name__ == "__main__":
    main()
