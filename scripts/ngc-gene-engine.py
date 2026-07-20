#!/usr/bin/env python3
"""
NGC高质高产基因引擎 v1.0 — 5万/天计划
NGC免费API·多模型并行·地枢本地LGE直写
目标: 200条/次·每10min = 28,800/天(单节点)
扩展: 地枢+天工+灵龙 = 86,400+/天
"""
import urllib.request, json, time, hashlib, re, os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

NGC_KEY = "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"
NGC_API = "https://integrate.api.nvidia.com/v1/chat/completions"
LGE_URL = "http://localhost:8200"
LGE_KEY = "lgox-gene-key-2025"

# 三模型分层
GEN_MODEL = "meta/llama-3.1-8b-instruct"     # 快速生成·100条/批
DEEP_MODEL = "nvidia/nemotron-3-nano-30b-a3b" # 质量评审
FAST_MODEL = "meta/llama-3.1-8b-instruct"     # 评分

CONCURRENCY = 8      # NGC支持高并发
TARGET = 200         # 每批目标
GENE_MAX = 500

DOMAINS = {
    "ai-agent": {"name": "AI Agent", "w": 25, "topics": [
        "多智能体协作协议设计","Agent长期记忆与RAG架构","MCP工具调用安全模型",
        "自主Agent决策验证机制","Agent自我进化触发条件","联邦学习Agent知识共享",
        "人机协作信任建立","Agent可解释性与审计","工具编排错误恢复",
        "多模型路由成本优化"
    ]},
    "uav": {"name": "无人机低空", "w": 20, "topics": [
        "自主巡检路径规划","AI机巢调度与能源管理","GPS拒止视觉SLAM",
        "集群协同编队控制","低空经济空域法规","5G+边缘AI实时图传",
        "桥梁裂缝深度学习检测","多光谱传感器融合","无人机BMS续航优化",
        "对抗天气飞行稳定性"
    ]},
    "edge": {"name": "边缘计算", "w": 15, "topics": [
        "模型量化与剪枝","WASM浏览器AI推理","KV缓存优化",
        "边缘联邦学习通信效率","移动端GPU推理对比","模型蒸馏边缘部署",
        "ONNX运行时硬件加速","边缘AI能耗热控制","TinyML物联网传感器",
        "边缘云协同推理架构"
    ]},
    "fed": {"name": "联邦架构", "w": 15, "topics": [
        "P2P知识同步冲突合并","节点自愈协议心跳","基因引擎五原语版本控制",
        "Docker特权系统管理","联邦桥消息持久化去重","多节点共识算法",
        "联邦拓扑动态发现","零信任AI联邦","仪表盘实时数据聚合",
        "DNA双螺旋基因同步"
    ]},
    "mlops": {"name": "MLOps", "w": 15, "topics": [
        "LoRA微调内存优化","RLHF人类反馈质量评估","分布式训练通信拓扑",
        "模型版本管理回滚","A/B测试模型部署","ML流水线自动化测试",
        "GPU集群任务调度","模型监控漂移检测","向量数据库索引优化",
        "特征工程管道自动化"
    ]},
    "security": {"name": "AI安全", "w": 10, "topics": [
        "LLM越狱攻击防御","训练数据投毒检测","模型水印知识产权",
        "AI生成内容溯源认证","联邦节点零信任控制","敏感数据联邦脱敏",
        "AI供应链安全审计","推理侧信道防御","GDPR训练合规",
        "模型逆向工程风险"
    ]},
}

def ngc_chat(messages, model=GEN_MODEL, max_tokens=300, temp=0.7):
    data = json.dumps({"model": model, "messages": messages,
        "max_tokens": max_tokens, "temperature": temp}).encode()
    req = urllib.request.Request(NGC_API, data=data, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {NGC_KEY}"})
    r = urllib.request.urlopen(req, timeout=25)
    return json.loads(r.read())["choices"][0]["message"]["content"]

def log(msg):
    print(f"[{datetime.now().strftime('%m%d-%H%M%S')}] {msg}")

def produce_one(domain_key, topic):
    d = DOMAINS[domain_key]
    prompt = f"Generate a high-quality technical knowledge entry (150-300 chars). Domain: {d['name']}. Topic: {topic}. Be specific, data-driven, actionable. Pure technical knowledge, verifiable."
    try:
        content = ngc_chat([{"role": "user", "content": prompt}], GEN_MODEL, 350)
        if len(content) > 40:
            return {"content": content[:GENE_MAX], "domain": d["name"], "topic": topic}
    except:
        pass
    return None

def quality_score(content):
    prompt = f"Rate this technical knowledge 0.0-1.0. Reply ONLY number.\n{content[:300]}\nScore:"
    try:
        text = ngc_chat([{"role": "user", "content": prompt}], FAST_MODEL, 5, 0.1)
        nums = re.findall(r'[\d.]+', text)
        return min(0.95, max(0.05, float(nums[0]))) if nums else 0.50
    except:
        return 0.50

def lge_write(content, fitness):
    try:
        data = json.dumps({"content": content, "memory_type": "semantic",
            "source": "NGC引擎", "fitness": fitness}).encode()
        req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        urllib.request.urlopen(req, timeout=10)
        return True
    except:
        return False

def main():
    log(f"═══ NGC高质高产引擎 v1.0 ═══")
    log(f"目标:{TARGET}条·{CONCURRENCY}并发")
    
    # 构建任务队列
    tasks = []
    total_w = sum(d["w"] for d in DOMAINS.values())
    for dk, dc in DOMAINS.items():
        count = max(1, int(TARGET * dc["w"] / total_w))
        for i in range(count):
            tasks.append((dk, dc["topics"][i % len(dc["topics"])]))
    
    # 并发生产
    produced = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = {ex.submit(produce_one, dk, t): (dk, t) for dk, t in tasks[:TARGET]}
        for f in as_completed(futures):
            r = f.result()
            if r: produced.append(r)
    
    log(f"  生产:{len(produced)}/{len(tasks)}条·{100*len(produced)//max(1,len(tasks))}%")
    
    # 质量评审+写入
    written = 0
    for g in produced[:200]:
        score = quality_score(g["content"])
        if score >= 0.35:
            if lge_write(g["content"], score):
                written += 1
    
    log(f"  ✅ 写入LGE:{written}条")
    
    # 心跳基因
    lge_write(f"[NGC引擎·心跳·{datetime.now().strftime('%m%d-%H%M')}] 地枢·{written}条·NGC", 0.6)

if __name__ == "__main__":
    main()
