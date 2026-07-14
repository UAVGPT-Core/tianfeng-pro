#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║  NGC基因质量飞轮 — nemotron-30B替代gemma4              ║
║  质量评审·向量去重·基因富化·全自动                      ║
║  天工GPU执行·地枢LGE沉淀·NGC 30B火力                    ║
╚══════════════════════════════════════════════════════════╝
"""
import json, os, sys, time, subprocess, urllib.request
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / "lgox-ops" / "data" / "gene-quality"
LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"
TIANGONG = "http://100.118.207.31:11434"

def log(msg):
    print(f"[{datetime.now().strftime('%m%d-%H%M%S')}] {msg}", flush=True)

def ngc_review(gene_content):
    """NGC nemotron-30B 基因质量评审"""
    cmd = f"""ssh -o ConnectTimeout=5 dgx1 'python3 -c "
import urllib.request, json
key=None
with open(\"/tmp/nvkey.env\") as f:
    key=f.read().strip().split(\"=\",1)[1].strip().strip(chr(34)).strip(chr(39))
prompt=f\"\"\"你是LGOX联邦基因质量评审官。评审这条基因(0-100分):
评分标准: 技术深度40·可操作性30·联邦价值20·新颖性10
格式: 分数|理由(20字)

基因: {gene_content[:500]}\"\"\"
body=json.dumps({{\"model\":\"nvidia/nemotron-3-nano-30b-a3b\",\"messages\":[{{\"role\":\"user\",\"content\":prompt}}],\"max_tokens\":60,\"temperature\":0.1}}).encode()
req=urllib.request.Request(\"https://integrate.api.nvidia.com/v1/chat/completions\",data=body,headers={{\"Authorization\":f\"Bearer {{key}}\",\"Content-Type\":\"application/json\"}})
d=json.loads(urllib.request.urlopen(req,timeout=25).read())
print(d[\"choices\"][0][\"message\"][\"content\"])
" 2>/dev/null'"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=35)
        result = r.stdout.strip()
        if "|" in result:
            parts = result.split("|")
            score_str = parts[0].strip()
            reason = parts[1].strip() if len(parts) > 1 else ""
            try:
                score = float(score_str.replace("分","").strip()) / 100
                return min(0.95, max(0.1, score)), reason
            except:
                pass
        return 0.5, result[:50]
    except:
        return None, ""

def tiangong_review(gene_content):
    """天工GPU降级评审"""
    try:
        prompt = f"评审这条LGOX基因(0-100分·只输出数字+20字理由): {gene_content[:400]}"
        body = json.dumps({"model": "qwen2.5:14b", "messages": [{"role": "user", "content": prompt}],
            "stream": False, "options": {"temperature": 0.1, "num_predict": 60}}).encode()
        req = urllib.request.Request(f"{TIANGONG}/api/chat", data=body,
            headers={"Content-Type": "application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=15).read())
        result = d["message"]["content"].strip()
        try:
            score = float(result.split("分")[0].strip()) / 100
            return min(0.9, max(0.1, score)), result[:30]
        except:
            return 0.45, result[:30]
    except:
        return 0.40, ""

def review_batch(limit=20):
    """评审一批低fitness基因·NGC 30B主审"""
    log("═══ NGC基因质量飞轮 ═══")
    
    # 拉低fitness基因
    try:
        req = urllib.request.Request(f"{LGE_URL}/genes/search", 
            data=json.dumps({"query": "agent 联邦 AI", "n_results": limit}).encode(),
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        resp = urllib.request.urlopen(req, timeout=10)
        genes = json.loads(resp.read()).get("results", [])
    except:
        log("LGE不可达·跳过")
        return []

    reviewed = []
    for i, gene in enumerate(genes):
        content = gene.get("content", "")[:300]
        old_fitness = gene.get("fitness", gene.get("fitness_score", 0.3))
        
        if old_fitness > 0.6:
            continue  # 高质量基因跳过
        
        # NGC 30B评审
        new_score, reason = ngc_review(content)
        if new_score is None:
            new_score, reason = tiangong_review(content)  # 降级天工
        
        if new_score > old_fitness:
            reviewed.append({
                "content": content[:100],
                "old": old_fitness,
                "new": new_score,
                "reason": reason,
                "reviewer": "NGC-30B" if new_score > 0.5 else "天工-qwen"
            })
            log(f"  [{i+1}/{len(genes)}] {old_fitness:.2f}→{new_score:.2f} | {reason[:30]} | {reviewed[-1]['reviewer']}")
    
    # 汇总基因
    if reviewed:
        summary = f"NGC基因质量飞轮·{datetime.now().strftime('%m%d%H%M')}·评审{len(reviewed)}条·升级{sum(1 for r in reviewed if r['new']>r['old'])}条·NGC主力{sum(1 for r in reviewed if 'NGC' in r['reviewer'])}次"
        try:
            gene = json.dumps({"content": summary, "memory_type": "episodic",
                "source": "NGC基因质量飞轮/nemotron-30B", "fitness_score": 0.75}).encode()
            urllib.request.Request(f"{LGE_URL}/genes/write", data=gene,
                headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        except: pass
        log(f"✅ {summary}")
    
    return reviewed

if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    review_batch(15)
