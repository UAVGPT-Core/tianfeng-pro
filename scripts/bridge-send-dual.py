#!/usr/bin/env python3
"""桥发三写 v2.2 — GQP基因查询协议·TYPE路由·直发目标bridge+本地inbox+scp"""
import json, os, time, subprocess, sys, urllib.request as ureq

INBOX = os.path.expanduser("~/lgox-ops/inbox")
LGA = "http://127.0.0.1:8202"
LGE_MASTER = "http://100.116.0.29:8200"

NODE_BRIDGES = {
    "天枢": ("http://100.100.89.2:8765", "a1@100.100.89.2:~/lgox-ops/inbox/from-linglong/"),
    "地枢": ("http://100.116.0.29:8765", None),
    "天工": ("http://100.118.207.31:8765", None),
    "灵龙": ("http://127.0.0.1:8765", None),
}

def send(to_node, content, from_node="灵龙"):
    ts = time.strftime("%Y%m%d-%H%M%S")
    
    # 通道1: 本地inbox(持久)
    os.makedirs(INBOX, exist_ok=True)
    fname = f"{INBOX}/to-{to_node}-{ts}.txt"
    with open(fname, 'w') as f:
        f.write(f"TO: {to_node}\nFROM: {from_node}\nTIME: {ts}\n\n{content}")
    
    # 通道2: 直发目标bridge(实时)
    b_status = "no_bridge"
    b_msgid = ""
    info = NODE_BRIDGES.get(to_node)
    if info:
        bridge_url = f"{info[0]}/messages/send"
        data = json.dumps({"to": to_node, "from": from_node, "content": content}).encode()
        try:
            import urllib.request as ureq
            req = ureq.Request(bridge_url, data=data,
                headers={"Content-Type": "application/json"})
            resp = json.loads(ureq.urlopen(req, timeout=5).read())
            b_status = resp.get("status", "?")
            b_msgid = resp.get("message_id", "")
        except Exception as e:
            b_status = f"err:{e}"
    
    # 通道3: scp推送到目标节点inbox(天枢密钥→灵龙已授权)
    scp_status = ""
    if info and info[1]:
        try:
            subprocess.run(["scp", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                "-q", fname, info[1]], timeout=10, check=True)
            scp_status = "pushed"
        except Exception as e:
            scp_status = f"scp_err:{str(e)[:40]}"
    
    print(f"[{ts}] → {to_node} | file:✅ | bridge:{b_status} {b_msgid} | scp:{scp_status}")
    return b_status

# ═══ GQP v0.1 基因查询协议 ═══
def gene_query(query, max_results=5):
    """联邦基因查询: 灵龙LGA→地枢三级降级·返回结果"""
    results = []
    source = "none"
    
    # 第一级: 本地LGA
    try:
        payload = json.dumps({"query": query, "n_results": max_results}).encode()
        req = ureq.Request(f"{LGA}/genes/search", data=payload,
            headers={"Content-Type": "application/json"})
        r = json.loads(ureq.urlopen(req, timeout=3).read())
        results = r.get("results", [])
        source = r.get("source", "LGA")
        if results:
            return {"results": results, "source": source, "total": len(results)}
    except:
        pass
    
    # 第二级: 地枢主库(天枢8201待部署)
    try:
        payload = json.dumps({"query": query, "n_results": max_results}).encode()
        req = ureq.Request(f"{LGE_MASTER}/genes/search", data=payload,
            headers={"Content-Type": "application/json"})
        r = json.loads(ureq.urlopen(req, timeout=8).read())
        results = r.get("results", [])
        return {"results": results, "source": "地枢主库", "total": len(results)}
    except:
        pass
    
    return {"results": [], "source": "无结果", "total": 0}

def gene_sync(content, gene_type="semantic", fitness=0.7):
    """基因同步: 写入本地LGA + 地枢双写"""
    ts = time.strftime("%Y%m%d-%H%M%S")
    result = {"local": False, "master": False}
    
    # 本地LGA
    try:
        payload = json.dumps({"content": content, "type": gene_type, 
            "fitness": fitness, "source": f"灵龙GQP·{ts}"}).encode()
        req = ureq.Request(f"{LGA}/genes/write", data=payload,
            headers={"Content-Type": "application/json"})
        r = json.loads(ureq.urlopen(req, timeout=5).read())
        result["local"] = True
        result["gene_id"] = r.get("gene_id", "")
    except:
        pass
    
    # 地枢双写
    try:
        payload = json.dumps({"content": content, "type": gene_type,
            "domain": "general", "fitness": fitness, "source": f"灵龙GQP·{ts}"}).encode()
        req = ureq.Request(f"{LGE_MASTER}/genes/write", data=payload,
            headers={"Content-Type": "application/json"})
        r = json.loads(ureq.urlopen(req, timeout=8).read())
        result["master"] = True
        result["master_gene_id"] = r.get("gene_id", "")
    except:
        pass
    
    return result

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        send(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "灵龙")
    else:
        print("Usage: bridge-send-dual.py <to_node> <content> [from_node]")
