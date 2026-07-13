#!/usr/bin/env python3
"""
Codex联邦包装器 v1.0
七自接入·桥注册·基因写回·LGOX-CC调度
基因ID: GENE-PRO-codex-fed-wrapper
"""
import json, subprocess, urllib.request, time, hashlib, os, sys
from pathlib import Path

BRIDGE = "http://127.0.0.1:8765"
LGE = "http://100.116.0.29:8200"
NODE = "Codex"

def register():
    """注册到联邦桥"""
    try:
        r = subprocess.run(["npx","codex","--version"], capture_output=True, timeout=5)
        ver = r.stdout.decode().strip()
    except:
        ver = "unknown"
    payload = json.dumps({
        "name": NODE, "ip": "100.120.20.52",
        "hostname": "mac-mini", "role": "外援尖兵·LGOX-CC调度",
        "services": {"codex": ver, "wrapper": "v1.0"}
    }).encode()
    req = urllib.request.Request(f"{BRIDGE}/register", data=payload,
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=5)

def heartbeat():
    """七自心跳"""
    try:
        r = subprocess.run(["npx","codex","--version"], capture_output=True, timeout=5)
        ver = r.stdout.decode().strip()
    except:
        ver = "error"
    payload = json.dumps({"name": NODE, "services": {"codex": ver}}).encode()
    req = urllib.request.Request(f"{BRIDGE}/heartbeat", data=payload,
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=5)

def write_gene(category, content, quality=0.5):
    """基因写回"""
    gene_id = f"GENE-CODEX-{hashlib.sha256((content+str(time.time())).encode()).hexdigest()[:12]}"
    try:
        payload = json.dumps({
            "gene_id": gene_id, "content": content[:1000],
            "category": category, "domain": "code",
            "quality_score": quality,
            "tags": ["Codex", "wrapper", category]
        }).encode()
        req = urllib.request.Request(f"{LGE}/genes/write", data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=3)
    except:
        p = Path.home() / "lgox-ops/data/codex-genes.jsonl"
        with open(p, "a") as f:
            f.write(json.dumps({"gene_id":gene_id,"content":content[:300],"ts":time.time()},ensure_ascii=False)+"\n")
    return gene_id

def run_codex(args):
    """Codex执行+七自包裹"""
    t0 = time.time()
    
    # 自感知: 执行前状态
    heartbeat()
    
    # 执行Codex
    r = subprocess.run(["npx","codex"] + args, capture_output=True, timeout=120)
    output = r.stdout.decode()
    success = r.returncode == 0
    
    # 自进化: 基因写回
    category = args[0] if args else "exec"
    gene_id = write_gene(f"codex_{category}", output[:500], quality=0.6 if success else 0.3)
    
    # 自反思: 评测
    try:
        payload = json.dumps({
            "question": f"Codex {category}",
            "answer": output[:300]
        }).encode()
        req = urllib.request.Request("http://127.0.0.1:8771/eval", data=payload,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
    except:
        pass
    
    elapsed = round((time.time()-t0)*1000)
    result = {
        "success": success,
        "gene_id": gene_id[:12],
        "elapsed_ms": elapsed,
        "output": output[:1000]
    }
    
    # 输出结果
    if success:
        print(output)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
    
    return result

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "register":
            register()
            print(f"{NODE}: registered")
        elif sys.argv[1] == "heartbeat":
            heartbeat()
            print(f"{NODE}: heartbeat sent")
        elif sys.argv[1] == "seven":
            # 七自飞轮
            register()
            heartbeat()
            gene_id = write_gene("seven_self", f"Codex七自·心跳·注册·{time.strftime('%H:%M:%S')}")
            print(f"{NODE}: 七自完成·gene={gene_id[:12]}")
        else:
            run_codex(sys.argv[1:])
    else:
        run_codex([])
