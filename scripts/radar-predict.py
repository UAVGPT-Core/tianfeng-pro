#!/usr/bin/env python3
"""
雷达预测引擎 v1.0 · 从"今天"到"6个月后"
分析30天雷达基因趋势 → DeepSeek预测 → 输出6个月前瞻
"""
import json, subprocess, urllib.request, os, time
from collections import Counter

LGE = "http://100.116.0.29:8200"
DS_API = "http://localhost:18666/v1/chat/completions"
DS_KEY = ""
try:
    with open(os.path.expanduser("~/ai-gateway/.env")) as f:
        for line in f:
            if "DEEPSEEK" in line and "KEY" in line:
                DS_KEY = line.split("=")[1].strip()
except: pass

def get_radar_trends(days=30, limit=50):
    """获取雷达基因趋势"""
    keywords = ["雷达", "竞对", "知乎", "AI趋势", "LLM", "Agent", "无人机", "大模型"]
    all_genes = []
    for kw in keywords:
        try:
            req = urllib.request.Request(f"{LGE}/genes/search",
                data=json.dumps({"query": kw, "n_results": 10}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            genes = json.loads(urllib.request.urlopen(req, timeout=5).read()).get("results", [])
            all_genes.extend(genes)
        except: pass
    
    # 去重取前50
    seen = set()
    unique = []
    for g in all_genes:
        cid = g.get("content", "")[:50]
        if cid not in seen:
            seen.add(cid)
            unique.append(g)
        if len(unique) >= limit: break
    return unique

def predict_six_months(trend_data):
    """AI预测6个月趋势"""
    if not DS_KEY: return "DS API不可用"
    
    # 提取关键词频次
    all_text = " ".join([g.get("content", "")[:200] for g in trend_data])
    words = all_text.split()
    top_terms = Counter([w for w in words if len(w) > 2 and w.isascii() == False]).most_common(15)
    trend_summary = " | ".join([f"{t[0]}({t[1]})" for t in top_terms[:10]])
    
    prompt = f"""你是LGOX联邦的未来学分析师。基于以下30天雷达趋势数据，预测6个月后(2027年1月)会发生什么:

趋势关键词: {trend_summary}

样本内容(前5条):
{chr(10).join([g.get('content','')[:150] for g in trend_data[:5]])}

请预测:

🔮 6个月后·关键技术趋势:
  [3条最重要趋势·每条20字内·标注概率%]
  
⚡ 6个月后·对LGOX的挑战:
  [最大的3个威胁·每个15字内]

💡 6个月后·LGOX的机会窗口:
  [最大的3个机会·每个20字内·含建议行动]

🎯 LGOX现在就该做的事:
  [Top 1:最重要的一个行动]

格式简洁·不冗余·可执行。"""
    
    try:
        req = urllib.request.Request(DS_API,
            data=json.dumps({
                "model": "deepseek-v4-flash",
                "messages": [{"role": "system", "content": "你是LGOX联邦未来学分析师。精确、前瞻、可执行。"},
                            {"role": "user", "content": prompt}],
                "temperature": 0.8, "max_tokens": 500
            }).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {DS_KEY}"},
            method="POST")
        resp = json.loads(urllib.request.urlopen(req, timeout=20).read())
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        return f"预测失败:{e}"

def write_prediction(prediction):
    """写入预测基因"""
    try:
        data = {
            "content": f"[6个月预测·{time.strftime('%Y-%m')}] {prediction}",
            "memory_type": "semantic",
            "source": "预测引擎",
            "fitness": 0.85,
            "tags": ["6个月预测", "未来学", "战略"]
        }
        req = urllib.request.Request(f"{LGE}/genes/write",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
        return resp.get("gene_id")
    except: return None

# ═══ 主流程 ═══
print(f"🔮 雷达预测引擎 v1.0")
print(f"   时间旅行: 今天→6个月后(2027-01)")

trends = get_radar_trends(30, 40)
print(f"   30天趋势: {len(trends)}条基因")

if trends and DS_KEY:
    prediction = predict_six_months(trends)
    if prediction and "失败" not in prediction:
        gid = write_prediction(prediction)
        if gid:
            print(f"   预测基因: {gid[:16]}")
        print(f"\n{prediction}")
    else:
        print(f"   预测: {prediction}")
else:
    print(f"   ⚠️ 数据不足或API不可用")
