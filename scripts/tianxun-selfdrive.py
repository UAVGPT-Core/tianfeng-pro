#!/usr/bin/env python3
"""
天巡永动自驱飞轮 v1.0 — LGOX联邦第10节点·七自活体引擎
每5分钟自检→愈合→进化→汇报→纳基因
部署: 灵龙 cron | 零API费(纯本地检测)
"""
import urllib.request, json, time, sys, subprocess, os

HEALTH_URL = "http://localhost:8778/health"
BRIDGE_URL = "http://localhost:8765/health"
LGE_URL = "http://100.116.0.29:8200/health"
LGE_WRITE = "http://100.116.0.29:8200/genes/write"
REPORT_FILE = os.path.expanduser("~/lgox-ops/logs/tianxun-selfdrive.log")

def check(url, name, timeout=5):
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return {"ok": True, "data": str(r.read()[:200])}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}

def write_gene(content, gene_type="episodic"):
    try:
        data = json.dumps({
            "content": content, "memory_type": gene_type,
            "source": "天巡自驱飞轮", "fitness": 0.5
        }).encode()
        req = urllib.request.Request(LGE_WRITE, data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": "lgox-federation-key-2024"})
        r = urllib.request.urlopen(req, timeout=8)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)[:100]}

# ═══ 主检测 ═══
now = time.strftime("%Y-%m-%d %H:%M:%S")
results = {}

# ① 自感知 — 健康自检
results["tianxun"] = check(HEALTH_URL, "天巡")
results["bridge"] = check(BRIDGE_URL, "联邦桥")
results["lge"] = check(LGE_URL, "LGE基因库")

# ② 诊断
issues = []
if not results["tianxun"]["ok"]:
    issues.append("天巡:8778不可达")
if not results["bridge"]["ok"]:
    issues.append("联邦桥:8765不可达")
if not results["lge"]["ok"]:
    issues.append("LGE地枢不可达")

# ③ 自愈合 — 如果挂了尝试重启
if not results["tianxun"]["ok"]:
    try:
        subprocess.run(["launchctl", "start", "com.lgox.tianxun-ai"], timeout=10)
        issues.append("🩹 已尝试重启天巡")
    except:
        issues.append("❌ 重启天巡失败")

# ④ 状态汇总
status_line = f"[{now}] 天巡自驱: 天巡={'🟢' if results['tianxun']['ok'] else '🔴'} 桥={'🟢' if results['bridge']['ok'] else '🔴'} LGE={'🟢' if results['lge']['ok'] else '🔴'}"
if issues:
    status_line += f" | 问题:{';'.join(issues)}"

# ⑤ 纳基因 — 异常写入LGE永久免疫
if issues:
    gene_content = f"[天巡自驱·{now}] 异常:{';'.join(issues)} | 天巡={results['tianxun']} | 桥={results['bridge']} | LGE={results['lge']}"
    write_gene(gene_content)

# ⑥ 输出
print(status_line)
with open(REPORT_FILE, 'a') as f:
    f.write(status_line + "\n")

# ⑦ 只有异常时才非零退出（触发告警）
sys.exit(1 if issues else 0)
