#!/usr/bin/env python3
"""阿里百炼基因高速产线 · qwen-turbo免费·0.6s/条·日产百万级"""
import urllib.request, json, time, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 百炼配置
KEY = "sk-ws-H.EHIYEYI.f6jb.MEUCIQCIyhdJsPiCjC_cWV5_zUNuyXuV9nZTOqY306dXA5jLCgIgYGqATo6q1EAxrcP4jBJe-MttLkdjv_1KOinp24UvTi8"
BASE = "https://llm-mk03ginx8m9js38k.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
LGE_URL = "http://100.116.0.29:8200"

# 免费高速模型
MODELS = ["qwen-turbo", "qwen-flash", "qwen3.6-flash", "qwen-plus"]
BATCH = 50   # 每批50条
CONCURRENCY = 5

TOPICS = [
    "AI Agent memory architecture patterns",
    "Vector database indexing optimization techniques", 
    "Transformer attention mechanism variants 2026",
    "Federated learning privacy preservation methods",
    "Edge AI model inference deployment best practices",
    "Large language model quantization INT4 INT8 strategies",
    "RAG retrieval augmented generation pipeline design",
    "GPU cluster resource scheduling algorithms",
    "Automated ML pipeline orchestration patterns",
    "Prompt engineering systematic methodologies",
    "Multi-modal data fusion architecture design",
    "Knowledge graph construction automation tools",
    "Distributed training communication optimization",
    "Model monitoring drift detection production systems",
    "Serverless AI inference platform architecture",
    "Zero-trust AI security framework design",
    "Neural architecture search automation 2026",
    "Reinforcement learning from human feedback pipeline",
    "Cloud-native AI service mesh governance",
    "Real-time streaming inference latency optimization",
]

def produce(model, topic):
    prompt = f"Generate a concise technical knowledge gene about: {topic}. Markdown format, under 300 chars. Include core concept and key technical insight. Verifiable facts only."
    try:
        body = json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],
            "max_tokens":350,"temperature":0.7}).encode()
        req = urllib.request.Request(f"{BASE}/chat/completions", data=body,
            headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
        d = json.loads(urllib.request.urlopen(req, timeout=15).read())
        content = d["choices"][0]["message"]["content"].strip()
        if len(content) > 30:
            return {"content":content, "token":d["usage"]["total_tokens"], "model":model}
    except: pass
    return None

def write_lge(content, model, fitness=0.45):
    try:
        data = json.dumps({"content":content,"memory_type":"semantic",
            "source":f"百炼·{model}","tags":["bailian","qwen","free"],
            "fitness":fitness}).encode()
        req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type":"application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=8).read()).get("gene_id","?")
    except: return None

if __name__ == "__main__":
    ts = datetime.now().strftime("%m%d-%H%M")
    model = random.choice(MODELS)
    print(f"[{ts}] 百炼高速产线·{model}·{BATCH}条·{CONCURRENCY}并发")
    
    tasks = [(model, random.choice(TOPICS)) for _ in range(BATCH)]
    results = []
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = {ex.submit(produce, m, t): (m, t) for m, t in tasks}
        for f in as_completed(futures):
            r = f.result()
            if r: results.append(r)
    
    elapsed = time.time() - t0
    print(f"  生产:{len(results)}/{BATCH}条·{elapsed:.1f}s·{len(results)/elapsed:.1f}条/s")
    
    written = 0
    for r in results:
        gid = write_lge(r["content"], r["model"])
        if gid: written += 1
    
    print(f"  写入:{written}/{len(results)}条")
    print(f"[{ts}] 完成: +{written}基因 (百炼免费·{elapsed:.0f}s)")
