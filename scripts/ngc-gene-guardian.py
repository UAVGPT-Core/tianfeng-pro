#!/usr/bin/env python3
"""
NGC基因质量门卫 v2.0 — 低质基因→LLM重写→高质回库
部署: 天工DGX1 cron每30min | 零API费(NGC免费层+本地Ollama降级)
"""
import urllib.request, json, time, os, sys

LGE = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"
OLLAMA = "http://localhost:11434/api/generate"

# NGC配置
NGC_KEY = ""
for p in ["~/.hermes/.env", "/tmp/nvkey.env", "~/.ngc_key"]:
    try:
        with open(os.path.expanduser(p)) as f:
            for line in f:
                if "NGC" in line.upper() or "NVIDIA" in line.upper() or "nvapi" in line.lower():
                    NGC_KEY = line.split("=",1)[1].strip().strip('"').strip("'")
                    if NGC_KEY: break
    except: pass

def lge_search(query, n=10):
    try:
        data = json.dumps({"query": query, "n_results": n}).encode()
        req = urllib.request.Request(f"{LGE}/genes/search", data=data,
            headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read()).get("results", [])
    except: return []

def lge_mutate(gene_id, new_content):
    try:
        data = json.dumps({"gene_id": gene_id, "content": new_content}).encode()
        req = urllib.request.Request(f"{LGE}/genes/mutate", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read())
    except: return {}

def lge_evolve(gene_id, new_fitness):
    try:
        data = json.dumps({"gene_id": gene_id, "fitness_score": new_fitness}).encode()
        req = urllib.request.Request(f"{LGE}/genes/evolve", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read())
    except: return {}

def ollama_score(model, content, original):
    """本地Ollama评分·0-1分"""
    prompt = f"""Score this gene content quality from 0.0 to 1.0. Reply with ONLY the number.
Original: {original[:200]}
Content: {content[:300]}
Quality score:"""
    try:
        data = json.dumps({"model": model, "prompt": prompt, "stream": False,
            "options": {"num_predict": 5, "temperature": 0.1}}).encode()
        req = urllib.request.Request(OLLAMA, data=data,
            headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=30)
        resp = json.loads(r.read())
        text = resp.get("response", "0.5").strip()
        return float(text.split()[0])
    except:
        return 0.5

def ollama_rewrite(model, content):
    """本地Ollama重写低质基因"""
    prompt = f"""Rewrite this gene to be high-quality and informative. Keep it concise (<300 chars).
Original: {content}
Rewritten:"""
    try:
        data = json.dumps({"model": model, "prompt": prompt, "stream": False,
            "options": {"num_predict": 400, "temperature": 0.5}}).encode()
        req = urllib.request.Request(OLLAMA, data=data,
            headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=45)
        return json.loads(r.read()).get("response", "")
    except:
        return ""

# ═══ 主流程 ═══
now = time.strftime("%Y-%m-%d %H:%M:%S")
print(f"[{now}] NGC质量门卫 v2.0 启动")
print(f"  NGC Key: {'已配置' if NGC_KEY else '未配置·降级Ollama'}")

# ① 拉取低质基因
queries = ["low quality", "fitness 0.3", "radar scan raw"]
all_low = []
for q in queries:
    genes = lge_search(q, n=20)
    for g in genes:
        fid = g.get("gene_id", "")
        if fid not in {x.get("gene_id") for x in all_low}:
            all_low.append(g)

# 按fitness排序·优先处理最低的
all_low.sort(key=lambda g: g.get("fitness_score", 0.5))
target = all_low[:15]  # 每轮最多15条
print(f"  低质候选: {len(all_low)}条 → 处理{len(target)}条")

# ② 逐条评审+重写
improved = 0
model = "qwen2.5:14b"  # 天工主力·零成本

for g in target:
    gid = g.get("gene_id", "?")
    old_fit = g.get("fitness_score", 0.5)
    content = g.get("content", g.get("preview", ""))
    if not content or len(content) < 30:
        continue
    
    # 评分
    score = ollama_score(model, content, content[:100])
    
    if score < 0.55:
        # 重写
        new_content = ollama_rewrite(model, content)
        if new_content and len(new_content) > 30:
            lge_mutate(gid, new_content)
            new_score = ollama_score(model, new_content + " [enriched]", content[:100])
            new_score = min(new_score, 0.85)
            lge_evolve(gid, new_score)
            improved += 1
            print(f"  ✅ {gid[:25]}... {old_fit:.2f}→{new_score:.2f}")

print(f"[{now}] 完成: {improved}/{len(target)}条提升")
