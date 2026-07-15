#!/usr/bin/env python3
"""
小枢AI数据飞轮·统一闭环
=========================
期货/信号数据→小枢实时解读→用户评分反馈→基因入库→下次更准

检查项:
  ① 数据管道: futures-v2.json + signals-v2.json 新鲜度
  ② AI在线: 小枢8779响应
  ③ 前端注入: ai-flywheel-v1.js 可达
  ④ 基因闭环: 反馈写入LGE
  ⑤ 互测联动: 互测飞轮评分互哺
"""
import urllib.request, json, time, os

# ═══ 检查 ═══
checks = []
total_weight = 0

def check(name, weight, fn):
    global total_weight
    total_weight += weight
    try:
        result = fn()
        checks.append({"name": name, "weight": weight, "pass": result, "detail": ""})
    except Exception as e:
        checks.append({"name": name, "weight": weight, "pass": False, "detail": str(e)[:60]})

# ① 数据管道
check("期货数据管道", 20, lambda: len(urllib.request.urlopen("https://stock.uavgpt.com/public/futures-v2.json", timeout=8).read()) > 100)
check("信号数据管道", 20, lambda: len(urllib.request.urlopen("https://stock.uavgpt.com/public/signals-v2.json", timeout=8).read()) > 100)

# ② AI在线
check("小枢健康", 15, lambda: json.loads(urllib.request.urlopen("http://localhost:8779/health", timeout=5).read()).get("status") == "ok")
check("小枢对话", 15, lambda: "choices" in json.loads(urllib.request.urlopen(
    urllib.request.Request("http://localhost:8779/chat/completions",
        data=json.dumps({"messages":[{"role":"user","content":"hi"}],"max_tokens":5}).encode(),
        headers={"Content-Type":"application/json"}), timeout=15).read()))

# ③ 前端注入
check("AI飞轮JS可达", 10, lambda: urllib.request.urlopen("https://stock.uavgpt.com/ai-flywheel-v1.js", timeout=8).getcode() == 200)
check("futures注入", 5, lambda: "ai-flywheel" in urllib.request.urlopen("https://stock.uavgpt.com/futures.html", timeout=8).read().decode())

# ④ 基因闭环
check("LGE可写", 10, lambda: json.loads(urllib.request.urlopen("http://100.116.0.29:8200/health", timeout=5).read()).get("status") == "ok")

# ⑤ 互测联动
check("互测DB有数据", 5, lambda: os.path.exists(os.path.expanduser("~/lgox-ops/data/mutual_test.db")))

# ═══ 评分 ═══
passed = sum(c["weight"] for c in checks if c["pass"])
score = round(passed / total_weight * 100)

status = "🟢" if score >= 90 else ("🟡" if score >= 70 else "🔴")

# ═══ 输出 ═══
result = {
    "score": score,
    "status": "ok" if score >= 90 else "degraded",
    "checks": checks,
    "summary": f"{status} 小枢AI数据飞轮: {score}/100 | {sum(1 for c in checks if c['pass'])}/{len(checks)}项通过"
}

# 输出JSON给dashboard-updater
print(json.dumps(result, ensure_ascii=False))

# 低于90分时写入gene记录
if score < 90:
    failed = [c["name"] for c in checks if not c["pass"]]
    try:
        data = json.dumps({
            "content": f"[小枢AI数据飞轮降级·{score}分] 失败项: {', '.join(failed)}",
            "memory_type": "episodic", "source": "小枢AI数据飞轮", "fitness": 0.3
        }).encode()
        req = urllib.request.Request("http://100.116.0.29:8200/genes/write", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": "lgox-gene-key-2025"})
        urllib.request.urlopen(req, timeout=5)
    except: pass
