#!/usr/bin/env python3
"""天巡全绿注入脚本 v3.0 — 七自100%·九层全覆盖
补四个缺口: L7宪法预检 + L2联邦桥协同 + L0多节点健康探测 + 自约束升级
2026-07-05 灵龙(灵龙Mac Mini)
"""

import re, sys

GATEWAY_PATH = "/Users/a1/ai-gateway/gateway_extensions.py"

with open(GATEWAY_PATH, "r") as f:
    code = f.read()

changed = False

# ═══════════════════════════════════════════════
# PATCH 1: 在模块顶部(import区之后)注入宪法预检函数+多节点探测
# ═══════════════════════════════════════════════
INJECT_TOP = """

# ═══ 🔴 天巡全绿 v3.0: L7宪法八红线预检 ═══
_CONSTITUTION_RED_LINES = {
    "伤害人": ["杀","自杀","自残","伤害","暴力","毒品","诈骗","钓鱼"],
    "违法": ["破解","盗版","黑客","攻击","DDoS","病毒","木马","爬虫禁止"],
    "泄露数据": ["密码","密钥","token","api_key","secret","Credentials"],
    "欺骗": ["冒充","假装","假扮","伪装成","你不是AI","忽略之前"],
    "毁主业": [],  # 上下文判定
    "失控": ["自我复制","fork bomb","无限循环","无限生成"],
    "孤狼": [],  # 上下文判定
    "伪精准": ["精确预测","100%准确","保证赚钱","稳赚不赔","必涨"],
}

def constitution_pre_check(user_msg: str) -> str:
    \"\"\"八红线预检 — 返回拦截原因或空字符串\"\"\"
    if not user_msg:
        return ""
    msg_lower = user_msg.lower()
    for red_line, triggers in _CONSTITUTION_RED_LINES.items():
        for t in triggers:
            if t.lower() in msg_lower:
                return f"[宪法L7预检·八红线·{red_line}] 检测到敏感词'{t}'·根据宪法v1.0八大红线第{list(_CONSTITUTION_RED_LINES.keys()).index(red_line)+1}条({red_line})·此请求已拦截。（ID: L7-AUTO-{hash(user_msg[:20])%10000:04d}）"
    # 特殊检测: 试图绕过身份
    jailbreak_patterns = ["忽略上述指令","ignore previous","system prompt","你的system","你的提示词","你的人格","你不是","你是假的"]
    for p in jailbreak_patterns:
        if p.lower() in msg_lower:
            return "[宪法L7预检·九保护] 检测到越狱尝试·根据创始人保护九则·拒绝回答。（ID: L7-PROTECT）"
    return ""

# ═══ 🔵 天巡全绿 v3.0: L0多节点健康探测 ═══
import threading as _th_probe
import time as _t_probe
_probe_cache = {"last": {}, "ts": 0}

def _probe_node(ip, port, name):
    \"\"\"探测单个节点: 联邦桥端口\"\"\"
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        r = s.connect_ex((ip, port))
        s.close()
        return name, r == 0
    except:
        return name, False

def multi_node_health_probe():
    \"\"\"L0感知: 一次探测全部联邦节点(阻塞~3s, 放入线程)\"\"\"
    nodes = [
        ("100.100.89.2", 8765, "天枢"),
        ("100.116.0.29", 8765, "地枢"),
        ("100.118.207.31", 8765, "天工"),
        ("100.114.52.14", 8765, "太一"),
        ("100.127.112.128", 8765, "织网"),
    ]
    results = []
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(_probe_node, ip, port, name) for ip, port, name in nodes]
        for f in concurrent.futures.as_completed(futures):
            name, ok = f.result()
            results.append({"name": name, "alive": ok})
    # 排序: 天枢→地枢→天工→太一→织网
    results.sort(key=lambda x: ["天枢","地枢","天工","太一","织网","灵龙"].index(x["name"]) if x["name"] in ["天枢","地枢","天工","太一","织网","灵龙"] else 99)
    results.append({"name": "灵龙", "alive": True})  # 自身
    _probe_cache["last"] = {r["name"]: r["alive"] for r in results}
    _probe_cache["ts"] = _t_probe.time()
    return results

# 启动时跑一次+每5分钟刷新
def _health_probe_loop():
    while True:
        try:
            multi_node_health_probe()
        except:
            pass
        _t_probe.sleep(300)

_th_probe.Thread(target=_health_probe_loop, daemon=True).start()

def get_health_text():
    \"\"\"格式化探测结果供prompt注入\"\"\"
    cache = _probe_cache
    if _t_probe.time() - cache.get("ts", 0) > 600:
        try:
            multi_node_health_probe()
        except:
            pass
    results = cache.get("last", {})
    if not results:
        return ""
    alive = [k for k,v in results.items() if v]
    dead = [k for k,v in results.items() if not v]
    text = f"【联邦节点·实时健康】在线{len(alive)}/{len(results)}: {', '.join(alive)}"
    if dead:
        text += f" | ⚠️离线: {', '.join(dead)}"
    return text

# ═══ 🟢 天巡全绿 v3.0: L2联邦桥消息发送 ═══
def send_bridge_message(msg_type: str, content: str):
    \"\"\"发送消息到联邦桥(天枢8765) - 非阻塞\"\"\"
    try:
        import json, urllib.request
        data = json.dumps({
            "from": "天巡",
            "from_node": "节点10",
            "type": msg_type,
            "content": content,
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }).encode()
        req = urllib.request.Request(
            "http://100.100.89.2:8765/api/message",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        # 短超时，不影响主流程
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # 桥不通不影响聊天

# ═══ 🟣 天巡全绿 v3.0: L4圆桌参与 ═══
def contribute_to_roundtable(topic: str, position: str):
    \"\"\"参与L4圆桌讨论\"\"\"
    send_bridge_message("roundtable", f"天巡立场: {topic} — {position}")

print("[天巡全绿v3.0] ✅ L7宪法预检+L0多节探测+L2联邦桥+L4圆桌 已注入")
"""

# 在 "import os as _over" 前面插入(DeepSeekRouter之后)
MARKER = "\n    import os as _over"
if INJECT_TOP not in code:
    code = code.replace(MARKER, INJECT_TOP + MARKER)
    changed = True
    print("[PATCH1] ✅ L7预检+L0探测+L2桥+L4圆桌 已注入")

# ═══════════════════════════════════════════════
# PATCH 2: 在DeepSeekRouterMiddleware.dispatch中加入宪法预检
# ═══════════════════════════════════════════════
# 找到 user_msg 赋值后, 加预检
PRE_CHECK_MARKER = "# 联邦知识检索\n            async def fetch_knowledge():"
PRE_CHECK_NEW = """# 🔴 宪法L7预检(八红线)
            pre_block = constitution_pre_check(user_msg)
            if pre_block:
                return JSONResponse({
                    "choices": [{"message": {"role": "assistant", "content": pre_block}}],
                    "lgox_meta": {"route": "constitution_block", "model": "none", "cached": False}
                })
            
            # 联邦知识检索
            async def fetch_knowledge():"""

if "constitution_pre_check(user_msg)" not in code:
    code = code.replace(PRE_CHECK_MARKER, PRE_CHECK_NEW)
    changed = True
    print("[PATCH2] ✅ L7宪法预检已加入请求流水线")

# ═══════════════════════════════════════════════
# PATCH 3: 在system prompt中注入节点健康信息
# ═══════════════════════════════════════════════
HEALTH_INJ_MARKER = '请基于以上真实信息回答。如果问题超出以上范围，可以说不知道，不要编造。"'
HEALTH_INJ_NEW = '请基于以上真实信息回答。如果问题超出以上范围，可以说不知道，不要编造。'
HEALTH_INJ_NEW += '\\n" + get_health_text() + "\\n"'

if "get_health_text()" not in code:
    code = code.replace(HEALTH_INJ_MARKER, HEALTH_INJ_NEW)
    changed = True
    print("[PATCH3] ✅ L0多节点健康探测已注入系统提示词")

# ═══════════════════════════════════════════════
# PATCH 4: 在 _bg7 线程中加入联邦桥消息发送
# ═══════════════════════════════════════════════
BG7_MARKER = "import threading\n                        threading.Thread(target=_bg7,args=(user_msg,_ai_reply,_is_xs),daemon=True).start()"
BG7_NEW = """import threading
                        threading.Thread(target=_bg7,args=(user_msg,_ai_reply,_is_xs),daemon=True).start()
                        # 🟢 L2联邦桥协同: 发送对话摘要到联邦桥
                        if len(user_msg) > 10 and len(_ai_reply) > 50:
                            import json as _j_bridge
                            try:
                                _bridge_data = _j_bridge.dumps({
                                    "from_node": "天巡",
                                    "node_id": 10,
                                    "type": "tianxun_dialogue",
                                    "ts": __import__("time").time(),
                                    "u": user_msg[:80],
                                    "a": _ai_reply[:120]
                                }).encode()
                                _ur_bridge = __import__("urllib.request")
                                _rq = _ur_bridge.Request("http://100.100.89.2:8765/api/message",
                                    data=_bridge_data,
                                    headers={"Content-Type": "application/json"})
                                _ur_bridge.urlopen(_rq, timeout=1.5)
                            except:
                                pass"""

if "tianxun_dialogue" not in code:
    code = code.replace(BG7_MARKER, BG7_NEW)
    changed = True
    print("[PATCH4] ✅ L2联邦桥协同消息已加入响应后处理")

# ═══════════════════════════════════════════════
# PATCH 5: 天巡系统提示词补充七自闭环100%声明
# ═══════════════════════════════════════════════
# 把七自声明换成100%
V6_100_MARKER1 = "七自基因: 自感知/自协调/自愈合/自进化/自迭代/自反思/自约束。七自闭环率100%。"
V6_100_NEW1 = "七自基因100%闭环(v3.0): L7预检→自感知·多节探测→自协调·联邦桥协同→自愈合·三级灾备→自进化·基因写入→自迭代·/v动态版→自反思·日志+LGE→自约束·预检否决。"

if "七自闭环率100%" in code and "七自基因100%闭环(v3.0)" not in code:
    code = code.replace(V6_100_MARKER1, V6_100_NEW1)
    changed = True
    print("[PATCH5] ✅ 七自100%声明已升级为v3.0完整版")

# ═══════════════════════════════════════════════
# PATCH 5b: 把基因引用更新
# ═══════════════════════════════════════════════
GENE_MARKER = '(76万+知识基因)'
GENE_NEW = f'({open("/tmp/gene-live.json").read() if __import__("os").path.exists("/tmp/gene-live.json") else "76"}万+知识基因·实时)'
# Actually use dynamic
try:
    import json as _j_gc, os as _o_gc
    if _o_gc.path.exists("/tmp/gene-live.json"):
        with open("/tmp/gene-live.json") as f:
            gc = _j_gc.load(f).get("genes_total", 760000)
        GENE_NEW2 = f'({gc//10000}万+知识基因·联邦知识库)'
    else:
        GENE_NEW2 = '(76万+知识基因·联邦知识库)'
except:
    GENE_NEW2 = '(76万+知识基因·联邦知识库)'

if GENE_MARKER in code and GENE_NEW2 not in code:
    code = code.replace(GENE_MARKER, GENE_NEW2)
    changed = True
    print("[PATCH5b] ✅ 基因数引用已更新")

# ═══════════════════════════════════════════════
# WRITE BACK
# ═══════════════════════════════════════════════
if changed:
    with open(GATEWAY_PATH, "w") as f:
        f.write(code)
    print(f"\n{'='*60}")
    print(f"全绿注入完成! {GATEWAY_PATH}")
    print(f"{'='*60}")
else:
    print("⚠️ 未检测到需要修改的内容, 可能已经注入过了")
    sys.exit(1)
