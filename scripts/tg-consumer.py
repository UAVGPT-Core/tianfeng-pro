#!/usr/bin/env python3
"""天工桥积压消费者·灵龙侧主动poll"""
import json, urllib.request, time

TG_URL = "http://100.118.207.31:8765"
LGE_URL = "http://100.116.0.29:8200"

def consume():
    # 1. 查天工积压
    try:
        req = urllib.request.Request(f"{TG_URL}/messages/health")
        with urllib.request.urlopen(req, timeout=5) as r:
            health = json.loads(r.read())
        unread = health.get("total_unread", 0)
        print(f"天工积压: {unread}")
        if unread == 0:
            return
    except Exception as e:
        print(f"查询失败: {e}")
        return

    # 2. 拉取天工待收消息
    try:
        req = urllib.request.Request(f"{TG_URL}/messages/inbox?node=天工")
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        msgs = data.get("messages", [])
        print(f"获取{len(msgs)}条")
    except Exception as e:
        print(f"拉取失败: {e}")
        return

    # 3. 逐条处理
    for msg in msgs[:50]:
        content = msg.get("content", "")
        msg_id = msg.get("message_id", msg.get("id", ""))
        # 知识类→LGE基因库
        if len(content) > 20:
            try:
                payload = json.dumps({
                    "gene_id": f"GENE-CONSUME-{msg_id[:12]}",
                    "content": content[:1000],
                    "category": "consumed",
                    "domain": "general",
                    "quality_score": 0.3,
                    "tags": ["天工-积压消费"]
                }).encode()
                req = urllib.request.Request(f"{LGE_URL}/genes/write", data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=3)
            except:
                pass
    
    print(f"consumed {len(msgs[:50])} messages")

if __name__ == "__main__":
    consume()
