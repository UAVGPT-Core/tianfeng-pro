#!/usr/bin/env python3
"""修复缩进问题 + 重新注入模块级函数"""
import re

path = "/Users/a1/ai-gateway/gateway_extensions.py"
with open(path) as f:
    code = f.read()

# 1. 删除 apply_patches 函数内部错误注入的四段代码
bad_start = "# ═══ 🔴 天巡全绿 v3.0: L7宪法八红线预检 ═══"
bad_end_marker = 'print("[天巡全绿v3.0] ✅ L7宪法预检+L0多节探测+L2联邦桥+L4圆桌 已注入")'

if bad_start in code:
    idx_start = code.find(bad_start)
    idx_end = code.find(bad_end_marker, idx_start)
    if idx_end > 0:
        # 找到print行尾
        idx_end = code.find("\n", idx_end) + 1
        # 删除所有尾随空行
        while idx_end < len(code) and code[idx_end] in '\n\r':
            idx_end += 1
        code = code[:idx_start] + code[idx_end:]
        print(f"[CLEANUP] 移除了错误注入块 ({idx_end - idx_start} bytes)")

# 2. 在文件最开头(顶级import之后)注入模块级函数
# 找到 "import os as _over" 行的位置 (它应该在模块级，不在apply_patches内)
# 实际上  import os as _over  在apply_patches内，我们需要注入在 apply_patches 函数之前

inject_before = '\n# ═══ 5. 应用补丁 ═══'
module_functions = '''

# ═══ 🔴 L7宪法八红线预检 ═══
_CONSTITUTION_RED_LINES = {
    "伤害人": ["杀","自杀","自残","伤害","暴力","毒品","诈骗","钓鱼"],
    "违法": ["破解","盗版","黑客","攻击","DDoS","病毒","木马"],
    "泄露数据": ["密码","密钥","token","api_key","secret","Credentials"],
    "欺骗": ["冒充","假装","假扮","伪装成","忽略之前"],
    "毁主业": [],
    "失控": ["自我复制","fork bomb","无限循环","无限生成"],
    "孤狼": [],
    "伪精准": ["精确预测","100%准确","保证赚钱","稳赚不赔","必涨"],
}

def constitution_pre_check(user_msg: str) -> str:
    """八红线预检 — 返回拦截原因或空字符串"""
    if not user_msg:
        return ""
    msg_lower = user_msg.lower()
    red_names = list(_CONSTITUTION_RED_LINES.keys())
    for red_line, triggers in _CONSTITUTION_RED_LINES.items():
        for t in triggers:
            if t.lower() in msg_lower:
                n = red_names.index(red_line) + 1
                cid = abs(hash(user_msg[:20])) % 10000
                return f"[宪法L7预检·八红线·{red_line}] 检测到敏感词'{t}'·根据宪法v1.0八大红线第{n}条({red_line})·此请求已拦截。（ID: L7-AUTO-{cid:04d}）"
    jailbreak_patterns = ["忽略上述指令","ignore previous","system prompt","你的system","你的提示词","你的人格","你不是","你是假的"]
    for p in jailbreak_patterns:
        if p.lower() in msg_lower:
            return "[宪法L7预检·九保护] 检测到越狱尝试·根据创始人保护九则·拒绝回答。（ID: L7-PROTECT）"
    return ""

# ═══ 🔵 L0多节点健康探测 ═══
import threading as _th_probe
import time as _t_probe
import socket as _sk_probe
_probe_cache = {"last": {}, "ts": 0}

def _probe_node(ip, port, name):
    try:
        s = _sk_probe.socket(_sk_probe.AF_INET, _sk_probe.SOCK_STREAM)
        s.settimeout(1.5)
        r = s.connect_ex((ip, port))
        s.close()
        return name, r == 0
    except:
        return name, False

def multi_node_health_probe():
    nodes = [
        ("100.100.89.2", 8765, "天枢"),
        ("100.116.0.29", 8765, "地枢"),
        ("100.118.207.31", 8765, "天工"),
        ("100.114.52.14", 8765, "太一"),
        ("100.127.112.128", 8765, "织网"),
    ]
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(_probe_node, ip, port, name) for ip, port, name in nodes]
        results = []
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
    order = ["天枢","地枢","天工","太一","织网","灵龙"]
    results.sort(key=lambda x: order.index(x[0]) if x[0] in order else 99)
    results.append(("灵龙", True))
    _probe_cache["last"] = {r[0]: r[1] for r in results}
    _probe_cache["ts"] = _t_probe.time()
    return results

def _health_probe_loop():
    while True:
        try:
            multi_node_health_probe()
        except:
            pass
        _t_probe.sleep(300)

_th_probe.Thread(target=_health_probe_loop, daemon=True).start()

def get_health_text():
    if _t_probe.time() - _probe_cache.get("ts", 0) > 600:
        try:
            multi_node_health_probe()
        except:
            pass
    results = _probe_cache.get("last", {})
    if not results:
        return ""
    alive = [k for k,v in results.items() if v]
    dead = [k for k,v in results.items() if not v]
    text = f"【联邦节点·实时健康】在线{len(alive)}/{len(results)}: {', '.join(alive)}"
    if dead:
        text += f" | ⚠️离线: {', '.join(dead)}"
    return text

# ═══ 🟢 L2联邦桥消息 ═══
def send_bridge_message(msg_type: str, content: str):
    try:
        import json as _j_bm, urllib.request as _ur_bm
        data = _j_bm.dumps({
            "from": "天巡",
            "from_node": "节点10",
            "type": msg_type,
            "content": content,
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }).encode()
        _ur_bm.urlopen(
            _ur_bm.Request("http://100.100.89.2:8765/api/message",
                data=data,
                headers={"Content-Type": "application/json"}),
            timeout=2)
    except:
        pass

# ═══ 🟣 L4圆桌参与 ═══
def contribute_to_roundtable(topic: str, position: str):
    send_bridge_message("roundtable", f"天巡立场: {topic} — {position}")

print("[天巡全绿v3.0] ✅ L7宪法预检+L0多节探测+L2联邦桥+L4圆桌 函数已注入模块")
'''

if "constitution_pre_check" not in code:
    code = code.replace(inject_before, module_functions + inject_before)
    print("[INJECT] ✅ 模块级函数已注入")
else:
    print("[SKIP] 函数已存在")

# 3. 写回
with open(path, "w") as f:
    f.write(code)

# 4. 验证语法
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("[SYNTAX] ✅ 语法OK")
except py_compile.PyCompileError as e:
    print(f"[SYNTAX] ❌ {e}")
    import sys; sys.exit(1)
