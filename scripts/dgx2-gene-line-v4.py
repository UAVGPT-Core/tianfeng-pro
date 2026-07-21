#!/usr/bin/env python3
"""地枢NGC基因生产线 v4.0 · NGC免费API·日产万级"""
import urllib.request, json, time, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

NGC_KEY = "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"
NGC_API = "https://integrate.api.nvidia.com/v1/chat/completions"
NGC_MODEL = "meta/llama-3.1-8b-instruct"
LGE_URL = "http://127.0.0.1:8200"
LGE_KEY = "lgox-gene-key-2025"
BATCH = 30
CONCURRENCY = 2  # NGC免费API限流·保守2并发

DOMAINS = {
    "ai_arch":    "AI系统架构与设计模式",
    "ml_ops":     "MLOps与模型部署",
    "data_eng":   "数据工程与管道",
    "infra":      "云原生基础设施",
    "security":   "AI安全与对齐",
    "frontier":   "前沿AI研究进展",
}

TOPICS = {
    "ai_arch":  ["Transformer变体架构","MoE混合专家模型","Agent记忆系统","多模态融合架构","RAG检索增强","Agent工具调用","模型路由策略","推理优化管线"],
    "ml_ops":   ["模型版本管理","A/B测试框架","模型监控告警","自动化CI/CD","特征存储设计","模型压缩量化","在线学习系统","边缘部署优化"],
    "data_eng": ["流式数据处理","数据质量治理","特征工程自动化","实时ETL管道","图数据库优化","时序数据存储","向量索引构建","数据湖架构"],
    "infra":    ["K8s GPU调度","分布式训练网络","Serverless推理","多云负载均衡","存储缓存策略","容器安全加固","可观测性体系","自动扩缩容"],
    "security": ["模型安全审计","对抗样本防御","差分隐私训练","联邦学习安全","提示注入防护","数据脱敏技术","模型水印保护","安全RLHF对齐"],
    "frontier": ["量子机器学习","神经符号AI","具身智能控制","AI for Science","自监督新范式","长上下文突破","多Agent协作","世界模型构建"],
}

def gen_gene(domain, topic):
    prompt = f"""You are an AI knowledge engineer. Generate a high-quality technical knowledge gene about: {topic} (domain: {DOMAINS[domain]}).
Output in Markdown format. Include: core concept (1 sentence), key technical details (2-3 sentences), and practical application notes (1 sentence).
Keep under 350 chars. Pure technical knowledge. No stories. Verifiable facts."""
    try:
        body = json.dumps({"model":NGC_MODEL,"messages":[{"role":"user","content":prompt}],
            "max_tokens":400,"temperature":0.7}).encode()
        req = urllib.request.Request(NGC_API, data=body,
            headers={"Authorization":"Bearer "+NGC_KEY,"Content-Type":"application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=25).read())
        return d["choices"][0]["message"]["content"].strip()
    except: return None

def write_lge(content, domain):
    try:
        data = json.dumps({"content":content,"memory_type":"semantic","source":"地枢NGCv4",
            "tags":[domain,"ngc","dgx2"],"fitness":0.45}).encode()
        req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type":"application/json","X-LGE-Key":LGE_KEY})
        return json.loads(urllib.request.urlopen(req, timeout=10).read()).get("gene_id","?")
    except: return None

if __name__ == "__main__":
    ts = datetime.now().strftime("%m%d-%H%M")
    print(f"[{ts}] 地枢NGC基因线 v4.0 · {BATCH}条·{CONCURRENCY}并发")
    
    # 生成任务
    tasks = []
    for domain in DOMAINS:
        for topic in random.sample(TOPICS[domain], min(5, len(TOPICS[domain]))):
            tasks.append((domain, topic))
    tasks = random.sample(tasks, min(BATCH, len(tasks)))
    
    genes = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = {ex.submit(gen_gene, d, t): (d, t) for d, t in tasks}
        for f in as_completed(futures):
            result = f.result()
            if result and len(result) > 40:
                genes.append((futures[f][0], result))
    
    print(f"  生产:{len(genes)}/{len(tasks)}条·{100*len(genes)//max(1,len(tasks))}%")
    
    # 写入LGE
    ok = 0
    for domain, content in genes:
        gid = write_lge(content, domain)
        if gid: ok += 1
        time.sleep(0.3)
    
    print(f"  写入:{ok}/{len(genes)}条")
    print(f"[{ts}] 完成: +{ok}基因 (NGC免费)")
