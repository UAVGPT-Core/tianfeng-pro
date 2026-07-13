#!/usr/bin/env python3
"""
六合飞轮回环轮测 v1.1 · 轻量版
每10分钟灵龙→天枢发升级指令
版本ping-pong: v3.5↔v3.6↔v3.5...
验证六合飞轮闭环
"""
import json, time, urllib.request, os, sqlite3
from datetime import datetime

TIANSHU = "100.100.89.2"
DB = os.path.expanduser("~/lgox-ops/data/fed-loop-test.db")
STATE = os.path.expanduser("~/lgox-ops/data/fed-loop-state.json")

def init():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS rounds (id INTEGER PRIMARY KEY AUTOINCREMENT, direction TEXT, msg_id TEXT, status TEXT, detail TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit(); conn.close()

def load_state():
    try: return json.load(open(STATE))
    except: return {"round": 0, "ver": 5}  # start at v3.5

def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f: json.dump(s, f)

init()
s = load_state()
s["round"] += 1

# 版本ping-pong: 5↔6↔5... (代表v3.5↔v3.6)
from_ver = s["ver"]
to_ver = 6 if from_ver == 5 else 5

# 交替天巡/小枢
service = "tianxun" if s["round"] % 2 == 1 else "xiaoshu"
port = 8778 if service == "tianxun" else 8779

content = f"TYPE:task\n六合轮测R{s['round']:02d}: {service} v3.{from_ver}→v3.{to_ver}\n\n【命令】\nsed -i '' 's/v3\\.{from_ver}/v3.{to_ver}/g' ~/lgox-ops/scripts/{service}-ai.py\nkill -9 $(lsof -ti:{port})\nsleep 2\ncurl -s http://127.0.0.1:{port}/health"

data = json.dumps({"to": "天枢", "from": "灵龙", "content": content, "type": "task"}).encode()
req = urllib.request.Request(f"http://{TIANSHU}:8765/messages/send", data=data,
                              headers={"Content-Type": "application/json"})
try:
    msg = json.loads(urllib.request.urlopen(req, timeout=10).read())
    msg_id = msg.get("message_id", "?")[:8]
    status = msg.get("status", "FAIL")
except Exception as e:
    msg_id = "ERR"
    status = f"FAIL:{str(e)[:30]}"

# 记录
conn = sqlite3.connect(DB)
conn.execute("INSERT INTO rounds (direction, msg_id, status, detail) VALUES (?,?,?,?)",
    (f"灵龙→天枢 {service}", msg_id, status, f"v3.{from_ver}→v3.{to_ver}"))
conn.commit(); conn.close()

s["ver"] = to_ver
save_state(s)

ts = datetime.now().strftime("%H:%M:%S")
print(f"[{ts}] R{s['round']:02d}/36 {service} v3.{from_ver}→v3.{to_ver} {status} {msg_id}")
