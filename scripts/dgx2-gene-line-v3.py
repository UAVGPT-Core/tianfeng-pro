#!/usr/bin/env python3
"""
地枢基因生产线 v3.0 — VOD Pro免费API·全天候·高质基因量产
模型: deepseek-v4-flash (VOD免费) · 替代天工Ollama
部署: 地枢DGX2 cron每10min | 零API费·VOD免费额度
修复: v2天工Ollama频繁503 → v3走VOD直连
"""
import urllib.request, json, time, os

LGE = "http://localhost:8200"
LGE_KEY = "lgox-gene-key-2025"

# VOD Pro 免费API
VOD_KEY = os.getenv("BAIDU_VOD_KEY", "")
if not VOD_KEY:
    try:
        with open(os.path.expanduser("~/.hermes/.env")) as f:
            for line in f:
                if line.startswith("BAIDU_VOD_KEY=") or line.startswith("BAIDU_VOD_API_KEY="):
                    VOD_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except:
        pass

VOD_URL = "https://vod.bj.baidubce.com/v3/chat/oc/v1/chat/completions"

def vod_chat(messages, max_tokens=300):
    """VOD Pro API调用·免费·1.2s延迟"""
    data = json.dumps({
        "model": "deepseek-v4-flash",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode()
    req = urllib.request.Request(VOD_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VOD_KEY}"
    })
    r = urllib.request.urlopen(req, timeout=30)
    return json.loads(r.read())["choices"][0]["message"]["content"]

def lge_write(content, gene_type="semantic", source="地枢基因线V3", fitness=0.6):
    data = json.dumps({"content": content, "memory_type": gene_type,
        "source": source, "fitness": fitness}).encode()
    req = urllib.request.Request(f"{LGE}/genes/write", data=data,
        headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
    r = urllib.request.urlopen(req, timeout=10)
    return json.loads(r.read())

def quality_score(content, topic):
    prompt = f"Rate this gene quality (0.0-1.0). Reply ONLY the number.\nTopic: {topic}\nContent: {content[:300]}\nScore:"
    try:
        text = vod_chat([{"role": "user", "content": prompt}], 3)
        return float(text.strip().split()[0])
    except:
        return 0.55

now = time.strftime("%Y-%m-%d %H:%M:%S")
print(f"[{now}] 地枢基因生产线 v3.0 启动 (VOD Pro)")

topics = [
    "LGOX联邦基因进化策略优化",
    "分布式AI节点知识同步最佳实践",
    "基因fitness评分算法改进方案",
    "低空经济无人机巡检技术趋势",
    "AI Agent自主进化机制设计模式",
    "联邦学习中的知识蒸馏压缩方法",
    "GPU推理优化与模型量化实践",
    "多模型ensemble质量评审架构",
    "联邦知识图谱构建与查询优化",
    "边缘AI模型压缩与部署最佳实践",
]

produced = 0
for i, topic in enumerate(topics):
    time.sleep(1)  # 温和间隔·VOD 20并发限制
    try:
        prompt = f"Generate a high-quality knowledge gene about: {topic}\nBe specific, actionable, and data-driven. Include key insights.\nFormat: concise technical summary under 300 chars."
        draft = vod_chat([{"role": "user", "content": prompt}], 300)
        if not draft or len(draft) < 30:
            print(f"  ⚠️ {topic[:40]}... 生成过短")
            continue

        score = quality_score(draft, topic)
        result = lge_write(draft, "semantic", "地枢基因线V3", min(score, 0.9))
        gid = result.get("gene_id", "?")
        produced += 1
        print(f"  ✅ {gid[:30]}... fit={score:.2f} | {topic[:40]}")
    except Exception as e:
        print(f"  ❌ {topic[:30]}... {str(e)[:80]}")

print(f"[{now}] 完成: {produced}条基因")
