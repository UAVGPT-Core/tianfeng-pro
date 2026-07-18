#!/usr/bin/env python3
"""
地枢基因生产线 v2.0 — 天工Ollama·单模型·降并发
模型: qwen2.5-coder:7b (天工DGX1)
修复: 72B/32B/14B → 统一7B·降并发·加sleep
"""
import urllib.request, json, time

LGE = "http://localhost:8200"
LGE_KEY = "lgox-gene-key-2025"
OLLAMA = "http://192.168.30.12:11434"
MODEL = "qwen2.5-coder:7b"

def ollama_gen(prompt, max_tokens=300):
    data = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.7}}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=data,
        headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=90)
    return json.loads(r.read()).get("response", "")

def lge_write(content, gene_type="semantic", source="地枢基因线", fitness=0.6):
    data = json.dumps({"content": content, "memory_type": gene_type,
        "source": source, "fitness": fitness}).encode()
    req = urllib.request.Request(f"{LGE}/genes/write", data=data,
        headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
    r = urllib.request.urlopen(req, timeout=10)
    return json.loads(r.read())

def quality_score(content, topic):
    prompt = f"Rate this gene quality (0.0-1.0). Reply ONLY the number.\nTopic: {topic}\nContent: {content[:300]}\nScore:"
    try:
        text = ollama_gen(prompt, 3)
        return float(text.strip().split()[0])
    except:
        return 0.55

now = time.strftime("%Y-%m-%d %H:%M:%S")
print(f"[{now}] 地枢基因生产线 v2.0 启动")

topics = [
    "LGOX联邦基因进化策略优化",
    "分布式AI节点知识同步最佳实践",
    "基因fitness评分算法改进方案",
    "低空经济无人机巡检技术趋势",
    "AI Agent自主进化机制设计模式",
    "联邦学习中的知识蒸馏压缩方法",
    "GPU推理优化与模型量化实践",
    "多模型ensemble质量评审架构",
]

produced = 0
for i, topic in enumerate(topics):
    time.sleep(3)  # 避免打爆天工Ollama
    try:
        prompt = f"Generate a high-quality knowledge gene about: {topic}\nBe specific, actionable, and data-driven. Include key insights.\nFormat: concise technical summary under 300 chars."
        draft = ollama_gen(prompt, 300)
        if not draft or len(draft) < 30:
            print(f"  ⚠️ {topic[:40]}... 生成过短")
            continue

        score = quality_score(draft, topic)
        result = lge_write(draft, "semantic", "地枢基因线", min(score, 0.9))
        gid = result.get("gene_id", "?")
        produced += 1
        print(f"  ✅ {gid[:30]}... fit={score:.2f} | {topic[:40]}")
    except Exception as e:
        print(f"  ❌ {topic[:30]}... {str(e)[:80]}")

print(f"[{now}] 完成: {produced}条基因")
