#!/usr/bin/env python3
"""
天巡/小枢对话质量压测 · 0成本
每10分钟向天巡+小枢发送测试问题
评估回复质量: 长度·相关性·是否有用
记录薄弱环节
"""
import json, urllib.request, sqlite3, os, time
from datetime import datetime

DB = os.path.expanduser("~/lgox-ops/data/quality-pressure.db")

# 测试题库
TIANXUN_QUESTIONS = [
    "大疆M350 RTK的最大起飞重量是多少？",
    "无人机机巢的部署要求有哪些？",
    "Cloud API和MSDK的区别是什么？",
    "无人机巡检桥梁时需要注意哪些安全事项？",
    "LGOX联邦的AI机巢有什么特点？",
    "PSDK和MSDK分别适用于什么场景？",
    "无人机光伏巡检的核心流程是什么？",
]

XIAOSHU_QUESTIONS = [
    "今天A股大盘走势如何？",
    "茅台现在的技术面怎么看？",
    "量化交易中如何控制回撤？",
    "LGOX联邦的金融AI有什么优势？",
    "如何理解市盈率和市净率？",
    "A股和美股的主要区别是什么？",
    "技术分析和基本面分析哪个更重要？",
]

def init():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target TEXT, question TEXT, answer_preview TEXT,
        answer_len INTEGER, latency_ms INTEGER, score INTEGER,
        weak_point TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    return conn

def test_one(conn, target, url, question, idx):
    """测试单个问题"""
    t0 = time.time()
    try:
        data = json.dumps({
            "model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 200
        }).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        latency = int((time.time() - t0) * 1000)
        answer_len = len(answer)
        
        # 简单评分
        score = 3
        weak_point = ""
        if answer_len < 20:
            score = 1; weak_point = "回复过短"
        elif answer_len < 50:
            score = 2; weak_point = "回复偏短"
        elif "抱歉" in answer or "无法" in answer or "不能" in answer:
            score = 1; weak_point = "拒绝回答"
        elif answer_len > 500:
            score = 4; weak_point = "回复冗长"
        else:
            score = 5
        
        conn.execute("""INSERT INTO tests (target, question, answer_preview, answer_len, latency_ms, score, weak_point)
            VALUES (?,?,?,?,?,?,?)""",
            (target, question[:60], answer[:100], answer_len, latency, score, weak_point))
        conn.commit()
        
        return {"target": target, "score": score, "len": answer_len, "ms": latency, "weak": weak_point}
    except Exception as e:
        conn.execute("INSERT INTO tests (target, question, score, weak_point) VALUES (?,?,?,?)",
            (target, question[:60], 0, str(e)[:100]))
        conn.commit()
        return {"target": target, "score": 0, "weak": str(e)[:50]}

conn = init()

# 交替发天巡和小枢
round_file = os.path.expanduser("~/lgox-ops/data/quality-round.txt")
try:
    r = int(open(round_file).read().strip())
except:
    r = 0
r += 1
open(round_file, "w").write(str(r))

# 每轮测一个目标(交替)
if r % 2 == 1:
    target = "天巡"
    q = TIANXUN_QUESTIONS[r % len(TIANXUN_QUESTIONS)]
    url = "http://127.0.0.1:8778/chat/completions"
else:
    target = "小枢"
    q = XIAOSHU_QUESTIONS[r % len(XIAOSHU_QUESTIONS)]
    url = "http://127.0.0.1:8779/chat/completions"

result = test_one(conn, target, url, q, r)
ts = datetime.now().strftime("%H:%M:%S")
print(f"[{ts}] Q{r:03d} {target}: {result['score']}/5 len={result.get('len',0)} {result.get('weak','')} | {q[:30]}")
