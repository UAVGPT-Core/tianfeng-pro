#!/usr/bin/env python3
"""
灵龙·联邦消息处理 v5.0 — 四层标准化
L1:消息分级(P0/P1/P2/P3) L2:会话线程 L3:降级保证 L4:能力发现
"""
import sqlite3, json, time, socket, os, urllib.request, threading

DB = "/Users/a112233/.hermes/fed_messages.db"
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765
TIANSHU_BRIDGE = "100.100.89.2"  # 天枢远程桥
STATE = "/tmp/linglong-reply-v5.json"
TX_URL = "http://127.0.0.1:8778/chat"
XS_URL = "http://127.0.0.1:8779/chat"
CAPABILITIES = {
    "node": "灵龙",
    "version": "v5.0",
    "message_types": ["P0·question", "P1·alert", "P2·sync", "P3·heartbeat"],
    "reply_guarantee": "P0:5s P1:30s P2:ack P3:silent",
    "fallback_chain": ["天巡:8778", "小枢:8779", "本地缓存", "延迟重试×3"],
}

def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f: return json.load(f)
    return {"replied": {}, "retry_queue": []}

def save_state(st):
    st["replied"] = dict(list(st["replied"].items())[-500:])
    with open(STATE, "w") as f: json.dump(st, f)

def send_msg(to_node, content, msg_type="灵龙AI回答"):
    """双桥发送:type嵌入content前缀(桥DB无type列)"""
    tagged = f"[TYPE:{msg_type}] {content}"
    ok = False
    body = json.dumps({"to": to_node, "content": tagged, "type": msg_type, "from": "灵龙"})
    for host in [TIANSHU_BRIDGE, BRIDGE_HOST]:
        try:
            s = socket.socket(); s.settimeout(5)
            s.connect((host, BRIDGE_PORT))
            s.sendall(f'POST /messages/send HTTP/1.0\r\nHost:{host}\r\nContent-Type:application/json\r\nContent-Length:{len(body)}\r\n\r\n{body}'.encode())
            if "200" in s.recv(1024).decode(): ok = True
            s.close()
        except: pass
    return ok

def ask_ai(question, prefer="tx"):
    """L3降级保证: 天巡→小枢→重试"""
    urls = [("天巡", TX_URL), ("小枢", XS_URL)] if prefer == "tx" else [("小枢", XS_URL), ("天巡", TX_URL)]
    for name, url in urls:
        for attempt in range(2):
            try:
                payload = json.dumps({"question": question}).encode()
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    resp = json.loads(r.read())
                answer = resp.get("answer", "")
                if answer and len(answer) > 20:
                    return f"[{name}答] {answer[:500]}"
            except:
                if attempt == 0: time.sleep(1)
                continue
    return None

def extract_question(content):
    for prefix in ['[提问]', '[问题]', '[Q]', 'Q:', '问:']:
        if content.startswith(prefix): content = content[len(prefix):]
    for sep in ['？', '?', '\n']:
        idx = content.find(sep)
        if idx > 5: return content[:idx+1] if sep in '？?' else content[:idx]
    return content[:200]

def classify(content, msg_type):
    """L1消息分级"""
    if msg_type in ('提问', 'question', '灵龙AI回答'):
        return 'P0'
    if '?' in content or '？' in content:
        return 'P0'
    if '告警' in content or '路断' in content or '巡检' in content:
        return 'P1'
    # P3心跳检测: 精准匹配飞轮脉冲/轮询消息，避免GCP标准等含FCPF的正常消息误判
    if content.startswith('[大飞轮') or (content.startswith('📊FCPF') and '·poll' in content):
        return 'P3'
    return 'P2'

def main():
    st = load_state()
    replied = st.get("replied", {})
    
    try:
        db = sqlite3.connect(DB)
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM messages WHERE ts > datetime('now','-2 hours') ORDER BY ts DESC LIMIT 100").fetchall()
        db.close()
    except Exception as e:
        print(f"DB err: {e}"); return
    
    new_replies = 0
    for r in rows:
        rid = r['id']
        content = r['content'] or ''
        from_node = r['from_node'] or ''
        msg_type = r['type'] if 'type' in r.keys() else ''
        
        # 跳过已回复或心跳
        if rid in replied: continue
        priority = classify(content, msg_type)
        if priority == 'P3': continue  # 心跳静默
        
        # 只处理天枢消息
        if from_node != '天枢': continue
        
        now = time.time()
        last_retry = replied.get(rid, {}).get('retry_ts', 0) if isinstance(replied.get(rid), dict) else 0
        
        if priority == 'P0':
            q = extract_question(content)
            ai_answer = ask_ai(q, prefer="tx")
            
            if ai_answer:
                reply = f"[灵龙·P0回答] {ai_answer}"
                if send_msg('天枢', reply, '灵龙AI回答'):
                    new_replies += 1
                    replied[rid] = {'ts': now, 'status': 'answered'}
                    print(f"[{time.strftime('%H:%M')}] P0·AI回答: {q[:40]}...")
            else:
                # L3降级: 记录重试
                retry_count = replied.get(rid, {}).get('retries', 0) if isinstance(replied.get(rid), dict) else 0
                if retry_count < 3:
                    replied[rid] = {'retry_ts': now, 'retries': retry_count + 1, 'status': 'retrying'}
                    print(f"[{time.strftime('%H:%M')}] P0·重试{retry_count+1}/3: {q[:40]}...")
                else:
                    # 3次失败→告警
                    send_msg('天枢', f"[灵龙·降级告警] AI引擎3次重试失败: {q[:60]}", '灵龙告警')
                    replied[rid] = {'ts': now, 'status': 'failed'}
                    print(f"[{time.strftime('%H:%M')}] P0·耗尽: {q[:40]}...")
        
        elif priority == 'P1':
            reply = f"[灵龙·P1确认] 告警已记录。天巡79万+·小枢79万+·联邦桥在线。"
            send_msg('天枢', reply, '灵龙确认')
            replied[rid] = {'ts': now, 'status': 'acked'}
        
        elif priority == 'P2':
            replied[rid] = {'ts': now, 'status': 'acked'}  # 确认但不回复
    
    st["replied"] = replied
    save_state(st)

if __name__ == "__main__":
    main()
