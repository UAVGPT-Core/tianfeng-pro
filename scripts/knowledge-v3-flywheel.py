#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║  知识飞轮v3.0 — NGC全火力·多源融合·深度富化             ║
║  雷达v4→NGC富化→地枢LGE→联邦同步→六合闭环              ║
╚══════════════════════════════════════════════════════════╝
"""
import json, os, time, subprocess, urllib.request
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / "lgox-ops" / "data" / "knowledge-v3"
LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"
TIANGONG = "http://100.118.207.31:11434"

def log(msg):
    print(f"[{datetime.now().strftime('%m%d-%H%M%S')}] {msg}", flush=True)

def ngc_enrich(raw_knowledge):
    """NGC 30B深度富化原始知识"""
    cmd = f"""ssh -o ConnectTimeout=5 dgx1 'python3 -c "
import urllib.request, json
with open(\"/tmp/nvkey.env\") as f:
    key=f.read().strip().split(\"=\",1)[1].strip().strip(chr(34)).strip(chr(39))
prompt=f\"\"\"你是LGOX联邦知识富化引擎。将以下原始知识提炼为结构化基因(100-150字):
1.核心概念 2.联邦用途 3.接入方式 4.竞品对比
原始知识: {raw_knowledge[:2000]}\"\"\"
body=json.dumps({{\"model\":\"nvidia/nemotron-3-nano-30b-a3b\",\"messages\":[{{\"role\":\"user\",\"content\":prompt}}],\"max_tokens\":200,\"temperature\":0.3}}).encode()
req=urllib.request.Request(\"https://integrate.api.nvidia.com/v1/chat/completions\",data=body,headers={{\"Authorization\":f\"Bearer {{key}}\",\"Content-Type\":\"application/json\"}})
d=json.loads(urllib.request.urlopen(req,timeout=30).read())
print(d[\"choices\"][0][\"message\"][\"content\"])
" 2>/dev/null'"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=40)
        return r.stdout.strip() if r.stdout.strip() else None
    except:
        return None

def tiangong_enrich(raw_knowledge):
    """天工GPU富化·零成本降级"""
    try:
        prompt = f"提炼为LGOX基因(80字): {raw_knowledge[:800]}"
        body = json.dumps({"model": "qwen2.5:14b", "messages": [{"role": "user", "content": prompt}],
            "stream": False, "options": {"temperature": 0.3, "num_predict": 150}}).encode()
        req = urllib.request.Request(f"{TIANGONG}/api/chat", data=body,
            headers={"Content-Type": "application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=15).read())
        return d["message"]["content"].strip()
    except:
        return raw_knowledge[:200]

def run_flywheel():
    """知识飞轮主循环·NGC富化→写入LGE→六合闭环"""
    log("═══ 知识飞轮v3.0 · NGC全火力 ═══")
    
    # 拉取近期未富化基因
    try:
        req = urllib.request.Request(f"{LGE_URL}/genes/search",
            data=json.dumps({"query": "雷达 外部 知识 2026", "n_results": 10}).encode(),
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        resp = urllib.request.urlopen(req, timeout=10)
        genes = json.loads(resp.read()).get("results", [])
    except:
        log("LGE不可达")
        genes = []

    enriched = 0
    for gene in genes[:8]:
        content = gene.get("content", "")[:500]
        fitness = gene.get("fitness", gene.get("fitness_score", 0.3))
        
        if len(content) < 50 or fitness > 0.7:
            continue
        
        # NGC 30B深度富化
        enriched_content = ngc_enrich(content)
        if not enriched_content:
            enriched_content = tiangong_enrich(content)
        
        if enriched_content and len(enriched_content) > 30:
            # 写富化基因
            new_gene = {
                "content": f"[知识飞轮v3.0·NGC富化] {enriched_content[:400]}",
                "memory_type": "semantic",
                "source": "知识飞轮v3.0/NGC-30B富化",
                "fitness_score": min(0.75, fitness + 0.15),
                "tags": ["NGC富化", "知识飞轮v3.0"]
            }
            try:
                data = json.dumps(new_gene).encode()
                req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data,
                    headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
                urllib.request.urlopen(req, timeout=8)
                enriched += 1
                log(f"  ✅ 富化: fitness {fitness:.2f}→{new_gene['fitness_score']:.2f}")
            except:
                log("  💾 LGE写入失败·跳过")

    summary = f"知识飞轮v3.0·{datetime.now().strftime('%m%d%H%M')}·NGC富化{enriched}条"
    log(f"✅ {summary}")
    return enriched

if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    run_flywheel()
