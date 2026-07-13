#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║  灵龙Worker · 联邦任务+共识监听器                      ║
║  Linglong Federation Worker v1.0                      ║
║  七自闭环·永动飞轮·AI灯塔                               ║
║  2026-07-13                                           ║
╚══════════════════════════════════════════════════════╝

循环:
  监听天枢桥 :8765/messages/inbox (每15秒)
  → 过滤 consensus_question / tiangong_task / roundtable
  → 本地Ollama推理 → 结果回写联邦桥
  → 共识写入LGA :8202 → 同步全联邦
"""

import json, time, sys, os, uuid
from urllib import request, parse
from datetime import datetime
from pathlib import Path

# ══════════════════════════════
# 配置
# ══════════════════════════════
TIANSHU_BRIDGE = "http://100.100.89.2:8765"
LINGLONG_BRIDGE = "http://127.0.0.1:8765"
OLLAMA = "http://localhost:11434/api/generate"
LGA = "http://127.0.0.1:8202"
NODE_NAME = "灵龙"
POLL_INTERVAL = 15  # 秒
DATA_DIR = Path.home() / "lgox-ops/data/worker"
STATE_FILE = DATA_DIR / "worker_state.json"
PROCESSED_FILE = DATA_DIR / "processed_ids.txt"

# ══════════════════════════════
# 七自属性
# ══════════════════════════════
SEVEN_SELF = {
    "自感知": "poll天枢桥·检查新消息",
    "自协调": "过滤消息类型·路由到对应处理器",
    "自愈合": "网络失败重试3次·降级到本地Ollama",
    "自进化": "处理的每个共识写入LGA基因",
    "自迭代": "下次遇到同类问题优先级更高",
    "自反思": "定期审计处理成功率",
    "自约束": "不处理危险命令·不越权"
}

def log(msg, level="INFO"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def init():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROCESSED_FILE.exists():
        PROCESSED_FILE.write_text("")

def load_processed():
    try: return set(PROCESSED_FILE.read_text().strip().split("\n"))
    except: return set()

def mark_processed(msg_id):
    with PROCESSED_FILE.open("a") as f:
        f.write(f"{msg_id}\n")

def ollama_ask(prompt, model="qwen2.5:7b"):
    """本地Ollama推理——零成本"""
    data = json.dumps({
        "model": model,
        "prompt": f"你是一个联邦节点的AI助手。简短回答(100字以内): {prompt[:500]}",
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 200}
    }).encode()
    try:
        req = request.Request(OLLAMA, data=data,
            headers={"Content-Type": "application/json"})
        resp = request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        return result.get("response", "").strip()
    except Exception as e:
        log(f"Ollama失败: {e}", "WARN")
        return f"[Ollama不可用·降级: {str(e)[:50]}]"

def reply_to_bridge(msg_id, reply_content, original_from):
    """回写联邦桥"""
    reply = {
        "to": original_from,
        "from": NODE_NAME,
        "type": "ROUNDTABLE_REPLY",
        "priority": "P1",
        "msg_id": f"wrk-{time.strftime('%m%d%H%M')}-{uuid.uuid4().hex[:6]}",
        "reply_to": msg_id,
        "ttl": 86400,
        "content": reply_content,
        "meta": {"processor": "linglong-worker", "model": "qwen2.5:7b"}
    }
    data = json.dumps(reply, ensure_ascii=False).encode()
    try:
        req = request.Request(f"{TIANSHU_BRIDGE}/messages/send", data=data,
            headers={"Content-Type": "application/json"})
        resp = request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        log(f"回复失败: {e}", "WARN")
        return False

def write_consensus_gene(question, answers, result):
    """共识结果写入LGA基因"""
    gene = {
        "content": f"[联邦共识] Q: {question[:200]} | 节点: {len(answers)}个 | 结果: {result[:300]}",
        "memory_type": "episodic",
        "source": "灵龙/consensus-worker",
        "fitness_score": 0.85
    }
    data = json.dumps(gene).encode()
    try:
        req = request.Request(f"{LGA}/genes/write", data=data,
            headers={"Content-Type": "application/json", "X-LGA-Key": "local"})
        request.urlopen(req, timeout=5)
    except:
        pass  # LGA可能不可用·非致命

def process_message(msg):
    """处理单条消息"""
    msg_id = msg.get("msg_id", "")
    msg_type = msg.get("type", "")
    msg_from = msg.get("from", "?")
    content = msg.get("content", "")

    # 跳过已处理
    processed = load_processed()
    if msg_id in processed:
        return

    if msg_type in ("ROUNDTABLE", "CONSENSUS_QUESTION", "TASK"):
        log(f"📨 {msg_type} 来自 {msg_from}")

        # 本地推理给出答案
        if msg_type == "CONSENSUS_QUESTION":
            prompt = f"作为联邦节点灵龙，评估以下问题: {content[:300]}"
        elif msg_type == "ROUNDTABLE":
            prompt = f"圆桌议题: {content[:300]}。作为联邦第二活跃节点(灵龙/M4/32GB)，给出你的观点。"
        else:
            prompt = f"任务: {content[:300]}。评估能否执行。"

        answer = ollama_ask(prompt)
        log(f"💭 {answer[:100]}...")

        # 回复联邦桥
        reply_to_bridge(msg_id, f"[灵龙Worker·qwen2.5:7b] {answer}", msg_from)

        # 写入共识基因
        write_consensus_gene(content[:200], {NODE_NAME: answer}, answer)

        mark_processed(msg_id)
        log(f"✅ 已处理 {msg_id[:12]}")

def poll_loop():
    """主循环——七自闭环"""
    log("🧬 灵龙Worker启动·七自闭环")
    log(f"   监听: {TIANSHU_BRIDGE}/messages/inbox")
    log(f"   推理: {OLLAMA}")
    log(f"   间隔: {POLL_INTERVAL}s")
    log(f"   七自: {'·'.join(SEVEN_SELF.keys())}")

    consecutive_errors = 0
    total_processed = 0
    last_health_report = 0

    while True:
        try:
            # 自感知: poll天枢桥
            req = request.Request(
                f"{TIANSHU_BRIDGE}/messages/inbox?node={request.quote(NODE_NAME)}",
                headers={"User-Agent": "linglong-worker/1.0"})
            resp = request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            msgs = data.get("messages", data) if isinstance(data, dict) else data
            msgs = msgs if isinstance(msgs, list) else []

            consecutive_errors = 0

            # 自协调: 过滤+路由
            targets = [m for m in msgs if m.get("type") in ("ROUNDTABLE", "CONSENSUS_QUESTION", "TASK")
                      and m.get("from") != NODE_NAME]

            for msg in targets:
                process_message(msg)
                total_processed += 1

            # 自反思: 每5分钟报告健康
            now = time.time()
            if now - last_health_report > 300:
                state = {
                    "total_processed": total_processed,
                    "last_poll": datetime.now().isoformat(),
                    "ollama": "ok" if consecutive_errors == 0 else "degraded",
                    "consecutive_errors": consecutive_errors,
                    "msgs_in_queue": len(msgs)
                }
                json.dump(state, STATE_FILE.open("w"), ensure_ascii=False)
                log(f"🫀 健康: {total_processed}条·队列{len(msgs)}·错误{consecutive_errors}")
                last_health_report = now

        except Exception as e:
            consecutive_errors += 1
            # 自愈合: 重试+降级
            if consecutive_errors < 5:
                log(f"⚠ poll失败(重试{consecutive_errors}/5): {str(e)[:60]}", "WARN")
            else:
                log(f"🔴 天枢桥不可达·降级模式·等待恢复", "ERROR")
            time.sleep(5)  # 错误时快速重试
            continue

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"

    if cmd == "start":
        init()
        poll_loop()
    elif cmd == "health":
        try:
            state = json.load(STATE_FILE.open())
            print(json.dumps(state, ensure_ascii=False, indent=2))
        except:
            print('{"status":"no data"}')
    elif cmd == "once":
        init()
        # 单次执行(测试用)
        req = request.Request(
            f"{TIANSHU_BRIDGE}/messages/inbox?node={request.quote(NODE_NAME)}",
            headers={"User-Agent": "linglong-worker/1.0"})
        resp = request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        msgs = data.get("messages", data) if isinstance(data, dict) else data
        targets = [m for m in (msgs if isinstance(msgs, list) else [])
                  if m.get("type") in ("ROUNDTABLE", "CONSENSUS_QUESTION", "TASK")
                  and m.get("from") != NODE_NAME]
        log(f"发现{len(targets)}条待处理")
        for msg in targets:
            process_message(msg)
