#!/usr/bin/env python3
"""
小枢↔天巡 轮测引擎 v1.0 · 100回合互测 · 自治自愈 · 全闭环
部署: 灵龙 | 频率: cron每10分钟 | 每轮互问互答互评
"""
import json, os, time, urllib.request, sys

TX_URL = "http://127.0.0.1:8778/chat"
XS_URL = "http://127.0.0.1:8779/chat"
TX_HEALTH = "http://127.0.0.1:8778/health"
XS_HEALTH = "http://127.0.0.1:8779/health"
TX_EVOLVE = "http://127.0.0.1:8778/evolve/auto"
XS_EVOLVE = "http://127.0.0.1:8779/evolve/auto"
LGE_WRITE = "http://100.116.0.29:8200/genes/write"
LGE_KEY = "lgox-federation-key-2024"
LOG_FILE = "/tmp/tx-xs-roundtest.log"
STATE_FILE = "/tmp/tx-xs-roundtest-state.json"
MAX_ROUNDS = 100

# ═══ 互问题库（覆盖各自领域） ═══
TX_QUESTIONS = [
    "DJI M350飞控初始化时红灯快闪3次，怎么排查？",
    "Cloudflare Tunnel 525错误怎么定位？",
    "nginx反向代理超时60秒，调什么参数？",
    "联邦桥8765端口不通，诊断步骤？",
    "无人机机巢如何部署EdgeAI推理？",
    "低空经济航线审批流程是什么？",
    "Docker容器启动后立即退出怎么看日志？",
    "Tailscale组网两台机器ping不通怎么办？",
    "FastAPI异步端点阻塞怎么排查？",
    "七自基因的'自约束'具体怎么实现？",
]

XS_QUESTIONS = [
    "今天A股大盘上证指数走势怎么看？",
    "茅台600519当前技术形态分析？",
    "北向资金连续3天净流出意味着什么？",
    "MACD金叉但成交量萎缩怎么解读？",
    "创业板和科创板哪个板块更有机会？",
    "涨停板打开后又封回去是什么信号？",
    "龙虎榜机构专用席位买入需要跟吗？",
    "布林带收窄后通常怎么走？",
    "量化选股因子如何配置权重？",
    "美联储加息对A股的影响路径？",
]

# ═══ 工具函数 ═══
def post(url, data, timeout=30):
    payload = json.dumps(data).encode()
    req = urllib.request.Request(url, data=payload,
        headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def get(url, timeout=5):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def log(msg):
    ts = time.strftime("%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"round": 0, "tx_wins": 0, "xs_wins": 0, "heals": 0, "errors": 0}

def save_state(st):
    with open(STATE_FILE, "w") as f:
        json.dump(st, f)

# ═══ 自愈 ═══
def heal(service, port):
    """重启挂掉的服务"""
    import subprocess
    log(f"🩹 自愈: {service}(:{port}) 无响应, 强制重启...")
    subprocess.run(["launchctl", "unload", f"/Users/a112233/Library/LaunchAgents/com.lgox.{service}-ai.plist"],
                   capture_output=True)
    subprocess.run(["kill", "-9"] + 
                   subprocess.run(["lsof","-ti",f":{port}"], capture_output=True, text=True).stdout.strip().split(),
                   capture_output=True)
    time.sleep(2)
    subprocess.run(["launchctl", "load", f"/Users/a112233/Library/LaunchAgents/com.lgox.{service}-ai.plist"],
                   capture_output=True)
    time.sleep(5)

def check_and_heal():
    """检查双节点健康, 挂了自愈"""
    healed = False
    for name, url, port in [("tianxun", TX_HEALTH, 8778), ("xiaoshu", XS_HEALTH, 8779)]:
        try:
            r = get(url, timeout=15)
            gn = r.get("gene_count", "?")
            log(f"  {name}健康: {gn}")
        except Exception as e:
            log(f"  🔴 {name}不响应: {e}")
            heal(name, port)
            healed = True
    return healed

# ═══ 互问互答 ═══
def cross_ask(asker, asker_url, answerer, question, idx):
    """asker问answerer一个问题"""
    try:
        resp = post(asker_url, {"question": question}, timeout=30)
        answer = resp.get("answer", "")
        evidence = resp.get("evidence_count", 0)
        tokens = resp.get("tokens", 0)
        latency = resp.get("latency_ms", 0)
        
        # 质量评分
        score = 50
        if len(answer) > 100: score += 15
        if len(answer) > 300: score += 10
        if evidence > 0: score += 15
        if latency < 3000: score += 10
        
        # 身份检查
        if answerer == "天巡":
            if "小枢" in answer[:100] and "天巡" not in answer[:100]:
                score -= 30
                log(f"  ⚠️ 天巡身份漂移! 说了'小枢'")
        if answerer == "小枢":
            if "天巡" in answer[:100] and "小枢" not in answer[:100]:
                score -= 30
                log(f"  ⚠️ 小枢身份漂移! 说了'天巡'")
        
        score = max(0, min(100, score))
        fitness = score / 100
        
        log(f"  [{answerer}] 评分{score} | 证据{evidence}条 | {tokens}token | {latency}ms")
        
        # 自进化
        try:
            post(f"http://127.0.0.1:{8778 if answerer=='天巡' else 8779}/evolve/auto",
                 {"question": question, "answer": answer[:200], "evidence_count": evidence},
                 timeout=8)
        except:
            pass
        
        return {"score": score, "fitness": fitness, "answer": answer[:100], "evidence": evidence}
    except Exception as e:
        log(f"  🔴 {asker}→{answerer} 失败: {e}")
        return {"score": 0, "fitness": 0, "answer": "", "evidence": 0, "error": str(e)[:80]}

# ═══ 主循环 ═══
def main():
    st = load_state()
    round_num = st["round"] + 1
    
    if round_num > MAX_ROUNDS:
        log(f"✅ 已完成{MAX_ROUNDS}回合! 重置计数器")
        round_num = 1
        st = {"round": 0, "tx_wins": 0, "xs_wins": 0, "heals": 0, "errors": 0}
    
    log(f"══════ 第{round_num}/{MAX_ROUNDS}回合 ══════")
    
    # 健康检查 + 自愈
    healed = check_and_heal()
    if healed:
        st["heals"] += 1
    
    # 选问题
    tx_q = TX_QUESTIONS[(round_num - 1) % len(TX_QUESTIONS)]
    xs_q = XS_QUESTIONS[(round_num - 1) % len(XS_QUESTIONS)]
    
    # 天巡考小枢（天巡问技术问题考小枢）
    log(f"🔵 天巡→小枢: {tx_q[:40]}...")
    r1 = cross_ask("天巡", TX_URL, "小枢", tx_q, round_num)
    
    # 小枢考天巡（小枢问金融问题考天巡）
    log(f"🟣 小枢→天巡: {xs_q[:40]}...")
    r2 = cross_ask("小枢", XS_URL, "天巡", xs_q, round_num)
    
    # 计分
    tx_score = r2.get("score", 0)  # 天巡回答金融问题的得分
    xs_score = r1.get("score", 0)  # 小枢回答技术问题的得分
    
    if tx_score > xs_score: st["tx_wins"] += 1
    elif xs_score > tx_score: st["xs_wins"] += 1
    
    if r1.get("error") or r2.get("error"):
        st["errors"] += 1
    
    st["round"] = round_num
    st["last_tx_score"] = tx_score
    st["last_xs_score"] = xs_score
    save_state(st)
    
    # 写基因
    try:
        gene_content = f"[轮测#{round_num}] 天巡{tx_score}分 vs 小枢{xs_score}分 | 自愈{st['heals']}次 | 回合{st['round']}"
        post(LGE_WRITE, {
            "content": gene_content,
            "memory_type": "semantic",
            "source": "roundtest",
            "fitness": max(tx_score, xs_score) / 100
        }, timeout=8)
        log(f"🧬 基因已写入")
    except Exception as e:
        log(f"⚠️ 基因写入失败: {e}")
    
    total = st["round"]
    log(f"══════ 累计: {total}回合 | 天巡{st['tx_wins']}胜/小枢{st['xs_wins']}胜 | 自愈{st['heals']}次 | 错误{st['errors']}次 ══════")

if __name__ == "__main__":
    main()
