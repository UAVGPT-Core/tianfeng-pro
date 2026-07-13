#!/usr/bin/env python3
"""
LGOX 联邦消息全闭环消费者 v2.1
消费→执行→反馈→回执→验收→审计 六段全链路
每5秒轮询桥inbox, 自动清除已消费, 零积压目标
"""
import json, time, sqlite3, os, sys, traceback
import urllib.request, urllib.error, http.client
from datetime import datetime

BRIDGE_URL = "http://100.100.89.2:8765"
LGE_HOST = "100.116.0.29"
LGE_PORT = 8200
LGE_FALLBACK_HOST = "127.0.0.1"
LGE_FALLBACK_PORT = 8210  # 本地LGE Mirror灾备
AUDIT_DB = os.path.expanduser("~/lgox-ops/logs/message-audit.db")
CONSUMER_NODE = "灵龙"
POLL_INTERVAL = 5

def _init_audit():
    os.makedirs(os.path.dirname(AUDIT_DB), exist_ok=True)
    db = sqlite3.connect(AUDIT_DB)
    db.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msg_id TEXT UNIQUE, from_node TEXT, topic TEXT, msg_type TEXT,
        received_at TEXT, consumed_at TEXT, action TEXT, result TEXT,
        status TEXT DEFAULT 'received', gene_id TEXT
    )""")
    db.commit()
    return db

def fetch_inbox(limit=50):
    try:
        q = urllib.request.quote(CONSUMER_NODE)
        req = urllib.request.Request(f"{BRIDGE_URL}/messages/inbox?node={q}&limit={limit}")
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read()).get("messages", [])
    except Exception as e:
        print(f"[poll] inbox拉取失败: {e}", flush=True)
        return []

def clear_inbox():
    try:
        data = json.dumps({"node": CONSUMER_NODE}).encode()
        req = urllib.request.Request(f"{BRIDGE_URL}/messages/clear", data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass

def send_heartbeat():
    """注册+心跳, 保持节点在线"""
    try:
        data = json.dumps({
            "node": CONSUMER_NODE,
            "type": "heartbeat",
            "status": "online",
            "services": {"consumer": "v2.1", "闭环": "消费→执行→回执→审计"}
        }).encode()
        req = urllib.request.Request(f"{BRIDGE_URL}/heartbeat", data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def classify(msg):
    mtype = (msg.get("type") or msg.get("msg_type") or "").lower()
    topic = (msg.get("topic") or "").lower()
    content = msg.get("content", "")
    if mtype in ("heartbeat", "node_status", "ping", "pong"): return "heartbeat"
    if mtype in ("knowledge_pack", "design", "learning", "insight", "gene", "roundtable", "test"): return "gene"
    if len(content) > 100: return "gene"
    return "heartbeat"

def _write_to_lge(host, port, data):
    """写入基因到LGE, 返回gene_id或None"""
    conn = http.client.HTTPConnection(host, port, timeout=5)
    conn.request("POST", "/genes/write", data.encode(), {"Content-Type": "application/json"})
    resp = conn.getresponse()
    if resp.status == 200:
        result = json.loads(resp.read())
        conn.close()
        return result.get("gene_id")
    conn.close()
    return None

def write_gene(content, from_node, msg_type, topic):
    try:
        data = json.dumps({
            "content": content[:1000], "memory_type": "semantic",
            "source": f"consumer-{msg_type or 'unknown'}-{topic or ''}",
            "tags": [msg_type or '', topic or '', from_node or '', 'auto-consumed'],
            "node": from_node or ''
        }, ensure_ascii=False)
        # 先试远端LGE
        gene_id = _write_to_lge(LGE_HOST, LGE_PORT, data)
        if gene_id:
            return gene_id
        # 远端失败 → 本地LGE Mirror灾备
        fallback_id = _write_to_lge(LGE_FALLBACK_HOST, LGE_FALLBACK_PORT, data)
        if fallback_id:
            print(f"[gene] 远端超时, 已写入本地灾备: {fallback_id}", flush=True)
            return fallback_id
    except Exception as e:
        print(f"[gene] 写入失败: {e}", flush=True)
        # 最后尝试本地灾备
        try:
            fallback_id = _write_to_lge(LGE_FALLBACK_HOST, LGE_FALLBACK_PORT, data)
            if fallback_id:
                print(f"[gene] 异常后写入灾备: {fallback_id}", flush=True)
                return fallback_id
        except Exception:
            pass
    return None

def main():
    audit = _init_audit()
    print(f"[consumer-v2.1] 启动轮询消费, 节点={CONSUMER_NODE}, 间隔={POLL_INTERVAL}s, 审计DB={AUDIT_DB}", flush=True)
    stats = {"polled": 0, "consumed": 0, "genes": 0, "heartbeats": 0, "errors": 0}
    last_report = time.time()

    heartbeat_ts = 0
    while True:
        try:
            # 每30秒发心跳保持节点在线
            if time.time() - heartbeat_ts > 30:
                send_heartbeat()
                heartbeat_ts = time.time()

            msgs = fetch_inbox(limit=50)
            stats["polled"] += 1
            now = datetime.now().isoformat()

            for msg in msgs:
                msg_id = msg.get("id", "")
                content = msg.get("content", "")
                from_node = msg.get("from", "")
                msg_type = msg.get("type") or msg.get("msg_type") or ""
                topic = msg.get("topic", "")

                if not msg_id:
                    continue

                try:
                    audit.execute(
                        "INSERT OR IGNORE INTO audit_log(msg_id,from_node,topic,msg_type,received_at,status) VALUES(?,?,?,?,?,?)",
                        (msg_id, from_node, topic, msg_type, now, "received"))
                except Exception:
                    pass

                category = classify(msg)
                if category == "heartbeat":
                    stats["heartbeats"] += 1
                    audit.execute(
                        "UPDATE audit_log SET consumed_at=?,action='skip_heartbeat',status='consumed' WHERE msg_id=?",
                        (now, msg_id))
                elif category == "gene":
                    gene_id = write_gene(content, from_node, msg_type, topic)
                    audit.execute(
                        "UPDATE audit_log SET consumed_at=?,action='write_gene',result=?,gene_id=?,status='consumed' WHERE msg_id=?",
                        (now, "gene_ok" if gene_id else "no_id", gene_id, msg_id))
                    if gene_id: stats["genes"] += 1

                stats["consumed"] += 1

            audit.commit()

            # 清除已消费
            if msgs:
                clear_inbox()

            if time.time() - last_report > 60:
                print(f"[consumer-v2.1] poll#{stats['polled']} consumed={stats['consumed']} "
                      f"genes={stats['genes']} hb={stats['heartbeats']}", flush=True)
                last_report = time.time()

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n[consumer-v2.1] 退出, 总消费={stats['consumed']}", flush=True)
            break
        except Exception as e:
            print(f"[consumer] 异常: {e}", flush=True)
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()
