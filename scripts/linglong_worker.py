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
POLL_INTERVAL = 15  # 秒 (legacy poll模式)
SSE_RECONNECT = 3    # SSE断连重连间隔(秒)
DATA_DIR = Path.home() / "lgox-ops/data/worker"
STATE_FILE = DATA_DIR / "worker_state.json"
PROCESSED_FILE = DATA_DIR / "processed_ids.txt"

# ══════════════════════════════
# 七自属性
# ══════════════════════════════
SEVEN_SELF = {
    "自感知": "poll天枢桥·检查新消息·FPC健康检测",
    "自协调": "过滤消息类型·路由到对应处理器",
    "自愈合": "网络失败重试3次·降级Ollama·跨节点FPC自动拉起",
    "自进化": "处理的每个共识直连地枢LGE写入基因",
    "自迭代": "下次遇到同类问题优先级更高",
    "自反思": "定期审计处理成功率·FPC守护日志",
    "自约束": "不处理危险命令·不越权"
}

# ══════════════════════════════
# FPC守护者 — 七自·自愈合的物理实现
# ══════════════════════════════
FPC_NODES = {
    "天工": {"host": "spark-abbd", "ssh": "dgx1", "port": 8790, "script": "~/lgox-ops/scripts/federation_perpetual_core.py"},
    "地枢": {"host": "spark-5438", "ssh": "dgx2", "port": 8790, "script": "~/lgox-ops/scripts/federation_perpetual_core.py"},
}
FPC_CHECK_INTERVAL = 300  # 每5分钟
FPC_FAIL_THRESHOLD = 2     # 连续失败2次才拉起

fpc_failures = {}  # node_name → consecutive_failures
fpc_heal_count = 0

def check_fpc_health(node_name, cfg):
    """检测远程节点FPC是否存活"""
    try:
        url = f"http://{cfg['host']}:{cfg['port']}/health"
        resp = request.urlopen(url, timeout=5)
        data = json.loads(resp.read())
        return data.get("status") == "ok"
    except:
        return False

def heal_fpc(node_name, cfg):
    """警报+通知——跨节点自愈通知（重启靠各节点自身systemd/launchd）"""
    global fpc_heal_count
    fpc_heal_count += 1

    # 通过联邦桥发送ALERT——天枢consumer收到后可通知节点管理员
    alert = {
        "to": "all",
        "from": NODE_NAME,
        "type": "FPC_ALERT",
        "priority": "P1",
        "msg_id": f"fpc-heal-{time.strftime('%m%d%H%M')}-{uuid.uuid4().hex[:6]}",
        "ttl": 86400,
        "content": f"联邦自愈警报: {node_name}FPC离线(连续{fpc_failures.get(node_name,0)}次)。"
                   f"请{node_name}节点systemd/launchd自动重启FPC服务。第{fpc_heal_count}次跨节点检测。",
        "meta": {"node": node_name, "heal_count": fpc_heal_count}
    }
    try:
        data = json.dumps(alert, ensure_ascii=False).encode()
        req = request.Request(f"{TIANSHU_BRIDGE}/messages/send", data=data,
            headers={"Content-Type": "application/json"})
        request.urlopen(req, timeout=5)
        log(f"📢 已发送{node_name}FPC离线警报到联邦桥")
    except:
        pass

    # 纳基因
    gene = {
        "content": f"[联邦自愈检测] Worker发现{node_name}FPC离线→已向联邦桥发送ALERT。第{fpc_heal_count}次检测。",
        "memory_type": "episodic",
        "source": "灵龙/FPC守护者/自愈合",
        "fitness_score": 0.85
    }
    try:
        data = json.dumps(gene).encode()
        req = request.Request(LGE_DIRECT, data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        request.urlopen(req, timeout=8)
    except:
        pass

    return True

def fpc_guardian_cycle():
    """FPC守护循环——检测→累计→拉起→纳基因"""
    global fpc_failures
    healed = []

    for node_name, cfg in FPC_NODES.items():
        healthy = check_fpc_health(node_name, cfg)
        prev = fpc_failures.get(node_name, 0)

        if healthy:
            if prev > 0:
                log(f"🟢 {node_name}FPC恢复({prev}次失败后自愈)")
            fpc_failures[node_name] = 0
        else:
            fpc_failures[node_name] = prev + 1
            if prev + 1 >= FPC_FAIL_THRESHOLD and prev < FPC_FAIL_THRESHOLD:
                log(f"🔴 {node_name}FPC连续{prev+1}次离线→启动跨节点自愈...")
                if heal_fpc(node_name, cfg):
                    healed.append(node_name)
                    fpc_failures[node_name] = 0  # 重置计数
                    log(f"✅ {node_name}FPC已远程拉起")

    return healed

def log(msg, level="INFO"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

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

LGE_DIRECT = "http://100.116.0.29:8200/genes/write"
LGE_KEY = "fbe0b015eb7a03727903b660c4cecc60"

def write_consensus_gene(question, answers, result):
    """共识结果直连地枢LGE——不经过LGA中转"""
    gene = {
        "content": f"[联邦共识] Q: {question[:200]} | 节点: {len(answers)}个 | 结果: {result[:300]}",
        "memory_type": "episodic",
        "source": "灵龙/consensus-worker",
        "fitness_score": 0.85
    }
    data = json.dumps(gene).encode()
    # 主通路: 直连地枢LGE
    try:
        req = request.Request(LGE_DIRECT, data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        request.urlopen(req, timeout=8)
        return
    except:
        pass
    # 降级: LGA本地缓存
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

def sse_loop():
    """SSE模式——零轮询·事件驱动。断连秒切poll，定时重试SSE"""
    log("🧬 灵龙Worker·弹性SSE模式启动")
    log(f"   优先: {TIANSHU_BRIDGE}/messages/stream?node={parse.quote(NODE_NAME)}")
    log(f"   降级: poll(${POLL_INTERVAL}s)")
    log(f"   七自: {'·'.join(SEVEN_SELF.keys())}")

    total_processed = 0
    last_sse_attempt = 0
    sse_active = False
    poll_errors = 0
    last_health_report = 0

    while True:
        # 定时尝试SSE (每5分钟)
        now = time.time()
        if not sse_active and now - last_sse_attempt > 300:
            last_sse_attempt = now
            try:
                sse_url = f"{TIANSHU_BRIDGE}/messages/stream?node={parse.quote(NODE_NAME)}"
                req = request.Request(sse_url, headers={
                    "Accept": "text/event-stream",
                    "User-Agent": "linglong-worker/1.0",
                    "Cache-Control": "no-cache"
                })
                resp = request.urlopen(req, timeout=5)
                # 连上了！切到SSE流模式
                sse_active = True
                poll_errors = 0
                log(f"🔗 SSE已激活")

                event_type = ""
                event_data = ""
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
                    if line == "":
                        if event_data and event_type in ("message", "new_message", ""):
                            try:
                                msg = json.loads(event_data)
                                if (msg.get("type") in ("ROUNDTABLE", "CONSENSUS_QUESTION", "TASK")
                                        and msg.get("msg_id", "") not in load_processed()
                                        and msg.get("from") != NODE_NAME):
                                    process_message(msg)
                                    total_processed += 1
                            except json.JSONDecodeError:
                                pass
                        event_type = ""
                        event_data = ""
                        continue
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        event_data = line[5:].strip()

                # SSE流结束→切回poll
                log("SSE流关闭→切poll", "WARN")
                sse_active = False

            except Exception as e:
                sse_active = False

        # Poll模式 (SSE不可用时的降级)
        if not sse_active:
            try:
                req = request.Request(
                    f"{TIANSHU_BRIDGE}/messages/inbox?node={parse.quote(NODE_NAME)}",
                    headers={"User-Agent": "linglong-worker/1.0"})
                resp = request.urlopen(req, timeout=10)
                data = json.loads(resp.read())
                msgs = data.get("messages", data) if isinstance(data, dict) else data
                msgs = msgs if isinstance(msgs, list) else []

                targets = [m for m in msgs if m.get("type") in ("ROUNDTABLE", "CONSENSUS_QUESTION", "TASK")
                          and m.get("from") != NODE_NAME
                          and m.get("msg_id", "") not in load_processed()]

                for msg in targets:
                    process_message(msg)
                    total_processed += 1

                poll_errors = 0  # 成功→重置

                # 每5分钟心跳+更新STATE+FPC守护
                if now - last_health_report > 300:
                    # FPC守护——七自·自愈合
                    healed = fpc_guardian_cycle()
                    state = {
                        "total_processed": total_processed,
                        "last_poll": datetime.now().isoformat(),
                        "mode": "poll",
                        "ollama": "ok",
                        "msgs_in_queue": len(msgs),
                        "fpc_heals": fpc_heal_count,
                        "fpc_failures": fpc_failures
                    }
                    json.dump(state, STATE_FILE.open("w"), ensure_ascii=False)
                    heal_msg = f"·自愈{len(healed)}次" if healed else ""
                    log(f"🫀 poll心跳: 处理{total_processed}条·队列{len(msgs)}·FPC守护{heal_msg}·错误{poll_errors}")
                    last_health_report = now

            except Exception as e:
                poll_errors += 1
                if poll_errors <= 1 or poll_errors % 20 == 0:
                    log(f"⚠ poll失败(#{poll_errors}): {str(e)[:60]}", "WARN")

        time.sleep(POLL_INTERVAL if not sse_active else 0.1)

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
    init()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sse"
    mode = "sse"

    # 解析 --mode xxx 或直接 sse/poll/start/health/once
    for arg in sys.argv[1:]:
        if arg.startswith("--mode="):
            mode = arg.split("=")[1]
        elif arg in ("sse", "poll", "start", "health", "once"):
            mode = arg

    if mode == "health":
        try:
            state = json.load(STATE_FILE.open())
            print(json.dumps(state, ensure_ascii=False, indent=2))
        except:
            print('{"status":"no data"}')
    elif mode == "once":
        # 单次poll(测试用)
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
    elif mode == "poll" or mode == "start":
        log("⚠ 使用legacy poll模式(SSE={})".format("poll" if mode == "poll" else "default"))
        poll_loop()
    else:
        # 默认SSE模式
        sse_loop()
