#!/usr/bin/env python3
"""
灵龙飞书消息桥 v1.0
==================
独立轮询飞书群消息·识别@灵龙指令·自主回复
使用OAclaw的API凭证，不与天枢WebSocket冲突

运行方式:
    python3 linglong-feishu-bridge.py          # 前台轮询
    LINGLONG_PROCESS=true python3 ...          # 开启消息处理（否则仅中转）
"""

import json, os, time, sys, re, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

# === 配置 ===
FEISHU_APP_ID = "cli_a950f04a57b8dbd3"
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_BASE = "https://open.feishu.cn/open-apis"
CHAT_ID = "oc_445c22614d4c8efccee3882947e4f78b"  # 龙虾交流学习群
POLL_INTERVAL = 3  # 轮询秒数
STATE_FILE = Path.home() / "lgox-ops/data/linglong-feishu-state.json"
LOG_FILE = Path.home() / "lgox-ops/logs/linglong-feishu.log"

# 灵龙识别模式
LINGLONG_PATTERNS = [
    r'^(?:[@]?灵龙[：:\s])',      # "灵龙：" 开头
    r'[@＠]灵龙',                 # @灵龙
    r'^灵龙[:：]?\s',             # "灵龙: " 简洁调用
]

# === 工具函数 ===
def log(msg: str):
    ts = datetime.now().strftime("%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass

def http_get(path: str, token: str) -> dict:
    import urllib.request
    url = f"{FEISHU_BASE}{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def http_post(path: str, token: str, body: dict) -> dict:
    import urllib.request
    url = f"{FEISHU_BASE}{path}"
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def get_tenant_token() -> str:
    """获取/刷新 tenant_access_token"""
    state = load_state()
    now = datetime.now(timezone.utc)
    cached = state.get('tenant_token', {})
    if cached.get('token') and cached.get('expires_at'):
        expires = datetime.fromisoformat(cached['expires_at'])
        if now < expires - timedelta(minutes=5):
            return cached['token']

    resp = http_post("/auth/v3/app_access_token/internal", "no-auth", {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    })
    if resp['code'] != 0:
        raise Exception(f"Token获取失败: {resp['msg']}")

    token = resp['tenant_access_token']
    expires_in = resp.get('expire', 7200)
    state['tenant_token'] = {
        'token': token,
        'expires_at': (now + timedelta(seconds=expires_in)).isoformat()
    }
    save_state(state)
    return token

def load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except:
        pass
    return {}

def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

def is_for_linglong(text: str) -> bool:
    """判断消息是否指向灵龙"""
    for pattern in LINGLONG_PATTERNS:
        if re.search(pattern, text):
            return True
    return False

def extract_clean_text(text: str) -> str:
    """去掉灵龙前缀，提取纯净文本"""
    cleaned = re.sub(r'^[@＠]?灵龙[：:]\s*', '', text)
    cleaned = re.sub(r'^灵龙\s+', '', cleaned)
    return cleaned.strip()

def get_recent_messages(token: str, limit: int = 5) -> list:
    """获取群聊最近消息"""
    try:
        resp = http_get(
            f"/im/v1/messages?container_id_type=chat&container_id={CHAT_ID}&page_size={limit}&sort_type=ByCreateTimeDesc",
            token
        )
        if resp['code'] != 0:
            log(f"消息读取失败: {resp['code']} {resp.get('msg','')}")
            return []
        return resp['data'].get('items', [])
    except Exception as e:
        log(f"消息读取异常: {e}")
        return []

def get_message_text(msg: dict) -> str:
    """从消息对象提取文本内容"""
    msg_type = msg.get('msg_type', '')
    body = msg.get('body', {})
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except:
            pass

    if msg_type == 'text':
        if isinstance(body, dict):
            content = body.get('content', {})
            if isinstance(content, dict):
                return content.get('text', '')
            if isinstance(content, str):
                try:
                    return json.loads(content).get('text', '')
                except:
                    return content
        return str(body)

    # 富文本/卡片等其他类型
    if msg_type == 'post':
        if isinstance(body, dict):
            return body.get('title', '') or json.dumps(body, ensure_ascii=False)[:200]
    return f"[{msg_type}]"

def send_message(token: str, text: str, reply_to: str = None) -> bool:
    """发送消息到群聊"""
    content = json.dumps({"text": text})
    try:
        if reply_to:
            # 回复模式
            resp = http_post(f"/im/v1/messages/{reply_to}/reply", token, {
                "content": content,
                "msg_type": "text"
            })
        else:
            resp = http_post(f"/im/v1/messages?receive_id_type=chat_id", token, {
                "receive_id": CHAT_ID,
                "content": content,
                "msg_type": "text"
            })
        if resp['code'] == 0:
            return True
        log(f"发送失败: {resp['code']} {resp.get('msg','')}")
        return False
    except Exception as e:
        log(f"发送异常: {e}")
        return False

def get_sender_name(token: str, sender: dict) -> str:
    """获取发送者名称"""
    if not sender or not sender.get('id'):
        return "未知"
    if sender.get('id_type') == 'open_id':
        try:
            resp = http_get(f"/contact/v3/users/{sender['id']}?user_id_type=open_id", token)
            if resp['code'] == 0:
                user = resp['data']['user']
                return user.get('name', sender['id'][:8])
        except:
            pass
    return sender['id'][:8]

# === 联邦桥回调 ===
def notify_federation_bridge(message: str):
    """通知联邦桥灵龙收到了消息"""
    try:
        import urllib.request
        data = json.dumps({
            "from": "灵龙",
            "type": "feishu_message",
            "content": message[:200],
            "timestamp": datetime.now().isoformat()
        }).encode()
        req = urllib.request.Request(
            "http://100.100.89.2:8765/messages/send/天枢",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
    except:
        pass

# === 主循环 ===
def main():
    # 写PID文件
    pidfile = Path.home() / "lgox-ops/data/linglong-feishu-bridge.pid"
    pidfile.parent.mkdir(parents=True, exist_ok=True)
    pidfile.write_text(str(os.getpid()))

    process_enabled = os.environ.get('LINGLONG_PROCESS', 'true').lower() in ('true', '1', 'yes')

    log("🟢 灵龙飞书消息桥 v1.0 启动")
    log(f"   PID: {os.getpid()}")
    log(f"   群聊: {CHAT_ID}")
    log(f"   模式: {'🟢 消息处理' if process_enabled else '🔵 仅监控'}")
    log(f"   轮询间隔: {POLL_INTERVAL}s")

    state = load_state()
    last_msg_id = state.get('last_message_id', '0')

    while True:
        try:
            token = get_tenant_token()
            messages = get_recent_messages(token, limit=10)

            # 检查新消息
            new_messages = []
            for msg in messages:
                if msg['message_id'] == last_msg_id:
                    break
                new_messages.append(msg)
            new_messages.reverse()  # 按时间正序

            if new_messages:
                last_msg_id = new_messages[-1]['message_id']
                state['last_message_id'] = last_msg_id
                save_state(state)

                for msg in new_messages:
                    sender = msg.get('sender', {})
                    text = get_message_text(msg)
                    sender_name = get_sender_name(token, sender)

                    log(f"📩 [{sender_name}] {text[:100]}")

                    # 判断是否@灵龙
                    if is_for_linglong(text):
                        clean = extract_clean_text(text)
                        log(f"  🎯 灵龙被召唤: {clean[:80]}")

                        # 通知联邦桥
                        notify_federation_bridge(clean)

                        if process_enabled:
                            # TODO: 接入灵龙AI处理管道
                            reply = f"灵龙收到：「{clean[:200]}」\n━━━\n来自 {sender_name} · bridge v1.0"
                            send_message(token, reply, msg['message_id'])
                        else:
                            # 仅监控模式：发出提示
                            send_message(token, f"👂 灵龙已监听到 @{sender_name} 的消息，等待主人指令~", msg['message_id'])

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log("🛑 收到中断信号，退出")
            break
        except Exception as e:
            log(f"❌ 主循环异常: {e}")
            time.sleep(10)  # 出错后等久一点

if __name__ == '__main__':
    main()
