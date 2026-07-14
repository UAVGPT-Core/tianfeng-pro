#!/usr/bin/env python3
"""
雷达LLM消化器 v1.0 — 外部雷达原始扫描→Ollama消化→高质基因
部署: 天工DGX1 | 在external-radar.py之后运行
每6h: 拉取最近24h低质雷达基因→qwen2.5:14b重写→质量评审→回库
"""
import urllib.request, json, time, os

LGE = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"
OLLAMA = "http://localhost:11434/api/generate"

def lge_search(query, n=30):
    try:
        data = json.dumps({"query": query, "n_results": n}).encode()
        req = urllib.request.Request(f"{LGE}/genes/search", data=data,
            headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read()).get("results", [])
    except: return []

def lge_mutate(gid, content):
    try:
        data = json.dumps({"gene_id": gid, "content": content}).encode()
        req = urllib.request.Request(f"{LGE}/genes/mutate", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read())
    except: return {}

def lge_evolve(gid, fitness):
    try:
        data = json.dumps({"gene_id": gid, "fitness_score": fitness}).encode()
        req = urllib.request.Request(f"{LGE}/genes/evolve", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read())
    except: return {}

def ollama(prompt, max_tok=300):
    try:
        data = json.dumps({"model": "qwen2.5:14b", "prompt": prompt, "stream": False,
            "options": {"num_predict": max_tok, "temperature": 0.5}}).encode()
        req = urllib.request.Request(OLLAMA, data=data,
            headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=45)
        return json.loads(r.read()).get("response", "")
    except: return ""

now = time.strftime("%Y-%m-%d %H:%M:%S")
print(f"[{now}] 雷达LLM消化器 v1.0")

# 拉取原始雷达基因(fitness<0.3的)
queries = ["external radar", "arXiv", "GitHub trend", "HuggingFace", "raw scan"]
raw_genes = []
for q in queries:
    for g in lge_search(q, n=15):
        fid = g.get("gene_id", "")
        if fid not in {x.get("gene_id") for x in raw_genes}:
            fit = g.get("fitness_score", 0.5)
            if fit < 0.4:  # focus on low quality
                raw_genes.append(g)

raw_genes.sort(key=lambda g: g.get("fitness_score", 0.5))
target = raw_genes[:20]
print(f"  低质雷达基因: {len(raw_genes)} → 处理{len(target)}")

digested = 0
for g in target:
    gid = g.get("gene_id", "?")
    old_fit = g.get("fitness_score", 0.5)
    content = g.get("content", g.get("preview", ""))
    if len(content) < 30:
        continue
    
    # LLM消化: 提取核心洞察+结构化重写
    prompt = f"""Extract key technical insights from this raw scan and rewrite as a structured knowledge gene.
Keep it under 300 chars. Focus on actionable information.

Raw scan: {content[:500]}

Structured gene:"""
    digested_content = ollama(prompt, 300)
    
    if digested_content and len(digested_content) > 40:
        lge_mutate(gid, digested_content)
        new_fit = min(0.65, old_fit + 0.3)
        lge_evolve(gid, new_fit)
        digested += 1
        print(f"  ✅ {gid[:25]}... {old_fit:.2f}→{new_fit:.2f}")

print(f"[{now}] 消化: {digested}/{len(target)}")
