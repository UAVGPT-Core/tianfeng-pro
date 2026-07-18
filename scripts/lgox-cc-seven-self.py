#!/usr/bin/env python3
"""
LGOX-CC 七自飞轮 v1.0
自感知·自协调·自愈合·自进化·自迭代·自反思·自约束
基因ID: GENE-PRO-lgox-cc-seven-self
"""
import json, urllib.request, subprocess, time, os, hashlib
from datetime import datetime

BRIDGE = "http://127.0.0.1:8765"
LGE = "http://100.116.0.29:8200"
NODE = "LGOX-CC"
LOG = os.path.expanduser("~/lgox-ops/logs/lgox-cc-seven.log")

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    with open(LOG, "a") as f:
        f.write(line + "\n")
    print(line)

def seven_self():
    results = {}
    
    # 1. 自感知: 检测环境和自身状态
    try:
        r = urllib.request.urlopen(f"{BRIDGE}/health", timeout=5)
        bridge_ok = json.loads(r.read()).get("status") == "ok"
    except:
        bridge_ok = False
    
    try:
        r = subprocess.run(["npx", "codex", "--version"], capture_output=True, timeout=15)
        codex_ok = r.returncode == 0
    except:
        # retry once — npx cache can be slow
        try:
            r = subprocess.run(["npx", "codex", "--version"], capture_output=True, timeout=15)
            codex_ok = r.returncode == 0
        except:
            codex_ok = False
    
    try:
        r = subprocess.run(["which", "lgox-cc"], capture_output=True)
        cc_which = r.returncode == 0
    except:
        cc_which = False
    cc_script = os.path.exists(os.path.expanduser("~/lgox-ops/scripts/lgox-cc-v7.py"))
    cc_ok = cc_which or cc_script
    
    results["自感知"] = f"bridge={bridge_ok} codex={codex_ok} lgox-cc={cc_ok}"
    log(f"自感知: {results['自感知']}")
    
    # 2. 自协调: 心跳+注册到联邦桥
    try:
        payload = json.dumps({"name": NODE, "services": {"codex": "0.2.3", "lgox-cc": "v6.0"}}).encode()
        req = urllib.request.Request(f"{BRIDGE}/heartbeat", data=payload,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        results["自协调"] = "heartbeat_ok"
    except:
        results["自协调"] = "heartbeat_fail"
    log(f"自协调: {results['自协调']}")
    
    # 3. 自愈合: 消费积压·修复断裂
    try:
        r = urllib.request.urlopen(f"{BRIDGE}/messages/health", timeout=5)
        d = json.loads(r.read())
        unread = d.get("per_node", {}).get(NODE, 0)
        if unread > 0:
            # 清零
            payload = json.dumps({"node": NODE}).encode()
            req = urllib.request.Request(f"{BRIDGE}/messages/clear", data=payload,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        results["自愈合"] = f"consumed_{unread}"
    except:
        results["自愈合"] = "fail"
    log(f"自愈合: {results['自愈合']}")
    
    # 4. 自进化: 拉取最新基因学习
    evidence = []
    evolution_source = "remote"
    # 一级: 远程统一查询 (SSH隧道到天枢 unified-query-api)
    try:
        payload = json.dumps({"query": "七自飞轮 AI灯塔", "timeout": 5}).encode()
        req = urllib.request.Request("http://127.0.0.1:18769/query", data=payload,
            headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=8)
        d = json.loads(r.read())
        evidence = d.get("evidence", []) or d.get("results", []) or d.get("genes", [])
    except:
        evolution_source = "lga_fallback"
        # 二级: LGA本地基因代理
        try:
            payload = json.dumps({"query": "七自飞轮", "n_results": 5}).encode()
            req = urllib.request.Request("http://127.0.0.1:8202/genes/search", data=payload,
                headers={"Content-Type": "application/json"})
            r = urllib.request.urlopen(req, timeout=5)
            d = json.loads(r.read())
            evidence = d.get("results", []) or d.get("genes", [])
        except:
            evolution_source = "local_fallback"
            # 三级: 本地SQLite查询
            try:
                import sqlite3
                db = os.path.expanduser("~/lgox-ops/lge.db")
                if os.path.exists(db):
                    conn = sqlite3.connect(db)
                    cur = conn.cursor()
                    cur.execute("SELECT content FROM genes WHERE content LIKE ? LIMIT 5", ("%七自%",))
                    evidence = [row[0][:200] for row in cur.fetchall()]
                    conn.close()
            except:
                evidence = []
    results["自进化"] = f"{evolution_source}_evidence_{len(evidence)}"
    log(f"自进化: {results['自进化']}")
    
    # 5. 自迭代: 版本检查
    ver_ok = False
    for attempt in range(2):
        try:
            r = subprocess.run(["npx", "codex", "--version"], capture_output=True, timeout=15)
            if r.returncode == 0:
                ver = r.stdout.decode().strip()
                results["自迭代"] = f"codex_{ver}"
                ver_ok = True
                break
        except:
            pass
    if not ver_ok:
        results["自迭代"] = "fail"
    log(f"自迭代: {results['自迭代']}")
    
    # 6. 自反思: 写反思基因
    gene_id = f"GENE-CC7SELF-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]}"
    try:
        payload = json.dumps({
            "gene_id": gene_id,
            "content": json.dumps(results, ensure_ascii=False),
            "category": "seven-self",
            "domain": "meta",
            "quality_score": sum(1 for v in results.values() if "fail" not in v) / len(results),
            "tags": ["LGOX-CC", "七自飞轮"]
        }).encode()
        req = urllib.request.Request(f"{LGE}/genes/write", data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=3)
        results["自反思"] = f"gene_{gene_id[:12]}"
    except:
        results["自反思"] = f"local_{gene_id[:12]}"
        # 本地存档
        with open(os.path.expanduser("~/lgox-ops/data/cc-seven-genes.jsonl"), "a") as f:
            f.write(json.dumps({"gene_id": gene_id, "results": results, "ts": time.time()}, ensure_ascii=False) + "\n")
    log(f"自反思: {results['自反思']}")
    
    # 7. 自约束: 宪法合规检查
    constitution_check = all([
        bridge_ok,  # 不能孤狼
        not any("fail" in str(v) for v in results.values()),  # 不能伪精准
    ])
    results["自约束"] = "pass" if constitution_check else "violation"
    log(f"自约束: {results['自约束']}")
    
    return results

if __name__ == "__main__":
    log("═══ LGOX-CC七自飞轮 ═══")
    results = seven_self()
    passed = sum(1 for v in results.values() if "fail" not in v and "violation" not in v)
    log(f"七自: {passed}/7 通过")
