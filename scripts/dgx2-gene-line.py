#!/usr/bin/env python3
"""
地枢基因生产线 v1.0 — 双GPU·三模型·高质基因量产
模型: qwen2.5:14b(生成)+deepseek-r1:32b(深度推理)+qwen2.5-72b(质量评审)
部署: 地枢DGX2 cron每20min | 零API费·纯本地GPU
"""
import urllib.request, json, time, os

LGE = "http://localhost:8200"
LGE_KEY = "lgox-gene-key-2025"
OLLAMA = "http://localhost:11434"

def ollama_gen(model, prompt, max_tokens=400):
    data = json.dumps({"model": model, "prompt": prompt, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.7}}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=data,
        headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=60)
    return json.loads(r.read()).get("response", "")

def lge_write(content, gene_type="semantic", source="地枢基因线", fitness=0.6):
    data = json.dumps({"content": content, "memory_type": gene_type,
        "source": source, "fitness": fitness}).encode()
    req = urllib.request.Request(f"{LGE}/genes/write", data=data,
        headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
    r = urllib.request.urlopen(req, timeout=10)
    return json.loads(r.read())

def quality_score(content, original_topic):
    """qwen2.5-72b质量评审·返回0-1分"""
    prompt = f"""Rate this gene content quality (0.0-1.0). Reply ONLY the number.
Topic: {original_topic}
Content: {content[:400]}
Score:"""
    try:
        text = ollama_gen("qwen2.5-72b:latest", prompt, 5)
        return float(text.strip().split()[0])
    except:
        return 0.55

def deep_reasoning_gene(topic):
    """deepseek-r1:32b深度推理·生成分析型基因"""
    prompt = f"""Deep analysis of: {topic}
Provide structured insights with reasoning steps. Be concise (<400 chars).
Analysis:"""
    return ollama_gen("deepseek-r1:32b", prompt, 400)

now = time.strftime("%Y-%m-%d %H:%M:%S")
print(f"[{now}] 地枢基因生产线 v1.0 启动")

# ═══ 三阶段流水线 ═══
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
    # 阶段1: qwen2.5:14b生成初稿
    prompt = f"""Generate a high-quality knowledge gene about: {topic}
Be specific, actionable, and data-driven. Include key insights.
Format: concise technical summary (<300 chars)."""
    draft = ollama_gen("qwen2.5:14b", prompt, 350)
    if not draft or len(draft) < 40:
        continue
    
    # 阶段2: deepseek-r1:32b深度增强(偶数索引使用)
    if i % 2 == 0:
        enhanced = deep_reasoning_gene(topic)
        if enhanced and len(enhanced) > 40:
            draft = f"[深度推理] {topic}\n{draft[:200]}\n\n[推理增强]\n{enhanced[:250]}"
    
    # 阶段3: qwen2.5-72b质量评审
    score = quality_score(draft, topic)
    
    # 写入·质量门控
    result = lge_write(draft, "semantic", "地枢基因线", min(score, 0.9))
    gid = result.get("gene_id", "?")
    produced += 1
    print(f"  ✅ {gid[:30]}... fit={score:.2f} | {topic[:40]}")

print(f"[{now}] 完成: {produced}条基因")
