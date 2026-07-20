#!/usr/bin/env python3
"""
GPU基因富化引擎 v2.0 — 天工Ollama本地·深加工NGC基因
模型: lgox-distill-v1 (9GB, 14.8B) 或 lgox-evolved-* (4.7GB)
流程: LGE拉取低fitness基因→Ollama重写→质量复审→写回LGE
"""
import urllib.request, json, time, re, os
from datetime import datetime

LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"
OLLAMA = "http://localhost:11434"
MODEL = "lgox-distill-v1:latest"  # 蒸馏模型·9GB·14.8B
BATCH = 20

def ollama_gen(prompt, max_tokens=300, temp=0.7):
    data = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": temp}}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=data,
        headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=60)
    return json.loads(r.read()).get("response", "")

def lge_write(content, fitness):
    try:
        data = json.dumps({"content": content, "memory_type": "semantic",
            "source": "GPU富化引擎", "fitness": fitness}).encode()
        req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        urllib.request.urlopen(req, timeout=10)
        return True
    except: return False

def fetch_low_fitness(limit=50):
    """拉取fitness<0.5的低质基因"""
    try:
        req = urllib.request.Request(f"{LGE_URL}/genes/search", method="POST",
            data=json.dumps({"query": "fitness low quality", "n_results": limit}).encode(),
            headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read()).get("results", [])
    except:
        return []

def enrich_gene(gene):
    """Ollama蒸馏模型深度重写"""
    content = gene.get("content", "")[:500]
    gid = gene.get("gene_id", "?")[:20]
    prompt = f"""You are a senior AI knowledge engineer. Rewrite and improve this knowledge entry. Make it more technical, specific, and actionable. Add concrete data, metrics, or code examples if applicable. Keep under 400 chars.

Original: {content}

Improved version:"""
    try:
        improved = ollama_gen(prompt, 400, 0.6)
        if len(improved) > 60:
            score = quality_score(improved)
            return improved, score, gid
    except: pass
    return None, 0, gid

def quality_score(content):
    prompt = f"Rate this technical knowledge 0.0-1.0. Reply ONLY number.\n{content[:300]}\nScore:"
    try:
        text = ollama_gen(prompt, 3, 0.1)
        nums = re.findall(r'[\d.]+', text)
        return min(0.95, max(0.1, float(nums[0]))) if nums else 0.45
    except: return 0.45

def main():
    now = datetime.now().strftime("%m%d-%H%M%S")
    print(f"[{now}] GPU富化引擎 v2.0 启动 (模型:{MODEL})")
    
    genes = fetch_low_fitness(BATCH)
    if not genes:
        print("  无低质基因可富化")
        return
    
    print(f"  拉取{len(genes)}条低fitness基因")
    enriched = 0
    for i, gene in enumerate(genes[:20]):
        improved, score, gid = enrich_gene(gene)
        if improved and score > gene.get("fitness_score", 0):
            gene["content"] = improved
            gene["fitness_score"] = score
            lge_write(improved, score)
            enriched += 1
            print(f"  ✅ {gid} 0.{int(gene.get('fitness_score',0)*100)}→0.{int(score*100)}")
        time.sleep(1)
    
    print(f"[{now}] 富化完成: {enriched}条")
    lge_write(f"[GPU富化·{now}] 天工·{MODEL}·{enriched}条升级", 0.7)

if __name__ == "__main__":
    main()
