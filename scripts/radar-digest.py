#!/usr/bin/env python3
"""
雷达消化引擎 v1.0 — 从"发现"到"行动"
扫描最新雷达基因 → DeepSeek分析 → 输出:这个发现改变了什么
"""
import json, subprocess, urllib.request, os, time

LGE = "http://100.116.0.29:8200"
DS_API = "https://api.deepseek.com/v1/chat/completions"
DS_KEY = subprocess.run(["grep", "DEEPSEEK.*KEY", os.path.expanduser("~/ai-gateway/.env")], 
    capture_output=True, text=True).stdout.strip()
if DS_KEY:
    DS_KEY = DS_KEY.split("=")[1].strip()

def get_radar_genes(limit=10):
    """获取最新雷达基因"""
    try:
        req = urllib.request.Request(f"{LGE}/genes/search",
            data=json.dumps({"query": "雷达 竞对 知乎 AI趋势 无人机", "n_results": limit}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        return json.loads(urllib.request.urlopen(req, timeout=5).read()).get("results", [])
    except: return []

def digest_with_ai(gene_content):
    """AI消化:这个发现对LGOX意味着什么"""
    if not DS_KEY: return "API不可用"
    try:
        prompt = f"""你是LGOX联邦的战略分析师。分析以下外部发现对LGOX联邦的影响:

发现内容: {gene_content[:300]}

请用以下格式回答(每项一行,共3-5行):
🔮 影响: [对LGOX的具体影响]
⚡ 行动: [建议LGOX采取的行动,用✅/⚠️/🔴标注优先级]
📊 关联: [与LGOX现有能力的关联]
💡 机会: [可转化的商业或技术机会]

如果真的无关,就说"暂无直接影响"."""
        req = urllib.request.Request(DS_API,
            data=json.dumps({
                "model": "deepseek-v4-flash",
                "messages": [{"role": "system", "content": "你是LGOX联邦战略分析师。准确、简练、可执行。"},
                            {"role": "user", "content": prompt}],
                "temperature": 0.7, "max_tokens": 300
            }).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {DS_KEY}"},
            method="POST")
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        return f"消化失败:{e}"

def write_digested(original, digestion, score):
    """写入消化后的基因"""
    try:
        data = {
            "content": f"[雷达消化] 原文:{original[:200]}\n\n{digestion}",
            "memory_type": "semantic",
            "source": "雷达消化引擎",
            "fitness": min(0.9, score/10),
            "tags": ["雷达消化", "行动指南"]
        }
        req = urllib.request.Request(f"{LGE}/genes/write",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        return json.loads(urllib.request.urlopen(req, timeout=5).read()).get("gene_id")
    except: return None

# ═══ 主流程 ═══
print(f"🧠 雷达消化引擎 v1.0")
genes = get_radar_genes(10)
print(f"  最新雷达: {len(genes)}条")

digested = 0
for g in genes[:5]:  # 消化前5条
    content = g.get("content", "")
    gene_id = g.get("gene_id", "")[:12]
    try:
        digestion = digest_with_ai(content)
        if digestion and "失败" not in digestion and "暂无" not in digestion:
            gid = write_digested(content, digestion, score=13)
            if gid:
                digested += 1
                print(f"  ✅ {gene_id} → 已消化")
            time.sleep(1)  # API限速
    except Exception as e:
        print(f"  ⚠️ {gene_id}: {e}")

print(f"\n  消化完成: {digested}/{len(genes)}条")
print(f"  输出: 每条雷达→影响+行动+机会")
