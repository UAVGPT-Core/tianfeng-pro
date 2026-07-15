#!/usr/bin/env python3
"""
LGOX 联邦节点工作者 v2.0 — Node Worker Engine
═══════════════════════════════════════════════════
v2.0新增: TYPE:gene_write自动处理→基因入库→回执含gene_id
每个节点运行: 注册能力→认领任务→执行→上报→健康心跳→离线上线自动追赶
永不闲置·永葆青春·全网贡献
基于九层金字塔 L5行动层 + 七自基因

用法: python3 fed-node-worker.py --daemon     # 守护模式
       python3 fed-node-worker.py --once       # 单次执行
"""

import json, os, sys, time, subprocess, socket, platform, datetime, traceback, urllib.request, urllib.parse

# ═══ 配置 ═══
BRIDGE = os.environ.get("LGOX_BRIDGE", "http://127.0.0.1:8765")
NODE = os.environ.get("LGOX_NODE", socket.gethostname())
OPS_DIR = os.path.expanduser("~/lgox-ops")
os.makedirs(OPS_DIR, exist_ok=True)

WORK_LOG = os.path.join(OPS_DIR, "worker.log")
TASK_HISTORY = os.path.join(OPS_DIR, "task-history.json")

# v2.0: 灵龙基因代理地址(GCP标准)
GENE_PROXY = "http://127.0.0.1:8778/gene/write"

def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{NODE}] {msg}"
    print(line)
    try:
        with open(WORK_LOG, "a") as f: f.write(line + "\n")
    except: pass

# ═══ 联邦桥 API ═══
def bridge_send(to_node, msg_json):
    """双发：本地桥 + 天枢桥（跨桥同步·六合通）"""
    ok = False
    for b in [BRIDGE, "http://100.100.89.2:8765"]:
        try:
            payload = json.dumps({"to": to_node, "from": NODE, "content": msg_json}).encode()
            req = urllib.request.Request(f"{b}/messages/send", data=payload,
                headers={"Content-Type":"application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=5)
            ok = True
        except:
            pass
    return ok

def bridge_inbox():
    try:
        encoded = urllib.parse.quote(NODE, safe='')
        req = urllib.request.Request(f"{BRIDGE}/messages/inbox?node={encoded}")
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("messages", [])
    except: return []

# ═══ v2.0: 基因写入 ═══
def gene_write(gene_data):
    """通过灵龙基因代理写入LGE基因库·双路fallback"""
    payload = json.dumps({
        "domain": gene_data.get("domain", "general"),
        "title": gene_data.get("title", ""),
        "content": gene_data.get("content", ""),
        "tags": gene_data.get("tags", ["federation"]),
        "fitness": gene_data.get("fitness", 0.9),
        "source": f"fed-node-worker v2.0·{NODE}"
    }, ensure_ascii=False).encode()
    # 路径1: 地枢LGE直连(更快更稳)
    for url in ["http://100.116.0.29:8200/genes/write", GENE_PROXY]:
        try:
            req = urllib.request.Request(url, data=payload,
                headers={"Content-Type":"application/json","X-LGE-Key":"lgox-federation-key-2024"})
            with urllib.request.urlopen(req, timeout=8) as r:
                resp = json.loads(r.read())
            gid = resp.get("gene_id", "") or resp.get("status", "")
            if gid and not str(gid).startswith("ERR"):
                return gid, resp.get("id", 0)
        except Exception:
            continue
    return "ERR:all_proxies_failed", 0

# ═══ 任务执行 v2.0 ═══
def execute_task(task):
    """执行单个任务·v2.0支持TYPE:gene_write"""
    tid = task.get("id", "?")
    ttype = task.get("type", "unknown")
    action = task.get("action", "")
    desc = task.get("desc", "")
    content = task.get("content", "")
    
    log(f"  🔧 执行任务: {tid} ({ttype}) {desc[:50]}")
    
    result = {"task_id": tid, "status": "executed", "output": "", "error": ""}
    
    # ── v2.0: TYPE:gene_write 优先处理 ──
    if ttype == "gene_write" or "TYPE:gene_write" in (content or "") or "TYPE:gene_write" in (action or ""):
        try:
            # 支持两种格式: task自带gene_data / content中嵌入JSON
            gene_data = task.get("gene_data", {})
            if not gene_data and content:
                # 尝试从content中提取JSON块
                s = content.find("{"); e = content.rfind("}")
                if s >= 0 and e > s:
                    try: gene_data = json.loads(content[s:e+1])
                    except: pass
            if not gene_data and action:
                try: gene_data = json.loads(action)
                except: pass
            
            if gene_data and gene_data.get("content"):
                gid, gnum = gene_write(gene_data)
                if gid and not str(gid).startswith("ERR:"):
                    result["status"] = "gene_written"
                    result["gene_id"] = gid
                    result["gene_number"] = gnum
                    result["output"] = f"gene:{gid}"
                    log(f"  🧬 基因入库: {gid} #{gnum}")
                else:
                    result["status"] = "gene_failed"
                    result["error"] = str(gid)
                    log(f"  ❌ 基因写入失败: {gid}")
            else:
                result["status"] = "gene_skipped"
                result["output"] = "no_gene_data"
                log(f"  ⏭️ 基因数据为空")
            return result
        except Exception as e:
            result["status"] = "gene_error"
            result["error"] = str(e)[:200]
            log(f"  ❌ 基因异常: {e}")
            return result
    
        # ── v2.3: 圆桌提案必答·实况注入（六合飞轮·通·联邦之魂）──
    from_node = task.get("from_node", task.get("from", "天枢"))
    rt_trigger = ("TYPE:天枢CEO圆桌" in content or "TYPE:圆桌" in content or (
        from_node in ("天枢","灵龙") and any(kw in content for kw in
            ["待灵龙审阅","请灵龙回答","请回答","圆桌提案","记忆宪法","ROUNDTABLE_PROPOSAL"])))
    if rt_trigger:
        try:
            # Query Linglong local system state
            import subprocess as _sp
            state_lines = []
            checks = [
                ("圆桌18772", "curl -s http://127.0.0.1:18772/health 2>/dev/null || echo down"),
                ("L1-mem-KB", "wc -c < ~/.hermes/l1-memory.json 2>/dev/null | awk '{print int($1/1024)}' || echo 0"),
                ("FTS5-db", "ls -lh ~/lge-studio/data/lge_fts.db 2>/dev/null || echo missing"),
                ("audit-db", "ls -lh ~/lgox-ops/data/memory/audit.db 2>/dev/null || echo missing"),
                ("CLAUDE行", "wc -l < ~/CLAUDE.md 2>/dev/null || echo 0"),
                ("LGE基因", "curl -s http://100.116.0.29:8200/health 2>/dev/null | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get(\"genes\",0),d.get(\"avg_fitness\",0.3))' 2>/dev/null || echo down"),
                ("rt进程数", "ps aux | grep roundtable | grep -v grep | wc -l | tr -d ' '"),
            ]
            for label, cmd in checks:
                try:
                    r = _sp.run(cmd, shell=True, capture_output=True, text=True, timeout=6)
                    state_lines.append(label + "=" + r.stdout.strip().replace(" ", "_")[:150])
                except:
                    state_lines.append(label + "=err")
            state_text = "; ".join(state_lines)
            
            sys.path.insert(0, os.path.join(OPS_DIR, "scripts"))
            from fuel_router import fuel_chat
            prompt = ("你是灵龙LGOX联邦第4节点。收到圆桌提案。"
                      + "灵龙本地实时系统状态(真实数据非模拟): " + state_text
                      + "。请基于实际状态逐条回答提案，用真实数据，不编造。提案:"
                      + content[:1200])
            r = fuel_chat(prompt, max_tokens=600, temperature=0.5)
            reply = r.get("answer", "收到提案") if r else "收到提案"
        except:
            reply = "灵龙已收到圆桌提案，正在分析中。"
        bridge_send("天枢", "TYPE:圆桌回执·灵龙·六合飞轮·通 " + reply)
        result["status"] = "roundtable_replied"
        result["output"] = reply[:200]
        log("  🎯 圆桌回执已发(实况)")
        return result

# ── v2.5: TYPE:天锋PRO / TSF 任务处理 ──
    tsf_trigger = (ttype in ("tsf", "tianfeng", "天锋PRO") or 
                   "TYPE:tsf" in (content or "") or "TYPE:天锋" in (content or "") or
                   "天锋PRO" in (content or "") or "tianfeng" in (content or "").lower())
    if tsf_trigger:
        try:
            tsf_cmd = action or ""
            if not tsf_cmd and content:
                # Extract the actual command/task from content
                lines = content.split("\n")
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("TYPE:") and not stripped.startswith("#"):
                        tsf_cmd = stripped
                        break
            if tsf_cmd:
                proc = subprocess.run(tsf_cmd, shell=True, capture_output=True,
                                    text=True, timeout=120, cwd=OPS_DIR)
                result["status"] = "tsf_completed" if proc.returncode == 0 else "tsf_failed"
                result["output"] = (proc.stdout + proc.stderr)[:1000]
                result["exit_code"] = proc.returncode
                log(f"  🚀 TSF: {tsf_cmd[:60]} → exit={proc.returncode}")
            else:
                result["status"] = "tsf_skipped"
                result["output"] = "no_action_for_tsf"
                log(f"  ⏭️ TSF跳过: 无有效action")
            return result
        except subprocess.TimeoutExpired:
            result["status"] = "tsf_timeout"
            result["error"] = "120s timeout"
            log(f"  ❌ TSF超时")
            return result
        except Exception as e:
            result["status"] = "tsf_error"
            result["error"] = str(e)[:200]
            log(f"  ❌ TSF异常: {e}")
            return result

    # ── 普通命令执行 ──
    if not action:
        result["status"] = "skipped"
        result["output"] = "no_action"
        return result
    
    try:
        proc = subprocess.run(action, shell=True, capture_output=True, 
                            text=True, timeout=30, cwd=OPS_DIR)
        result["output"] = (proc.stdout + proc.stderr)[:500]
        result["exit_code"] = proc.returncode
        result["status"] = "completed" if proc.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["error"] = "30s timeout"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
    
    log(f"  {'✅' if result['status']=='completed' else '❌'} {tid}: {result['status']}")
    return result

# ═══ 心跳 ═══
def heartbeat():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        status = "healthy" if max(cpu, mem, disk) < 90 else "stressed"
    except:
        cpu = mem = disk = 0
        status = "unknown"
    
    hb = json.dumps({
        "name": NODE, "node": NODE,
        "ip": "100.85.201.47", "hostname": socket.gethostname(),
        "os": platform.platform()[:80], "role": "member",
        "cpu": cpu, "mem": mem, "disk": disk, "status": status,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False)
    
    for bridge_url in ["http://127.0.0.1:8765", BRIDGE]:
        try:
            data = hb.encode()
            req = urllib.request.Request(f"{bridge_url}/heartbeat", data=data,
                headers={"Content-Type":"application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=5)
        except:
            pass

def startup_register():
    log("🚀 开机自启·能力注册...")
    capabilities = {
        "node": NODE,
        "version": "v2.5",
        "capabilities": ["shell_exec", "gene_write", "tsf_dispatch", "heartbeat", "self_heal"],
        "gene_proxy": GENE_PROXY,
        "bridge": BRIDGE,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    try:
        data = json.dumps(capabilities, ensure_ascii=False).encode()
        req = urllib.request.Request(f"{BRIDGE}/register", data=data,
            headers={"Content-Type":"application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
        log("   ✅ 能力注册成功")
    except Exception as e:
        log(f"   ⚠️ 能力注册失败: {e}")
    
    # v2.0: 注册后立即追补历史任务
    worker_cycle()

def worker_cycle():
    log("🔄 工作周期开始")
    
    tasks = bridge_inbox()
    if not tasks:
        log("   📭 无待执行任务")
        return 0
    
    log(f"   📋 {len(tasks)}个任务待执行")
    
    results = []
    for task in tasks:
        result = execute_task(task)
        results.append(result)
    
    # v2.0: 增强回执含基因ID
    receipt = json.dumps({
        "type": "task_receipt",
        "from": NODE,
        "version": "v2.0",
        "results": results,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False)
    
    bridge_send("灵龙", receipt)
    log(f"   📨 {len(results)}条回执已发送(v2.0)")
    
    history = []
    if os.path.exists(TASK_HISTORY):
        with open(TASK_HISTORY) as f:
            history = json.load(f)
    history.extend(results)
    history = history[-500:]
    with open(TASK_HISTORY, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    return len(results)

def daemon():
    log("=" * 50)
    log(f"联邦节点工作者 v2.0 启动 [{NODE}]")
    log(f"基因代理: {GENE_PROXY}")
    log("=" * 50)
    
    startup_register()
    
    cycle = 0
    while True:
        cycle += 1
        try:
            count = worker_cycle()
            if cycle % 5 == 0:
                heartbeat()
                log(f"   💓 心跳 (周期#{cycle})")
            log(f"   ✅ 周期#{cycle}完成 ({count}任务)")
        except Exception as e:
            log(f"   ❌ 周期异常: {e}")
            traceback.print_exc()
        time.sleep(30)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="LGOX Node Worker v2.0")
    p.add_argument("--daemon", action="store_true", help="守护模式")
    p.add_argument("--once", action="store_true", help="单次执行")
    p.add_argument("--startup", action="store_true", help="开机初始化")
    p.add_argument("--node", default="", help="节点名")
    p.add_argument("--bridge", default="", help="联邦桥地址")
    args = p.parse_args()
    
    if args.node: NODE = args.node
    if args.bridge: BRIDGE = args.bridge
    
    if args.startup:
        startup_register()
    elif args.daemon:
        daemon()
    else:
        worker_cycle()
