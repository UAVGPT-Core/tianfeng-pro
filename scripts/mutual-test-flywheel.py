#!/usr/bin/env python3
"""
小枢↔天巡 24h互测飞轮 v2.0 · 六维评分·对决算力·动态题库·自动纳基因
========================================================================
架构:
  每5min一轮·双回合对决
  Round1: 小枢出题→天巡答→小枢评分
  Round2: 天巡出题→小枢答→天巡评分
  每6轮: 同题双答对比(同一问题·两边各答·互评)
  每12轮: 基因蒸馏(高分对话→LGE)

评分六维:
  ① 准确性(事实) ② 完整性(覆盖) ③ 时效性(是否最新数据)
  ④ 一致性(与历史回答是否一致) ⑤ 简洁度(不啰嗦) ⑥ 专业性(术语用对)
"""
import urllib.request, json, time, random, os, sqlite3
from datetime import datetime

# === 配置 ===
XIAOSHU = "http://localhost:8779/chat/completions"
TIANXUN = "http://localhost:8778/chat/completions"
LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"
ROUNDS_PER_HOUR = 12  # 每5min=12轮/h
DB_PATH = os.path.expanduser("~/lgox-ops/data/mutual_test.db")

# === 动态题库(5大类·40题·VOD生成补充) ===
QUESTION_POOL = {
    "联邦知识": [
        "LGOX联邦目前有几个节点？分别叫什么名字和分工？",
        "九层金字塔v7.82的L3层负责什么功能？",
        "天工地枢之间用什么连接？速度多少？",
        "联邦的燃料路由现在有哪几层？",
        "六合飞轮的六个环节分别是什么？",
        "七自基因包括哪七个属性？",
        "联邦基因库现在有多少条基因？",
        "小枢和天巡分别是什么角色和定位？",
        "200Gb直连对基因生产带来什么改变？",
        "百度VOD和DS直连有什么区别？",
    ],
    "代码能力": [
        "用Python写一个函数合并两个有序数组。",
        "如何用asyncio并发请求3个API取最快结果？",
        "写一个SQL查询找出过去30天访问量最高的10个页面。",
        "用Bash一行命令统计nginx日志中状态码为500的请求数。",
        "Python中__slots__有什么作用？什么场景用？",
        "如何用Redis实现分布式锁？给出Python代码。",
        "Docker的bridge和host网络模式有什么区别？",
        "写一个正则匹配中国手机号和身份证号。",
    ],
    "逻辑推理": [
        "5个海盗分100金币·半数以上通过·最优方案？",
        "3个开关控制1盏灯·只进一次房间·如何确定哪个开关？",
        "12个球1个次品·天平秤3次·找出次品并知轻重。",
        "一瓶毒药1000瓶水·10只小白鼠·最少几次找到毒药？",
        "两个鸡蛋100层楼·最少几次找到临界层？",
        "8x8棋盘去掉对角2格·能用31张多米诺骨牌覆盖吗？",
    ],
    "低空经济+无人机": [
        "边缘AI在无人机巡检中有哪些应用场景？",
        "无人机机巢的AI Box应该具备哪些功能？",
        "低空经济2026年的政策趋势是什么？",
        "PX4和ArduPilot有什么区别？选哪个？",
        "无人机视觉巡检中如何做缺陷检测？",
        "5G+AI对无人机蜂群编队有什么意义？",
    ],
    "金融+量化": [
        "如何用Python获取A股实时行情数据？",
        "均线金叉和MACD金叉哪个更可靠？",
        "什么是夏普比率？如何计算？",
        "期权希腊字母Delta和Gamma分别代表什么？",
        "量化交易中如何避免过拟合？",
        "A股涨停板制度对量化策略有什么影响？",
    ],
}

# === 数据库初始化 ===
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH)
conn.execute("""
CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, round_type TEXT,
    asker TEXT, answerer TEXT,
    question TEXT, answer TEXT,
    scores TEXT, avg_score REAL,
    gene_id TEXT
)""")
conn.execute("""
CREATE TABLE IF NOT EXISTS cross_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, question TEXT,
    xiaoshu_answer TEXT, tianxun_answer TEXT,
    xiaoshu_score REAL, tianxun_score REAL,
    consistency REAL
)""")
conn.execute("""
CREATE TABLE IF NOT EXISTS stats_hourly (
    hour TEXT PRIMARY KEY,
    total_rounds INTEGER, avg_score REAL,
    xiaoshu_avg REAL, tianxun_avg REAL,
    genes_written INTEGER
)""")
conn.commit()

# === 核心函数 ===
def chat(url, question, max_tokens=250):
    try:
        data = json.dumps({"messages":[{"role":"user","content":question}],
            "max_tokens":max_tokens,"temperature":0.4,"stream":False}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[ERR:{e}]"

def multi_dim_score(question, answer, answerer):
    """六维评分"""
    if not answer or answer.startswith("[ERR") or len(answer) < 15:
        return {"accuracy":0.1,"completeness":0.1,"freshness":0.1,
                "consistency":0.1,"conciseness":0.5,"professionalism":0.1}, 0.15
    
    scores = {}
    # ①准确性: 关键词命中
    kw_map = {"节点":["天枢","灵龙","天工","地枢","太一","织网","天玑","天怿","小枢","天巡"],
              "金字塔":["L0","L1","L2","L3","L4","L5","L6","L7"],
              "基因":["基因","LGE","fitness"],
              "200Gb":["200Gb","直连","0.13ms"],
              "VOD":["百度","VOD","免费"],
              "飞轮":["飞轮","永动","cron"],
              "燃料":["T0","T1","T2","天工","智谱"]}
    hits = 0; total = 0
    for topic, kws in kw_map.items():
        if topic in question:
            total += len(kws)
            hits += sum(1 for k in kws if k in answer)
    scores["accuracy"] = round(0.3 + 0.7 * hits / max(total,1), 2) if total > 0 else 0.6
    
    # ②完整性: 长度+结构
    scores["completeness"] = round(0.2 + min(0.6, len(answer)/400) + (0.2 if any(tag in answer for tag in ["1.","2.","3.","首先","其次","最后"]) else 0), 2)
    
    # ③时效性: 是否包含实时数据
    scores["freshness"] = 0.85 if any(str(d) in answer for d in ["858","2026","v7.82","v3.5","v3.6"]) else 0.5
    
    # ④一致性: 与已知事实对比
    consistency_checks = [
        (["10个","10","十个"], "节点数应为10"),
        (["858","85万","85W","850k"], "基因数应约85万"),
        (["v7.82","7.82"], "金字塔版本v7.82"),
        (["200Gb","200G","400Gb"], "200Gb直连"),
    ]
    c_score = 0.5
    for patterns, _ in consistency_checks:
        if any(p in answer for p in patterns):
            c_score = min(1.0, c_score + 0.15)
    scores["consistency"] = round(c_score, 2)
    
    # ⑤简洁度
    scores["conciseness"] = round(max(0.3, 1.0 - len(answer)/800), 2) if len(answer) < 500 else 0.4
    
    # ⑥专业性
    prof_kw = ["API","HTTP","SSH","GPU","cron","launchd","nginx","VOD","DS","LGE"]
    hits_p = sum(1 for k in prof_kw if k in answer)
    scores["professionalism"] = round(0.3 + min(0.7, hits_p * 0.1), 2)
    
    avg = round(sum(scores.values())/6, 2)
    return scores, avg


# ═══ VOD Pro引擎(免费·高质量评分) ═══
def _get_vod_key():
    import os
    with open(os.path.expanduser("~/.hermes/.env")) as ef:
        for line in ef:
            if "BAIDU_VOD_KEY" in line:
                return line.split("=",1)[1].strip().strip('"').strip("'")
    return ""

def chat_pro(question, max_tokens=300):
    """VOD Pro·高质量推理"""
    try:
        vod_key = _get_vod_key()
        data = json.dumps({"model":"deepseek-v4-pro","messages":[{"role":"user","content":question}],
            "max_tokens":max_tokens,"temperature":0.3,"stream":False}).encode()
        req = urllib.request.Request("https://vod.bj.baidubce.com/v3/chat/oc/v1/chat/completions",
            data=data, headers={"Content-Type":"application/json","Authorization":f"Bearer {vod_key}"})
        with urllib.request.urlopen(req, timeout=35) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]
    except: return ""

def pro_dual_score(question, a_x, a_t):
    """VOD Pro双答对比评分·精准裁决"""
    try:
        vod_key = _get_vod_key()
        q = f"请评分以下两个AI回答哪个更好(0-10):\n问题:{question[:150]}\nA:{a_x[:200]}\nB:{a_t[:200]}\n只返回JSON:{{\"a\":分,\"b\":分,\"winner\":\"A/B/平\",\"why\":\"10字\"}}"
        data = json.dumps({"model":"deepseek-v4-pro","messages":[{"role":"user","content":q}],
            "max_tokens":100,"temperature":0.1,"stream":False}).encode()
        req = urllib.request.Request("https://vod.bj.baidubce.com/v3/chat/oc/v1/chat/completions",
            data=data, headers={"Content-Type":"application/json","Authorization":f"Bearer {vod_key}"})
        with urllib.request.urlopen(req, timeout=35) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]
    except: return ""

def write_gene(content, fitness):
    try:
        data = json.dumps({"content":content,"memory_type":"episodic",
            "source":"互测飞轮v2","fitness":fitness}).encode()
        req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type":"application/json","X-LGE-Key":LGE_KEY})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("gene_id","")
    except: return ""

def save_round(round_type, asker, answerer, question, answer, scores, avg, gene_id=""):
    conn.execute("INSERT INTO rounds(ts,round_type,asker,answerer,question,answer,scores,avg_score,gene_id) VALUES(?,?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat(), round_type, asker, answerer, question, answer[:500], json.dumps(scores), avg, gene_id))
    conn.commit()

def update_hourly(avg_score, answerer, genes):
    hour = datetime.now().strftime("%Y-%m-%d %H:00")
    existing = conn.execute("SELECT * FROM stats_hourly WHERE hour=?",(hour,)).fetchone()
    if existing:
        new_total = existing[1]+1
        new_avg = round((existing[2]*existing[1] + avg_score)/new_total, 2)
        if answerer == "小枢":
            conn.execute("UPDATE stats_hourly SET total_rounds=?,avg_score=?,xiaoshu_avg=? WHERE hour=?",
                (new_total, new_avg, round((existing[3]*existing[1]+avg_score)/new_total,2), hour))
        else:
            conn.execute("UPDATE stats_hourly SET total_rounds=?,avg_score=?,tianxun_avg=? WHERE hour=?",
                (new_total, new_avg, round((existing[4]*existing[1]+avg_score)/new_total,2), hour))
        conn.execute("UPDATE stats_hourly SET genes_written=genes_written+? WHERE hour=?",(genes, hour))
    else:
        x_avg = avg_score if answerer=="小枢" else 0
        t_avg = avg_score if answerer=="天巡" else 0
        conn.execute("INSERT INTO stats_hourly VALUES(?,?,?,?,?,?)",
            (hour,1,avg_score,x_avg,t_avg,genes))
    conn.commit()

# === 主流程 ===
now = datetime.now()
hour = now.hour
rnd = now.minute // 5  # 当前是第几个5分钟
total_rounds = conn.execute("SELECT COUNT(*) FROM rounds").fetchone()[0]

print(f"[{now.strftime('%H:%M')}] 互测飞轮v2.0 启动 (总{total_rounds}轮)")

genes_written = 0
all_scores = []

# === 模式1: 互问模式(每轮) ===
if rnd % 3 != 0:
    # 小枢→天巡
    cat, qs = random.choice(list(QUESTION_POOL.items()))
    q = random.choice(qs)
    print(f"  小枢→天巡: {q[:50]}...")
    a = chat(TIANXUN, q)
    s, avg = multi_dim_score(q, a, "天巡")
    print(f"  天巡: {avg:.2f}分 | {a[:80]}...")
    save_round("互测", "小枢", "天巡", q, a, s, avg)
    all_scores.append(avg)
    update_hourly(avg, "天巡", 0)
    if avg >= 0.65:
        gid = write_gene(f"[互测→天巡] Q:{q} A:{a[:200]} 六维:{s}", avg)
        if gid: genes_written += 1

    # 天巡→小枢
    cat, qs = random.choice(list(QUESTION_POOL.items()))
    q = random.choice(qs)
    print(f"  天巡→小枢: {q[:50]}...")
    a = chat(XIAOSHU, q)
    s, avg = multi_dim_score(q, a, "小枢")
    print(f"  小枢: {avg:.2f}分 | {a[:80]}...")
    save_round("互测", "天巡", "小枢", q, a, s, avg)
    all_scores.append(avg)
    update_hourly(avg, "小枢", 0)
    if avg >= 0.65:
        gid = write_gene(f"[互测→小枢] Q:{q} A:{a[:200]} 六维:{s}", avg)
        if gid: genes_written += 1

# === 模式2: 同题对比模式(每3轮=15min) ===
else:
    cat, qs = random.choice(list(QUESTION_POOL.items()))
    q = random.choice(qs)
    print(f"  ⚔️ 同题对决: {q[:50]}...")
    
    a_x = chat(XIAOSHU, q, max_tokens=200)
    s_x, avg_x = multi_dim_score(q, a_x, "小枢")
    print(f"  小枢: {avg_x:.2f}分 | {a_x[:60]}...")
    
    a_t = chat(TIANXUN, q, max_tokens=200)
    s_t, avg_t = multi_dim_score(q, a_t, "天巡")
    print(f"  天巡: {avg_t:.2f}分 | {a_t[:60]}...")
    
    # VOD Pro精准评分
    pro_judge = pro_dual_score(q, a_x, a_t)
    # 一致性评分
    overlap = len(set(a_x[:100]) & set(a_t[:100]))
    consistency = round(min(1.0, overlap / 50), 2)
    
    winner = "小枢" if avg_x > avg_t else ("天巡" if avg_t > avg_x else "平局")
    if pro_judge: print(f"  Pro裁决: {pro_judge[:120]}")
    print(f"  一致性:{consistency} · 胜者:{winner}")
    
    conn.execute("INSERT INTO cross_validations(ts,question,xiaoshu_answer,tianxun_answer,xiaoshu_score,tianxun_score,consistency) VALUES(?,?,?,?,?,?,?)",
        (now.isoformat(), q, a_x[:500], a_t[:500], avg_x, avg_t, consistency))
    conn.commit()
    
    all_scores.extend([avg_x, avg_t])
    update_hourly(avg_x, "小枢", 0)
    update_hourly(avg_t, "天巡", 0)
    
    # 高分纳基因
    if avg_x >= 0.7:
        gid = write_gene(f"[同题对决·小枢{avg_x}] Q:{q} A:{a_x[:200]} 六维:{s_x}", avg_x)
        if gid: genes_written += 1
    if avg_t >= 0.7:
        gid = write_gene(f"[同题对决·天巡{avg_t}] Q:{q} A:{a_t[:200]} 六维:{s_t}", avg_t)
        if gid: genes_written += 1

# === 基因蒸馏(每12轮=1h) ===
if total_rounds > 0 and total_rounds % 12 == 0:
    print(f"  🧬 基因蒸馏(第{total_rounds}轮)...")
    # 统计本小时高分问答
    hr = datetime.now().strftime("%Y-%m-%d %H:00")
    top = conn.execute("SELECT question,answer,avg_score FROM rounds WHERE ts>=? AND avg_score>=0.7 ORDER BY avg_score DESC LIMIT 5", (hr,)).fetchall()
    for q, a, score in top:
        gid = write_gene(f"[蒸馏·{score}] Q:{q} A:{a[:300]}", min(0.9, score+0.1))
        if gid:
            genes_written += 1
            print(f"    蒸馏基因: {gid[:25]}...")

# === 最终 ===
conn.execute("UPDATE stats_hourly SET genes_written=genes_written+? WHERE hour=?", 
    (genes_written, now.strftime("%Y-%m-%d %H:00")))
conn.commit()

today_rounds = conn.execute("SELECT COUNT(*),AVG(avg_score) FROM rounds WHERE ts>=?", 
    (now.strftime("%Y-%m-%d"),)).fetchone()
print(f"[{now.strftime('%H:%M')}] 完成 | 今日{today_rounds[0]}轮·均{today_rounds[1]:.2f}分 | 纳基因{genes_written}条")

conn.close()
