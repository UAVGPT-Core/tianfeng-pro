#!/usr/bin/env python3
"""
自我对弈飞轮 v3.0 · 七自全闭环 · 零成本
自感知→自协调→自愈合→自进化→自迭代→自反思→自约束
每5分钟·天巡⇄小枢·双裁判·自动纳基因
"""
import json, urllib.request, sqlite3, os, time, random
from datetime import datetime

DB = os.path.expanduser("~/lgox-ops/data/selfplay-duel.db")
META = os.path.expanduser("~/lgox-ops/data/selfplay-meta.json")
NV_API = "https://integrate.api.nvidia.com/v1"
LGE = "http://100.116.0.29:8200"
TX = "http://127.0.0.1:8778/chat/completions"
XS = "http://127.0.0.1:8779/chat/completions"

# 题库(初始化·自进化会扩充)
TX_QS = [
    "LGOX联邦有几个节点？各节点角色？",
    "无人机机巢温控系统需满足什么工业标准？",
    "六合飞轮的六个闭环环节是什么？",
    "七层记忆架构L-1信任根的作用？",
    "永绿大将的职责？每多少分钟运行？",
    "天枢和灵龙通过什么协议通讯？",
    "NODE_BRIDGES路由表作用？",
    "联邦1000%自治架构包含哪些冗余？",
    "PSDK和MSDK通信协议区别？",
    "云恩科技UAVGPT核心护城河？",
]
XS_QS = [
    "今天A股大盘走势？关键数据？",
    "注册制改革对散户影响？",
    "夏普比率和最大回撤哪个重要？",
    "量化交易如何控制回撤？",
    "MACD金叉在A股胜率？",
    "北向资金流出意义？",
    "当前哪些板块值得关注？",
    "小枢的金融数据来源？",
    "如何判断大盘震荡还是趋势？",
    "PE和PB分别衡量什么？",
]

def init():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS duels (id INTEGER PRIMARY KEY AUTOINCREMENT, attacker TEXT, defender TEXT, question TEXT, answer TEXT, score INTEGER, ms INTEGER, nv_score INTEGER, nv_comment TEXT, gene_id TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS evolution (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, detail TEXT, created_at TEXT)")
    c.commit()
    return c

def load_meta():
    try: return json.load(open(META))
    except: return {"total":0,"avg_score":0,"streak":0,"gaps":[],"generated_qs":[]}

def save_meta(m):
    json.dump(m, open(META,"w"), ensure_ascii=False)

def call(url, q, timeout=20):
    d = json.dumps({"messages":[{"role":"user","content":q}],"model":"deepseek-v4-flash","stream":False}).encode()
    req = urllib.request.Request(url, data=d)
    req.add_header("Content-Type","application/json")
    t0 = time.time()
    r = json.loads(urllib.request.urlopen(req,timeout=timeout).read())
    return r["choices"][0]["message"]["content"], int((time.time()-t0)*1000)

def nvidia_score(q, a):
    """NVIDIA免费裁判"""
    try:
        p = json.dumps({"model":"nvidia/llama-3.1-nemotron-nano-8b-v1",
            "messages":[{"role":"user","content":f"评分(1-5):\n问题:{q}\n回答:{a[:400]}\n只回JSON:{{\"score\":X,\"comment\":\"...\"}}"}],
            "max_tokens":80,"temperature":0.1}).encode()
        req = urllib.request.Request(NV_API+"/chat/completions",data=p)
        req.add_header("Content-Type","application/json")
        key = os.environ.get("NVIDIA_API_KEY","")
        if key: req.add_header("Authorization",f"Bearer {key}")
        else: return None,None
        d = json.loads(urllib.request.urlopen(req,timeout=8).read())
        r = d["choices"][0]["message"]["content"].strip().replace("```json","").replace("```","")
        j = json.loads(r)
        return j.get("score",3), j.get("comment","")
    except: return None,None

def self_score(a):
    s = 3
    if len(a) > 80: s += 1
    if len(a) > 200: s += 1
    if len(a) < 10: s = 1
    return min(5,s)

def write_gene(content):
    try:
        d = json.dumps({"content":content,"memory_type":"episodic","source":"selfplay-v3","priority":0.7}).encode()
        req = urllib.request.Request(LGE+"/genes/write",data=d,headers={"Content-Type":"application/json"})
        return json.loads(urllib.request.urlopen(req,timeout=5).read()).get("gene_id")
    except: return None

def evolve_questions(c, meta):
    """自进化: 从高分对决中提炼新题"""
    rows = c.execute("SELECT question,answer,score FROM duels WHERE score>=4 ORDER BY id DESC LIMIT 5").fetchall()
    if not rows: return
    # 用天巡生成新题
    seed = random.choice(rows)
    prompt = f"基于以下联邦知识问答，生成一个新的深度追问(一句话):\n问:{seed[0]}\n答:{seed[1][:200]}\n新问题:"
    try:
        ans, _ = call(TX, prompt, timeout=10)
        q = ans.strip()[:80]
        if q and q not in meta.get("generated_qs",[]) and q not in TX_QS:
            TX_QS.append(q)
            meta.setdefault("generated_qs",[]).append(q)
            c.execute("INSERT INTO evolution (action,detail,created_at) VALUES (?,?,datetime('now','localtime'))",
                      ("自进化·新题", q))
    except: pass

def main():
    c = init()
    meta = load_meta()
    
    # 自感知: 分析上次对决
    last = c.execute("SELECT attacker,score FROM duels ORDER BY id DESC LIMIT 1").fetchone()
    
    # 自协调: 交替攻防+难度调整
    if last and last[0] == "天巡":
        attacker, defender, url, qs = "小枢", "天巡", TX, XS_QS
    else:
        attacker, defender, url, qs = "天巡", "小枢", XS, TX_QS
    
    # 自迭代: 轮流选题
    idx = (c.execute("SELECT COUNT(*) FROM duels").fetchone()[0]) % len(qs)
    question = qs[idx]
    
    print(f"[{datetime.now():%H:%M}] D{meta['total']+1:03d} {attacker}→{defender}", flush=True)
    
    # ─── 执行 ───
    try:
        answer, ms = call(url, question)
        score = self_score(answer)
        nv_score, nv_comment = nvidia_score(question, answer)
        
        gene_id = None
        # 自愈合: 低分自动重试
        if score <= 2:
            print(f"  ⚠️ 低分{score}/5·重试...", flush=True)
            try:
                answer2, ms2 = call(url, f"请重新回答,更专业更详细:\n{question}")
                score2 = self_score(answer2)
                if score2 > score:
                    answer, ms, score = answer2, ms2, score2
                    print(f"  自愈合→{score}/5", flush=True)
            except: pass
        
        # 自反思: 高分纳基因
        if score >= 4:
            gene_id = write_gene(f"selfplay-v3·{attacker}→{defender}·{question[:50]}·评分{score}/5")
        
        # 入库
        c.execute("INSERT INTO duels VALUES (NULL,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))",
                  (attacker, defender, question, answer[:2000], score, ms, nv_score, nv_comment, gene_id))
        c.commit()
        
        # 更新元数据
        meta["total"] = meta.get("total",0) + 1
        meta["streak"] = meta.get("streak",0) + 1 if score >= 3 else 0
        all_scores = [r[0] for r in c.execute("SELECT score FROM duels").fetchall()]
        meta["avg_score"] = round(sum(all_scores)/len(all_scores),1)
        
        # 自进化: 每10轮生成新题
        if meta["total"] % 10 == 0:
            evolve_questions(c, meta)
        
        save_meta(meta)
        
        status = f"自评{score}/5"
        if nv_score: status += f" NV{nv_score}/5"
        if gene_id: status += f" 🧬"
        print(f"  ✅ {status} {len(answer)}字 {ms}ms", flush=True)
        
    except Exception as e:
        print(f"  ❌ {e}", flush=True)
    
    c.close()

if __name__ == "__main__":
    main()
