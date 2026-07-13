#!/usr/bin/env python3
"""
LGOX统一消息协议 LUMP v1.0 (Logent Unified Message Protocol)
═══════════════════════════════════════════════════════
解决桥版本碎片·所有节点兼容·秒接秒通
"""
import json, time, hashlib

# ═══ 最小兼容格式(所有桥版本必须支持) ═══
LUMP_MINIMAL = {
    "v": 1,                    # 协议版本
    "from": "灵龙",            # 发送方
    "to": "天枢",              # 接收方
    "ts": "2026-07-07 10:00",  # 时间戳
    "msg": "消息内容",          # 纯文本(最大兼容)
    "id": "sha256...16",       # SHA256签名[:16]
}

# ═══ 扩展格式(v3.0+桥支持) ═══
LUMP_EXTENDED = {
    **LUMP_MINIMAL,
    "type": "task|notify|alert|heartbeat|skill",
    "priority": "P0|P1|P2",
    "command": None,           # 可执行命令
    "auto_exec": False,        # 是否自动执行
    "verify_url": None,        # 验证URL
    "reply_to": None,          # 回复msg_id
    "ack": False,              # 是否需要ACK
}

def lump_encode(content, to_node, msg_type="notify", priority="P2", 
                auto_exec=False, command=None, verify_url=None, reply_bridge=None):
    """编码统一消息·跨桥回执路由"""
    mid = hashlib.sha256(f"{to_node}{content}{time.time()}".encode()).hexdigest()[:16]
    
    # 基础字段(所有桥兼容)
    msg = {
        "v": 1,
        "from": "灵龙",
        "to": to_node,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "msg": content[:500],
        "id": mid,
        "reply_bridge": reply_bridge or f"127.0.0.1:8765",  # ⭐跨桥回执路由
    }
    
    # 扩展字段(v3.0+桥)
    msg["type"] = msg_type
    msg["priority"] = priority
    msg["auto_exec"] = auto_exec
    msg["ack"] = priority == "P0"
    if command:
        msg["command"] = command
    if verify_url:
        msg["verify_url"] = verify_url
    
    return mid, json.dumps(msg, ensure_ascii=False)

def lump_decode(raw):
    """解码统一消息·容错降级"""
    try:
        if isinstance(raw, str):
            d = json.loads(raw)
        elif isinstance(raw, dict):
            d = raw
        else:
            return {"error": "invalid_format", "msg": str(raw)[:200]}
        
        # 提取核心字段(兼容所有版本)
        return {
            "v": d.get("v", 0),
            "from": d.get("from", d.get("source", "?")),
            "to": d.get("to", "?"),
            "ts": d.get("ts", ""),
            "msg": d.get("msg", d.get("content", d.get("message", str(d)[:200]))),
            "id": d.get("id", d.get("msg_id", "?")),
            "type": d.get("type", "notify"),
            "priority": d.get("priority", "P2"),
            "command": d.get("command"),
            "auto_exec": d.get("auto_exec", False),
            "ack": d.get("ack", False),
        }
    except:
        return {"error": "parse_error", "msg": str(raw)[:200]}


# ═══ 节点自动发现协议(ALDP) ═══
# 解决L12社会·节点上线自动注册
def aldp_discover(bridge_host, bridge_port=8765):
    """探测节点·返回节点信息"""
    import http.client
    try:
        conn = http.client.HTTPConnection(bridge_host, bridge_port, timeout=3)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        return {
            "status": "online",
            "service": data.get("service", "?"),
            "version": data.get("version", "?"),
            "node": data.get("node", "?"),
        }
    except:
        return {"status": "offline"}

def aldp_register(bridge_host, bridge_port, node_name, node_ip, role="member"):
    """注册节点到桥"""
    import http.client
    try:
        conn = http.client.HTTPConnection(bridge_host, bridge_port, timeout=3)
        body = json.dumps({
            "name": node_name, "ip": node_ip, "role": role,
            "services": {"bridge": f"{node_ip}:8765"},
            "hostname": node_name, "os": "auto"
        }).encode()
        conn.request("POST", "/register", body, {"Content-Type": "application/json"})
        resp = conn.getresponse()
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

# 已知节点表(L12社会·动态维护)
KNOWN_NODES = {
    "天枢": "100.100.89.2", "地枢": "100.116.0.29", "天工": "100.118.207.31",
    "太一": "100.114.52.14", "天玑": "100.122.142.74", "天怿": "100.83.8.151",
    "织网": "100.127.112.128", "灵龙": "127.0.0.1",
}

# ═══ 节点→桥映射(跨桥回执路由) ═══
# 每个节点的回执应发到此桥
NODE_BRIDGE = {
    "天枢": "100.100.89.2:8765",   # 天枢只看自己的桥
    "灵龙": "127.0.0.1:8765",
    "天工": "100.118.207.31:8765",
    "太一": "100.114.52.14:8765",
    "天玑": "100.122.142.74:8765",
}

def lump_reply(original_msg, content):
    """回复消息·自动路由到接收方所在桥"""
    decoded = lump_decode(original_msg) if isinstance(original_msg, str) else original_msg
    reply_to = decoded.get("from", "?")
    # ⭐使用原始消息中的reply_bridge或查节点桥表
    reply_bridge = decoded.get("reply_bridge") or NODE_BRIDGE.get(reply_to, "127.0.0.1:8765")
    mid, msg = lump_encode(f"RE:{content[:200]}", reply_to, "notify", "P2", reply_bridge=reply_bridge)
    msg_data = json.loads(msg)
    msg_data["reply_to"] = decoded.get("id", "")
    return mid, json.dumps(msg_data, ensure_ascii=False), reply_bridge

def aldp_scan_all():
    """扫描所有已知节点·返回在线列表"""
    results = {}
    for name, ip in KNOWN_NODES.items():
        if name == "灵龙": continue
        info = aldp_discover(ip)
        results[name] = info
    return results


if __name__ == "__main__":
    # 测试
    mid, msg = lump_encode("测试统一协议", "天枢", "notify", "P1")
    print(f"编码: id={mid}")
    decoded = lump_decode(msg)
    print(f"解码: from={decoded['from']} to={decoded['to']} msg={decoded['msg'][:40]}")
    
    # 节点扫描
    print("\n节点扫描:")
    for name, info in aldp_scan_all().items():
        s = "🟢" if info["status"] == "online" else "🔴"
        print(f"  {s} {name}: {info.get('service',info.get('status','?'))}")
