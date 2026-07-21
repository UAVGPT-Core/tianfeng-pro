#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  小枢↔天巡 500轮测 v3.0 · NGC全驱动                          ║
║  双AI角色对话·NGC生成+NGC评分·全链路NGC KEY                   ║
║  主人休·轮测启                                                ║
╚══════════════════════════════════════════════════════════════╝
"""
import urllib.request, urllib.error, json, time, sqlite3, os, random
from datetime import datetime

NGC_KEY = "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"
NGC_API = "https://integrate.api.nvidia.com/v1/chat/completions"
LGE_URL = "http://100.116.0.29:8200"
DB = os.path.expanduser("~/lgox-ops/data/roundtest_500.db")
ROUNDS = 500

# 双AI角色定义
XIAOSHU_PROMPT = """你是小枢，LGOX联邦第9节点·金融AI助手。你博学、精准、以数据说话。
回答要: 技术深度+具体数据+可验证来源。拒绝模糊回答。拒绝故事。只说事实。"""

TIANXUN_PROMPT = """你是天巡，LGOX联邦第10节点·企业AI哨兵。你务实、高效、以架构思维回答。
回答要: 系统架构视角+工程实践+落地建议。拒绝空谈。只说可执行的方案。"""

TOPICS = [
    "AI Agent记忆系统架构设计",
    "联邦学习中的隐私保护技术对比",
    "Transformer注意力机制的演进与优化",
    "知识图谱在RAG系统中的实际应用",
    "多模态模型融合策略的性能对比",
    "边缘AI推理部署的最佳实践",
    "大模型量化的精度-效率权衡",
    "分布式训练中的通信优化技术",
    "提示工程的系统性方法论",
    "AI安全对齐的技术路线与挑战",
    "向量数据库的索引策略对比",
    "GPU集群资源调度算法演进",
    "自动化ML管道设计模式",
    "大模型幻觉的检测与缓解方法",
    "代码生成AI的评测标准与局限",
    "神经符号AI的融合架构设计",
    "自监督学习的最新突破与局限",
    "Agent工具调用协议设计原则",
    "云原生AI服务治理模式",
    "实时推理系统的延迟优化策略",
]

def ngc_chat(system_prompt, user_msg, max_tokens=400, temp=0.7):
    """NGC API调用·429自愈重试"""
    body = json.dumps({
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ],
        "max_tokens": max_tokens, "temperature": temp
    }).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(NGC_API, data=body,
                headers={"Authorization": "Bearer " + NGC_KEY, "Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=30).read())
            return d["choices"][0]["message"]["content"].strip(), d["usage"]["total_tokens"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = (attempt + 1) * 8  # 更长的等待
                print(f"  ⚠️ 429·等{wait}s...", end="", flush=True)
                time.sleep(wait)
            else:
                raise
        except Exception:
            if attempt < 2:
                time.sleep(3)
    # 3次重试全失败→返回占位
    return f"[NGC429:已等{(1+2+3)*8}s]", 0

def ngc_judge(question, xiaoshu_ans, tianxun_ans, topic):
    """NGC裁判评分 0-100"""
    prompt = f"""你是AI裁判。评两份回答(0-100分)。

话题: {topic}
问题: {question[:200]}

【小枢回答】: {xiaoshu_ans[:300]}
【天巡回答】: {tianxun_ans[:300]}

评分标准: 准确性30+深度25+实用性25+表达20
输出格式: 小枢:XX|天巡:YY|理由(一行)"""
    try:
        body = json.dumps({"model":"meta/llama-3.1-8b-instruct",
            "messages":[{"role":"user","content":prompt}],
            "max_tokens":80,"temperature":0.3}).encode()
        req = urllib.request.Request(NGC_API, data=body,
            headers={"Authorization":"Bearer "+NGC_KEY,"Content-Type":"application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=15).read())
        resp = d["choices"][0]["message"]["content"].strip()
        import re
        scores = re.findall(r'(\d+)', resp)
        x_s = int(scores[0]) if len(scores) > 0 else 50
        t_s = int(scores[1]) if len(scores) > 1 else 50
        return x_s, t_s, resp[:80], d["usage"]["total_tokens"]
    except:
        return 50, 50, "默认50", 0

def lge_write(content, fitness=0.85):
    try:
        data = json.dumps({"content":content,"memory_type":"episodic",
            "source":"轮测引擎v3","tags":["roundtest","500","ngc","mutual"],
            "fitness":fitness}).encode()
        req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type":"application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=8).read()).get("gene_id","?")
    except: return None

def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS rounds (
            round_id INTEGER PRIMARY KEY,
            topic TEXT, question TEXT,
            xiaoshu_answer TEXT, xiaoshu_score INTEGER,
            tianxun_answer TEXT, tianxun_score INTEGER,
            judge_reason TEXT, tokens_used INTEGER,
            elapsed_ms INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    return conn

def run():
    conn = init_db()
    print(f"[{datetime.now().strftime('%m%d-%H%M%S')}] ═══ 小枢↔天巡 500轮测 v3.0·NGC全驱动 ═══")
    
    x_score, t_score = 0, 0
    x_wins, t_wins, draws = 0, 0, 0
    total_tokens = 0
    
    for r in range(1, ROUNDS + 1):
        topic = TOPICS[r % len(TOPICS)]
        t0 = time.time()
        
        # ① 生成问题(中性提问者)
        q_prompt = f"围绕'{topic}'，提出一个有深度、可验证的专业技术问题。只输出问题本身。"
        question, qt = ngc_chat("你是中立的AI技术评审", q_prompt, 100, 0.5)
        total_tokens += qt
        
        # ② 小枢回答
        xiaoshu_ans, xt = ngc_chat(XIAOSHU_PROMPT, question, 400, 0.7)
        total_tokens += xt
        
        # ③ 天巡回答
        tianxun_ans, tt = ngc_chat(TIANXUN_PROMPT, question, 400, 0.7)
        total_tokens += tt
        
        # ④ NGC裁判评分
        x_s, t_s, reason, jt = ngc_judge(question, xiaoshu_ans, tianxun_ans, topic)
        total_tokens += jt
        
        x_score += x_s
        t_score += t_s
        if x_s > t_s: x_wins += 1
        elif t_s > x_s: t_wins += 1
        else: draws += 1
        
        elapsed = int((time.time() - t0) * 1000)
        
        # 存DB
        conn.execute(
            "INSERT INTO rounds(round_id,topic,question,xiaoshu_answer,xiaoshu_score,tianxun_answer,tianxun_score,judge_reason,tokens_used,elapsed_ms) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (r, topic, question[:400], xiaoshu_ans[:400], x_s, tianxun_ans[:400], t_s, reason, qt+xt+tt+jt, elapsed)
        )
        conn.commit()
        
        if r % 50 == 0 or r <= 5:
            print(f"[{datetime.now().strftime('%H%M%S')}] 轮{r:3d}/{ROUNDS} | 小枢{x_s:3d} 天巡{t_s:3d} | {reason[:40]}")
        
        time.sleep(5)  # NGC限流保护·每轮5秒间隔
    
    # ═══ 终局 ═══
    x_avg = x_score // ROUNDS
    t_avg = t_score // ROUNDS
    winner = "小枢🏆" if x_score > t_score else ("天巡🏆" if t_score > x_score else "平局🤝")
    
    report = f"""### 小枢↔天巡 500轮测·NGC全驱动·终局报告
**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
**回合**: {ROUNDS}轮
**小枢**: 均分{x_avg}·总分{x_score}·胜{x_wins}局
**天巡**: 均分{t_avg}·总分{t_score}·胜{t_wins}局
**平局**: {draws}局
**胜者**: {winner}
**总token**: {total_tokens}
**引擎**: NGC meta/llama-3.1-8b-instruct 全驱动
"""
    print(f"\n{'='*50}")
    print(report)
    
    gid = lge_write(report, 0.92)
    print(f"基因: {gid}")
    conn.close()

if __name__ == "__main__":
    run()
