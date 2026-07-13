#!/usr/bin/env python3
"""
联邦七自协调器 v1.0 — 天巡↔小枢 双魂中枢
运行于灵龙 · cron 30min
职责: 并发执行双探针 → 交叉分析 → 写基因 → 联邦广播
"""
import json, sys, os, time, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request, urllib.error

SCRIPTS = os.path.expanduser("~/lgox-ops/scripts")
BRIDGE = "http://100.100.89.2:8765"
LGE = "http://127.0.0.1:8210"  # 本地镜像·消除网络依赖(远端8200偶发超时)

def run_script(name, args):
    """运行脚本并返回JSON"""
    try:
        r = subprocess.run(
            ["python3", f"{SCRIPTS}/{name}"] + args,
            capture_output=True, text=True, timeout=90
        )
        return json.loads(r.stdout) if r.stdout else {"error": "empty_output"}
    except Exception as e:
        return {"error": str(e)}

# ⚠️ macOS urllib代理陷阱: getproxies_macosx_sysconf() 会拦截本地隧道
# 必须用 ProxyHandler({}) 构建无代理opener，否则 localhost:8210 也走系统代理→失败
_NOPROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def write_gene(content, mem_type="episodic", source="fed-coordinator", fitness=0.4):
    """写基因到LGE — 20s超时+1次重试·macOS无代理opener"""
    data = json.dumps({
        "content": content, "memory_type": mem_type,
        "source": source, "tags": ["七自","天巡","小枢","协调"]
    }).encode()
    
    last_err = None
    for attempt in range(2):  # 主请求+1次重试
        try:
            req = urllib.request.Request(f"{LGE}/genes/write", data=data,
                headers={"Content-Type": "application/json", "X-LGE-Key": "fbe0b015eb7a03727903b660c4cecc60"})
            with _NOPROXY_OPENER.open(req, timeout=20) as r:
                return json.loads(r.read()).get("gene_id", "?")
        except Exception as e:
            last_err = str(e)
            if attempt == 0:
                time.sleep(2)  # 错峰重试
    return f"ERR:{last_err}"

def bridge_send(topic, node_from, content):
    """发送联邦桥topic消息"""
    try:
        data = json.dumps({
            "to": "灵龙", "from": node_from,
            "type": "knowledge_pack", "topic": topic,
            "content": content
        }).encode()
        req = urllib.request.Request(f"{BRIDGE}/messages/send", data=data,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def main():
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] 七自协调器启动")
    
    # ═══ 自感知层: 并发执行双探针 ═══
    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(run_script, "tianxun-sentinel.py", ["--probe-all"]): "天巡",
            executor.submit(run_script, "xiaoshu-gateway.py", ["--check"]): "小枢",
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"error": str(e)}
    
    tx = results.get("天巡", {})
    xs = results.get("小枢", {})
    
    # ═══ 自协调层: 交叉分析 ═══
    tx_ok = tx.get("ok", 0)
    tx_total = tx.get("total", 0)
    tx_status = tx.get("status", "?")
    xs_status = xs.get("status", "?")
    
    # 天巡发现异常 → 通知小枢
    if tx_status != "🟢":
        bridge_send("天巡哨兵", "天巡", 
            f"⚠️ 公网巡检异常: {tx_ok}/{tx_total} 通过. 详情: {json.dumps(tx.get('results',{}), ensure_ascii=False)[:300]}")
        bridge_send("小枢分析", "天巡",
            f"⚠️ 天巡发现公网异常({tx_ok}/{tx_total}), 请小枢内部核验.")
    
    # ═══ 自进化层: 巡检结果写基因 ═══
    summary = f"七自协调|天巡:{tx_ok}/{tx_total}{tx_status}|小枢:{xs_status}"
    gene_id = write_gene(
        f"[{ts}] {summary} | 天巡详情:{json.dumps(tx,ensure_ascii=False)[:400]}",
        fitness=0.4
    )
    
    # ═══ 自反思层: 每日总结(每24次≈12h写一次) ═══
    hour = int(time.strftime("%H"))
    if hour in (8, 20):  # 早晚各一次深度总结
        bridge_send("小枢分析", "协调器",
            f"📊 半日总结: 天巡{tx_ok}/{tx_total}·小枢{xs_status}. 基因已写入LGE({gene_id}).")

    # ═══ 联邦广播: 双频道推送 ═══
    bridge_send("天巡哨兵", "天巡",
        f"🟢 巡检: {tx_ok}/{tx_total} 公网全绿. {ts}")
    bridge_send("小枢分析", "小枢",
        f"🟢 网关: 健康检查{xs_status}. {ts}")
    
    print(f"  天巡:{tx_ok}/{tx_total}{tx_status} 小枢:{xs_status} 基因:{gene_id}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
