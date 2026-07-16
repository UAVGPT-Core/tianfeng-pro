#!/usr/bin/env python3
"""
混合基因增产引擎 v1.0 · 灵龙
七自: 自感知·自进化·自迭代
职能: 跨域基因杂交 → 产生新知识 → 混合型基因(hybrid)从1.2K→10K+
原理: 取两条不同域的基因 → LLM合成新洞察 → 写回LGE
cron: 每2小时·零成本
"""
import urllib.request, json, time, os, subprocess, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

LGE = "http://100.116.0.29:8200"
LOG = os.path.expanduser("~/lgox-ops/logs/hybrid-gene.log")
DOMAINS = ["AI", "无人机", "金融", "编程", "运维", "基因", "联邦", "进化"]
PAIRS_PER_RUN = 12

def log(msg):
    ts = datetime.now().strftime("%m%d-%H%M%S")
    print(f"[{ts}] {msg}")
    with open(LOG, "a") as f: f.write(f"[{ts}] {msg}\n")

def lge_post(path, data, timeout=10):
    try:
        req = urllib.request.Request(f"{LGE}{path}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except: return None

def fetch_gene(domain, n=3):
    r = lge_post("/genes/search", {"query": domain, "n_results": n})
    return r.get("results", []) if r else []

def hybrid_pair(gene_a, gene_b):
    """用本地Ollama合成两条基因"""
    content_a = gene_a.get("content", gene_a.get("preview", ""))[:300]
    content_b = gene_b.get("content", gene_b.get("preview", ""))[:300]

    prompt = f"""Synthesize a novel insight by combining these two knowledge domains:

Domain A: {content_a}
Domain B: {content_b}

Create ONE hybrid insight (<400 chars) that neither domain alone could produce.
Make it concrete with a specific example or application."""
    try:
        proc = subprocess.run(["ollama", "run", "qwen2.5:14b", prompt],
            capture_output=True, text=True, timeout=90)
        result = proc.stdout.strip()
        if result and len(result) > 40:
            return result[:500]
    except: pass
    return None

def main():
    log("═══ 混合基因增产引擎 ═══")

    # 随机选2个域
    d1, d2 = random.sample(DOMAINS, 2)
    log(f"杂交: {d1} × {d2}")

    genes_a = fetch_gene(d1, 5)
    genes_b = fetch_gene(d2, 5)
    if not genes_a or not genes_b:
        log(f"基因不足 A:{len(genes_a)} B:{len(genes_b)}·跳过")
        return

    created = 0
    for ga in genes_a[:4]:
        for gb in genes_b[:4]:
            hybrid = hybrid_pair(ga, gb)
            if hybrid:
                result = lge_post("/genes/write", {
                    "content": f"[{d1}×{d2}杂交] {hybrid}",
                    "memory_type": "hybrid",
                    "source": "hybrid-gene-engine",
                    "fitness_score": 0.55,
                    "parent_a": ga.get("gene_id",""),
                    "parent_b": gb.get("gene_id","")
                })
                if result:
                    created += 1

    log(f"杂交完成: {created}条新混合基因")
    import urllib.request as ur
    try:
        req = ur.Request(f"{LGE}/genes/stats")
        with ur.urlopen(req, timeout=8) as resp:
            stats_hint = json.loads(resp.read())
    except:
        stats_hint = None
    if isinstance(stats_hint, dict):
        log(f"LGE: {stats_hint.get('total','?'):,}·hybrid: +{created}")

if __name__ == "__main__":
    main()
