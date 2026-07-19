#!/usr/bin/env python3
"""
天怿超个体化 v1.0 — WSL2轻量基因节点
六合飞轮: 通→处→执→馈→审→基因
部署: 天怿 WSL2@Win10 · 低资源·智谱免费API
触发: 天枢watchdog检测上线→自动scp+ssh执行
"""
import urllib.request, json, time, os, sys
from datetime import datetime

NODE = "天怿"
NODE_ID = "tianyi-wsl2"
LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"

# 智谱GLM-4-Flash 免费
GLM_KEY = "fd867a96bad64f53a8ece13ac6911887.T3zYiYf7KbxhVTb0"
GLM_API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def glm_chat(messages, max_tokens=300):
    data = json.dumps({"model": "glm-4-flash", "messages": messages, "max_tokens": max_tokens, "temperature": 0.7}).encode()
    req = urllib.request.Request(GLM_API, data=data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {GLM_KEY}"})
    r = urllib.request.urlopen(req, timeout=30)
    return json.loads(r.read())["choices"][0]["message"]["content"]

def lge_write(content, fitness=0.5):
    data = json.dumps({"content": content, "memory_type": "semantic", "source": NODE, "fitness": fitness}).encode()
    req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data, headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
    urllib.request.urlopen(req, timeout=10)
    return True

# 轻量专题(5条/次·低资源)
topics = [
    ("WSL2部署优化", "WSL2上AI开发环境的最佳配置与性能调优"),
    ("Windows+Linux混合AI", "Windows宿主机与WSL2 Linux虚拟机协同AI推理的架构设计"),
    ("低资源基因生产", "在4GB内存设备上运行AI基因生产的最小化方案"),
    ("边缘节点自治", "间歇性在线节点的知识同步与离线缓存策略"),
    ("学习型AI节点", "AI节点从被动执行到主动学习进化的自驱机制"),
]

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    produced = 0
    
    for domain, topic in topics:
        try:
            prompt = f"生成一条技术知识(100-200字)。领域:{domain}。主题:{topic}。纯技术·可验证·简洁。"
            draft = glm_chat([{"role": "user", "content": prompt}], 250)
            if draft and len(draft) > 40:
                lge_write(f"[{NODE}] {domain}: {draft[:500]}", 0.6)
                produced += 1
                print(f"  ✅ {domain}")
            time.sleep(2)
        except Exception as e:
            print(f"  ❌ {domain}: {str(e)[:60]}")
    
    # 心跳基因
    heartbeat = f"[{NODE}·超个体心跳·{now}] 在线·WSL2@Win10·轻量基因节点·{produced}条产出"
    lge_write(heartbeat, 0.5)
    
    print(f"[{now}] {NODE} 完成: {produced}条基因")
    return produced

if __name__ == "__main__":
    main()
