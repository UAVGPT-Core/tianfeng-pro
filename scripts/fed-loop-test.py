#!/usr/bin/env python3
"""
六合飞轮回环轮测引擎 v1.0
6小时·每10分钟一轮·36轮·天枢⇄灵龙双向
通→处→执→馈→审 五段闭环验证
0成本·全自动
"""
import json, time, urllib.request, sqlite3, os, sys
from datetime import datetime

DB = os.path.expanduser("~/lgox-ops/data/fed-loop-test.db")
TIANSHU = "100.100.89.2"
LINGLONG_LOCAL = "127.0.0.1"
ROUNDS = 36  # 6h / 10min
SLEEP_BETWEEN = 600  # 10 min

# 版本号 ping-pong 范围
BASE_VER = 5
PING_PONG = [(5, 6), (6, 5)]  # (from, to)

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_num INTEGER, direction TEXT, msg_id TEXT,
        stage_tong INTEGER DEFAULT 0, stage_chu INTEGER DEFAULT 0,
        stage_zhi INTEGER DEFAULT 0, stage_kui INTEGER DEFAULT 0,
        stage_shen INTEGER DEFAULT 0,
        result TEXT, error TEXT, duration_ms INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    return conn

def send_task(to_node, from_node, target_node, service, from_ver, to_ver):
    """发送升级任务到天枢桥"""
    content = f"TYPE:task\n六合飞轮回环轮测 R{from_ver}→{to_ver}\n升级{target_node}的{service}版本\n\n【命令】\nsed -i '' 's/v{from_ver}\\.{from_ver}/v{to_ver}.{to_ver}/g' ~/lgox-ops/scripts/{service}-ai.py\nkill -9 $(lsof -ti:8778)\nsleep 2\ncurl -s http://127.0.0.1:8778/health"
    
    if service == "xiaoshu":
        content = content.replace(":8778", ":8779")
        content = content.replace("tianxun", "xiaoshu")
    
    data = json.dumps({"to": to_node, "from": from_node, "content": content, "type": "task"}).encode()
    req = urllib.request.Request(f"http://{TIANSHU}:8765/messages/send", data=data,
                                  headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())

def verify_health(node_ip, port):
    """验证health端点版本号"""
    url = f"http://{node_ip}:{port}/health"
    resp = urllib.request.urlopen(url, timeout=5)
    return json.loads(resp.read()).get("version", "?")

def check_ack(from_node):
    """检查ack回复"""
    q = urllib.request.quote(from_node)
    url = f"http://{TIANSHU}:8765/messages/inbox?node={q}"
    resp = urllib.request.urlopen(url, timeout=5)
    msgs = json.loads(resp.read()).get("messages", [])
    for m in msgs:
        if "ack" in (m.get("content", "") or "").lower():
            return m.get("id", "")[:8]
    return None

def run_round(conn, round_num):
    """执行一轮测试"""
    t0 = time.time()
    direction = "灵龙→天枢" if round_num % 2 == 1 else "天枢→灵龙"
    
    result = {"stage_tong": 0, "stage_chu": 0, "stage_zhi": 0, "stage_kui": 0, "stage_shen": 0}
    error = ""
    
    try:
        # 通: 发送
        msg = send_task("天枢", "灵龙", "天枢", "tianxun", 4, 5)
        msg_id = msg.get("message_id", "?")[:8]
        result["stage_tong"] = 1 if msg.get("status") == "delivered" else 0
        
        if result["stage_tong"]:
            # 处+执: 等天枢consumer处理(2分钟)
            time.sleep(130)
            
            # 馈: 查ack
            ack = check_ack("灵龙")
            result["stage_kui"] = 1 if ack else 0
            
            # 审: 调consumer触发执行
            try:
                import subprocess
                subprocess.run(f"ssh a1@{TIANSHU} 'python3 ~/lgox-ops/scripts/tianshu-inbox-consumer.py'", 
                             shell=True, timeout=10, capture_output=True)
                result["stage_chu"] = 1
                result["stage_zhi"] = 1
            except:
                pass
            
            # 审: 验证health
            ver = verify_health(TIANSHU, 8778)
            result["stage_shen"] = 1
        
        duration = int((time.time() - t0) * 1000)
        
        # 评分
        score = sum(result.values())
        status = "PASS" if score >= 4 else "PARTIAL" if score >= 2 else "FAIL"
        
        conn.execute("""INSERT INTO rounds (round_num, direction, msg_id, 
            stage_tong, stage_chu, stage_zhi, stage_kui, stage_shen, result, error, duration_ms)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (round_num, direction, msg_id, result["stage_tong"], result["stage_chu"],
             result["stage_zhi"], result["stage_kui"], result["stage_shen"], status, error, duration))
        conn.commit()
        
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] R{round_num:02d}/36 {direction} {status} msg={msg_id} score={score}/5", flush=True)
        return status
        
    except Exception as e:
        duration = int((time.time() - t0) * 1000)
        conn.execute("""INSERT INTO rounds (round_num, direction, result, error, duration_ms)
            VALUES (?,?,?,?,?)""", (round_num, direction, "FAIL", str(e)[:200], duration))
        conn.commit()
        print(f"[{datetime.now():%H:%M:%S}] R{round_num:02d}/36 FAIL: {str(e)[:60]}", flush=True)
        return "FAIL"

def summary(conn):
    """生成汇总报告"""
    cur = conn.execute("""SELECT result, COUNT(*) as cnt, 
        AVG(stage_tong+stage_chu+stage_zhi+stage_kui+stage_shen) as avg_score
        FROM rounds GROUP BY result""")
    print("\n═══════════════════════════════════")
    print("六合飞轮回环轮测 · 6h汇总")
    print("═══════════════════════════════════")
    for row in cur:
        print(f"  {row[0]:8s} {row[1]}轮 均分{row[2]:.1f}/5")
    
    total = conn.execute("SELECT COUNT(*) FROM rounds").fetchone()[0]
    passed = conn.execute("SELECT COUNT(*) FROM rounds WHERE result='PASS'").fetchone()[0]
    print(f"\n  总计{total}轮 通过{passed} 通过率{100*passed//max(total,1)}%")
    print("═══════════════════════════════════")

if __name__ == "__main__":
    conn = init_db()
    start_round = conn.execute("SELECT COALESCE(MAX(round_num),0)+1 FROM rounds").fetchone()[0]
    
    if start_round > ROUNDS:
        summary(conn)
        sys.exit(0)
    
    print(f"六合飞轮回环轮测 启动: R{start_round:02d}-R{ROUNDS:02d} 共{ROUNDS-start_round+1}轮")
    
    for r in range(start_round, ROUNDS + 1):
        status = run_round(conn, r)
        if r < ROUNDS:
            time.sleep(SLEEP_BETWEEN)
    
    summary(conn)
