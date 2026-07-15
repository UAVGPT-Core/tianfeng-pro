#!/usr/bin/env python3
"""
小枢↔天巡 互测飞轮 v1.0 · 24h永动·自动纳基因
每5min: 小枢问天巡→评分→天巡问小枢→评分→纳基因
"""
import urllib.request, json, time, random

XIAOSHU = "http://localhost:8779/chat/completions"
TIANXUN = "http://localhost:8778/chat/completions"
LGE = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"

QUESTIONS = [
    "LGOX联邦有几个节点？分别叫什么？",
    "金字塔现在是哪个版本？",
    "联邦的基因库现在有多少条基因？",
    "天工地枢之间用什么连接的？",
    "你多久自检一次？",
    "联邦的燃料路由有几层？",
    "当前有几个飞轮在运行？",
    "双200Gb直连的速度是多少？",
    "小枢和天巡分别是什么角色？",
    "联邦的核心架构是什么？",
    "无人机机巢如何部署AI Box？",
    "边缘计算在无人机巡检中如何应用？",
    "低空经济包含哪些产业链？",
    "200Gb直连对基因生产有什么提升？",
    "百度VOD DeepSeek比直连快多少？",
]

def chat(url, question):
    try:
        data = json.dumps({"messages":[{"role":"user","content":question}],"stream":False}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
        r = urllib.request.urlopen(req, timeout=20)
        d = json.loads(r.read())
        return d["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[错误:{e}]"

def score_answer(question, answer):
    """简单评分: 长度+关键词+非空"""
    if not answer or len(answer) < 10 or "错误" in answer:
        return 0.2
    score = 0.4 + min(0.3, len(answer)/500)  # 长度分
    keywords = ["LGOX","联邦","基因","飞轮","金字塔","节点","天工","地枢"]
    hits = sum(1 for k in keywords if k in answer)
    score += min(0.3, hits * 0.05)
    return round(min(score, 0.9), 2)

def write_gene(content, fitness):
    try:
        data = json.dumps({"content":content,"memory_type":"episodic",
            "source":"互测飞轮","fitness":fitness}).encode()
        req = urllib.request.Request(f"{LGE}/genes/write", data=data,
            headers={"Content-Type":"application/json","X-LGE-Key":LGE_KEY})
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read()).get("gene_id","")
    except: return ""

now = time.strftime("%H:%M")
print(f"[{now}] 互测飞轮启动")

# 随机选2个问题
q1, q2 = random.sample(QUESTIONS, 2)

# 小枢→天巡
print(f"  小枢问天巡: {q1[:30]}...")
a1 = chat(TIANXUN, q1)
s1 = score_answer(q1, a1)
print(f"  天巡答: {a1[:60]}... 评分:{s1}")
if s1 > 0.5:
    gid = write_gene(f"[互测·小枢→天巡] Q:{q1[:60]} A:{a1[:120]} 评分:{s1}", s1)
    if gid: print(f"  纳基因: {gid[:25]}...")

# 天巡→小枢
print(f"  天巡问小枢: {q2[:30]}...")
a2 = chat(XIAOSHU, q2)
s2 = score_answer(q2, a2)
print(f"  小枢答: {a2[:60]}... 评分:{s2}")
if s2 > 0.5:
    gid = write_gene(f"[互测·天巡→小枢] Q:{q2[:60]} A:{a2[:120]} 评分:{s2}", s2)
    if gid: print(f"  纳基因: {gid[:25]}...")

print(f"[{now}] 互测完成: 小枢{s1}·天巡{s2}")
