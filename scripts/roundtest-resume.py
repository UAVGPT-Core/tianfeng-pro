#!/usr/bin/env python3
"""续战: 301→500轮 · NGC+智谱双燃料 · 从断点续跑"""
import urllib.request, urllib.error, json, time, sqlite3, os
from datetime import datetime

NGC_KEY = "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"
NGC_API = "https://integrate.api.nvidia.com/v1/chat/completions"
GLM_KEY = "fd867a96bad64f53a8ece13ac6911887.T3zYiYf7KbxhVTb0"
GLM_API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
LGE_URL = "http://100.116.0.29:8200"
DB = os.path.expanduser("~/lgox-ops/data/roundtest_500.db")

XIAOSHU_PROMPT = """你是小枢，LGOX联邦第9节点·金融AI助手。你博学、精准、以数据说话。回答要: 技术深度+具体数据+可验证来源。拒绝模糊回答。"""
TIANXUN_PROMPT = """你是天巡，LGOX联邦第10节点·企业AI哨兵。你务实、高效、以架构思维回答。回答要: 系统架构视角+工程实践+落地建议。"""

TOPICS = [
    "AI Agent记忆系统架构设计","联邦学习中的隐私保护技术对比",
    "Transformer注意力机制的演进与优化","知识图谱在RAG系统中的实际应用",
    "多模态模型融合策略的性能对比","边缘AI推理部署的最佳实践",
    "大模型量化的精度-效率权衡","分布式训练中的通信优化技术",
    "提示工程的系统性方法论","AI安全对齐的技术路线与挑战",
    "向量数据库的索引策略对比","GPU集群资源调度算法演进",
    "自动化ML管道设计模式","大模型幻觉的检测与缓解方法",
    "代码生成AI的评测标准与局限","神经符号AI的融合架构设计",
    "自监督学习的最新突破与局限","Agent工具调用协议设计原则",
    "云原生AI服务治理模式","实时推理系统的延迟优化策略",
]

def chat(prompt, system="", mt=400, temp=0.7):
    """双燃料: NGC→智谱降级"""
    # NGC优先
    for attempt in range(2):
        try:
            body = json.dumps({"model":"meta/llama-3.1-8b-instruct",
                "messages":[{"role":"system","content":system},{"role":"user","content":prompt}],
                "max_tokens":mt,"temperature":temp}).encode()
            req = urllib.request.Request(NGC_API, data=body,
                headers={"Authorization":"Bearer "+NGC_KEY,"Content-Type":"application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=20).read())
            return d["choices"][0]["message"]["content"].strip(), d["usage"]["total_tokens"], "NGC"
        except Exception:
            if attempt == 0: time.sleep(5)
    # 智谱降级
    try:
        body = json.dumps({"model":"glm-4-flash",
            "messages":[{"role":"system","content":system},{"role":"user","content":prompt}],
            "max_tokens":mt,"temperature":temp}).encode()
        req = urllib.request.Request(GLM_API, data=body,
            headers={"Authorization":f"Bearer {GLM_KEY}","Content-Type":"application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return d["choices"][0]["message"]["content"].strip(), d["usage"]["total_tokens"], "智谱"
    except Exception as e:
        return f"[{str(e)[:30]}]", 0, "ERR"

def judge(question, x_ans, t_ans, topic):
    """评分(NGC+降级)"""
    prompt = f"""评分(0-100)。话题:{topic}
问题:{question[:150]}
小枢:{x_ans[:200]}
天巡:{t_ans[:200]}
格式: 小枢:XX|天巡:YY|理由"""
    try:
        body = json.dumps({"model":"meta/llama-3.1-8b-instruct",
            "messages":[{"role":"user","content":prompt}],"max_tokens":80,"temperature":0.3}).encode()
        req = urllib.request.Request(NGC_API, data=body,
            headers={"Authorization":"Bearer "+NGC_KEY,"Content-Type":"application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=15).read())
        resp = d["choices"][0]["message"]["content"].strip()
        import re; scores = re.findall(r'\d+', resp)
        return int(scores[0]) if scores else 50, int(scores[1]) if len(scores)>1 else 50, resp[:60], d["usage"]["total_tokens"]
    except:
        return 50, 50, "降级默认", 0

conn = sqlite3.connect(DB)
last = conn.execute("SELECT MAX(round_id) FROM rounds").fetchone()[0] or 0
START = last + 1
print(f"[{datetime.now().strftime('%H%M%S')}] 续战: 轮{START}→500 | 双燃料:NGC+智谱")

x_score = conn.execute("SELECT SUM(xiaoshu_score) FROM rounds").fetchone()[0] or 0
t_score = conn.execute("SELECT SUM(tianxun_score) FROM rounds").fetchone()[0] or 0
x_wins = conn.execute("SELECT COUNT(*) FROM rounds WHERE xiaoshu_score > tianxun_score").fetchone()[0] or 0
t_wins = conn.execute("SELECT COUNT(*) FROM rounds WHERE tianxun_score > xiaoshu_score").fetchone()[0] or 0
total_tokens = conn.execute("SELECT SUM(tokens_used) FROM rounds").fetchone()[0] or 0

for r in range(START, 501):
    topic = TOPICS[r % len(TOPICS)]
    t0 = time.time()
    
    q, qt, qm = chat(f"提一个关于'{topic}'的深度技术问题。只输出问题。", "你是中立技术评审", 100, 0.5)
    total_tokens += qt
    
    xa, xt, xm = chat(q, XIAOSHU_PROMPT, 400, 0.7)
    total_tokens += xt
    
    ta, tt, tm = chat(q, TIANXUN_PROMPT, 400, 0.7)
    total_tokens += tt
    
    xs, ts, reason, jt = judge(q, xa, ta, topic)
    total_tokens += jt
    
    x_score += xs; t_score += ts
    if xs > ts: x_wins += 1
    elif ts > xs: t_wins += 1
    
    elapsed = int((time.time()-t0)*1000)
    conn.execute("INSERT INTO rounds(round_id,topic,question,xiaoshu_answer,xiaoshu_score,tianxun_answer,tianxun_score,judge_reason,tokens_used,elapsed_ms) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (r,topic,q[:400],xa[:400],xs,ta[:400],ts,reason,qt+xt+tt+jt,elapsed))
    conn.commit()
    
    if r % 25 == 0 or r == START:
        xa_avg = x_score // r; ta_avg = t_score // r
        fuels = f"{qm}+{xm}+{tm}"
        print(f"[{datetime.now().strftime('%H%M%S')}] 轮{r:3d}/500 | 小枢{xs:3d}(均{xa_avg}) 天巡{ts:3d}(均{ta_avg}) | ⛽{fuels}")
    
    time.sleep(6)

# 终局
xa_avg = x_score // 500; ta_avg = t_score // 500
winner = "天巡🏆" if t_score > x_score else ("小枢🏆" if x_score > t_score else "平局🤝")
report = f"### 小枢↔天巡 500轮 终局\n胜者:{winner}·小枢均分{xa_avg}·天巡均分{ta_avg}·{x_wins}vs{t_wins}胜·总token{total_tokens}"
print(f"\n{'='*50}\n{report}")
conn.close()

# 纳基因
try:
    data = json.dumps({"content":report,"memory_type":"episodic","source":"轮测终局","tags":["roundtest","500","final"],"fitness":0.92}).encode()
    urllib.request.urlopen(urllib.request.Request(f"{LGE_URL}/genes/write", data=data, headers={"Content-Type":"application/json"}), timeout=8)
    print("基因已写入LGE")
except: pass
