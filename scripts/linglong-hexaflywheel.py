#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║  灵龙六合飞轮 v2.0 — 桥积压自愈 + 全闭环                ║
║  通→处理→执→馈→审→基因·零依赖天枢consumer               ║
║  AI灯塔·AI坐标·七自永动                                 ║
╚══════════════════════════════════════════════════════════╝

运行: python3 linglong-hexaflywheel.py [--once|--daemon|--status]
  --once   单次消费(手动/cron)
  --daemon 常驻守护(每30秒一轮)
  --status 查看积压状态
"""

import json, os, sys, time, sqlite3, subprocess
from pathlib import Path
from datetime import datetime
import urllib.request as ureq

# ═══ 配置 ═══════════════════════════════════════
BRIDGE_URL = "http://100.100.89.2:8765"
NODE_NAME = "linglong"
LOCAL_OLLAMA = "http://localhost:11434"
LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"
DATA_DIR = Path.home() / "lgox-ops" / "data" / "hexaflywheel"
MAX_BATCH = 15  # 每轮最多处理15条

# ═══ 工具 ═══════════════════════════════════════

def log(msg: str):
    ts = datetime.now().strftime("%m%d-%H%M%S")
    print(f"[{ts}] {msg}", flush=True)


def bridge_get(path: str, timeout=8):
    """读联邦桥"""
    try:
        req = ureq.Request(f"{BRIDGE_URL}{path}")
        resp = ureq.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except Exception as e:
        log(f"桥读失败: {e}")
        return None


def bridge_post(path: str, data: dict, timeout=8):
    """写联邦桥"""
    try:
        payload = json.dumps(data).encode()
        req = ureq.Request(f"{BRIDGE_URL}{path}", data=payload,
            headers={"Content-Type": "application/json"})
        resp = ureq.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except Exception as e:
        log(f"桥写失败: {e}")
        return None


def local_infer(prompt: str, max_tokens=150) -> str:
    """灵龙本地Ollama推理(零成本零延迟)"""
    try:
        data = json.dumps({
            "model": "qwen3:8b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": max_tokens}
        }).encode()
        req = ureq.Request(f"{LOCAL_OLLAMA}/api/chat", data=data,
            headers={"Content-Type": "application/json"})
        resp = ureq.urlopen(req, timeout=30)
        return json.loads(resp.read()).get("message", {}).get("content", "")
    except:
        return ""


def write_gene(content: str, fitness=0.5, memtype="episodic"):
    """写基因到地枢LGE"""
    try:
        gene = {
            "content": content,
            "memory_type": memtype,
            "source": f"灵龙六合飞轮/自愈闭环/{datetime.now().strftime('%m%d%H%M')}",
            "fitness_score": fitness
        }
        data = json.dumps(gene).encode()
        req = ureq.Request(f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
        ureq.urlopen(req, timeout=8)
        return True
    except:
        return False


# ═══ 核心: 消息处理引擎 ═══════════════════════

def classify_message(msg: dict) -> str:
    """智能分类→决定处理策略"""
    mtype = msg.get("type", "").upper()
    content = msg.get("content", "")
    sender = msg.get("from", "")

    # 圆桌/讨论→本地推理回复
    if mtype in ("ROUNDTABLE", "DISCUSSION", "CONSENSUS"):
        return "DISCUSS"

    # 任务指令→执行
    if mtype in ("TASK", "COMMAND", "EXECUTE"):
        return "EXEC"

    # 反馈/确认→审计
    if mtype in ("FEEDBACK", "ACK", "REPLY"):
        return "AUDIT"

    # 信息通知→记录
    return "LOG"


def process_discussion(msg: dict) -> dict:
    """处理圆桌讨论→本地推理→回复"""
    topic = msg.get("topic", msg.get("content", "")[:80])
    sender = msg.get("from", "unknown")
    msg_id = msg.get("msg_id", "?")

    prompt = (
        f"你是灵龙·LGOX联邦Worker节点。收到来自{sender}的联邦桥消息。\n"
        f"主题:{topic[:200]}\n"
        f"内容:{msg.get('content','')[:500]}\n\n"
        f"请简洁回复(30-80字):确认收到+表态(同意/部分同意/需讨论)+关键建议。"
    )
    reply = local_infer(prompt, 100)

    if reply:
        return bridge_post("/messages/send", {
            "to": sender,
            "from": NODE_NAME,
            "type": "REPLY",
            "priority": "P2",
            "msg_id": f"ll-reply-{msg_id}",
            "content": f"[灵龙auto-reply] {reply}",
            "ref_msg_id": msg_id
        }) or {}
    return {}


def process_exec(msg: dict) -> dict:
    """处理执行指令→本地执行→反馈结果"""
    content = msg.get("content", "")
    sender = msg.get("from", "")
    msg_id = msg.get("msg_id", "?")

    # 安全执行——仅允许白名单命令
    result = "指令已收到·灵龙Worker评估中"
    try:
        # 简单shell执行(白名单限制)
        if "status" in content.lower() or "健康" in content or "check" in content.lower():
            r = subprocess.run("uptime; echo '---'; df -h / | tail -1", 
                shell=True, capture_output=True, text=True, timeout=10)
            result = f"灵龙健康:\n{r.stdout[:300]}"
    except:
        pass

    return bridge_post("/messages/send", {
        "to": sender, "from": NODE_NAME, "type": "ACK_EXEC",
        "priority": "P2", "msg_id": f"ll-exec-{msg_id}",
        "content": result, "ref_msg_id": msg_id
    }) or {}


def process_audit(msg: dict):
    """审计消息→提取基因"""
    content = msg.get("content", "")[:300]
    sender = msg.get("from", "?")

    # 自动纳基因
    gene_content = f"[灵龙审计·{sender}] {content[:200]}"
    write_gene(gene_content, fitness=0.45, memtype="episodic")


def process_message(msg: dict) -> str:
    """处理单条消息·返回action"""
    action = classify_message(msg)
    sender = msg.get("from", "?")
    msg_id = msg.get("msg_id", "?")

    if action == "DISCUSS":
        process_discussion(msg)
        return "DISCUSS→REPLY"

    elif action == "EXEC":
        process_exec(msg)
        return "EXEC→ACK"

    elif action == "AUDIT":
        process_audit(msg)
        return "AUDIT→GENE"

    else:
        # LOG级别也纳基因(知识沉淀)
        content = msg.get("content", "")[:200]
        if len(content) > 20:
            write_gene(f"[灵龙收悉·{sender}] {content}", fitness=0.35)
        return "LOG"


# ═══ 主循环 ═══════════════════════════════════

def consume_backlog():
    """消费桥积压→六合全闭环"""
    log("═══ 六合飞轮:通→处理→执→馈→审→基因 ═══")

    # ① 通(Connect)——拉积压
    status = bridge_get("/messages/health")
    if not status:
        log("❌ 桥不可达·中断")
        return

    total = status.get("total_unread", 0)
    linglong_unread = status.get("per_node", {}).get("灵龙", 0)
    log(f"①通: 总积压{total}条·灵龙{linglong_unread}条")

    if total == 0 and linglong_unread == 0:
        log("✅ 无积压·跳过")
        # 自检心跳
        bridge_post("/messages/send", {
            "to": "tianshu", "from": NODE_NAME, "type": "HEARTBEAT",
            "priority": "P3",
            "content": f"灵龙六合飞轮心跳·{datetime.now().strftime('%m%d%H%M')}·积压0"
        })
        return

    # ② 处理(Process)——拉取消息
    # 先消费灵龙专属→再消费全局
    messages = []
    for target in [NODE_NAME, "all"]:
        try:
            inbox = bridge_get(f"/messages/inbox?node={target}&limit={MAX_BATCH}")
            if inbox:
                msgs = inbox if isinstance(inbox, list) else inbox.get("messages", [])
                messages.extend(msgs)
        except:
            pass

    if not messages:
        log("②处理: 无可消费消息·但积压>0→可能已在消费中")
        return

    log(f"②处理: 拉取{len(messages)}条")

    # ③④⑤⑥ 执行·反馈·审计·基因
    actions = {"DISCUSS→REPLY": 0, "EXEC→ACK": 0, "AUDIT→GENE": 0, "LOG": 0}
    gene_count = 0

    for msg in messages:
        act = process_message(msg)
        actions[act] = actions.get(act, 0) + 1

        # 每次讨论都纳基因
        if act == "DISCUSS→REPLY":
            content = msg.get("content", "")[:300]
            gene_count += write_gene(
                f"[灵龙六合·圆桌] {msg.get('from','?')}: {content}",
                fitness=0.50
            )

    # 汇总基因
    summary_gene = (
        f"灵龙六合飞轮·{datetime.now().strftime('%m%d%H%M')}·"
        f"消费{len(messages)}条·积压{total}→{total-len(messages)}·"
        f"回复{actions['DISCUSS→REPLY']}条·纳基因{gene_count}条"
    )
    write_gene(summary_gene, fitness=0.55)

    log(f"③执④馈⑤审: {actions}")
    log(f"⑥基因: {gene_count}条·{summary_gene[:100]}")

    # 自述——发送处理报告
    bridge_post("/messages/send", {
        "to": "tianshu", "from": NODE_NAME, "type": "REPORT",
        "priority": "P2",
        "content": f"[灵龙六合飞轮报告] {summary_gene}"
    })

    log(f"✅ 六合闭环完成·积压{total}→{max(0,total-len(messages))}")


def daemon_mode():
    """守护模式·每30秒一轮"""
    log("灵龙六合飞轮守护启动·每30s一轮")
    while True:
        try:
            consume_backlog()
        except Exception as e:
            log(f"异常: {e}")
        time.sleep(30)


def status_mode():
    """查看状态"""
    status = bridge_get("/messages/health")
    if status:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print("桥不可达")


# ═══ 入口 ═══════════════════════════════════

if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    arg = sys.argv[1] if len(sys.argv) > 1 else "--once"

    if arg == "--daemon":
        daemon_mode()
    elif arg == "--status":
        status_mode()
    else:  # --once
        consume_backlog()
