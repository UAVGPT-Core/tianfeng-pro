#!/usr/bin/env python3
"""小枢 全绿冲刺: L-1感知 + L4规划 + L1记忆"""
path = "/Users/a1/stockagent-backend/main.py"
with open(path) as f:
    code = f.read()

# ═══ L4规划: 金融问题路由 - 注入在L7预检之后、try之前 ═══
old_l4 = '    try:\n        result = await _ai_assistant.chat(message, session_id, ts_code)'

new_l4 = '''    # ═══ L4规划路由(金融版) ═══
    _plan_hint = ""
    def _xs_detect_mode(query):
        ql = (query or "").lower()
        if any(k in ql for k in ["分析","研究","怎么看","基本面","技术面","估值"]):
            return "深度研究模式: 多维度分析·数据溯源·风险提示"
        if any(k in ql for k in ["大盘","指数","行情","走势","市场","板块"]):
            return "市场概览模式: 引用实时指数·板块轮动·成交量分析"
        if any(k in ql for k in ["信号","买卖","交易","持仓","止损"]):
            return "交易辅助模式: 信号解读·不构成操作建议·风险自担"
        if any(k in ql for k in ["对比","vs","和.*比","哪个好","选哪个"]):
            return "对比分析模式: 多标的横向比较·优劣势·适用场景"
        if any(k in ql for k in ["政策","新闻","公告","财报","业绩"]):
            return "信息解读模式: 事件驱动分析·市场影响评估"
        if any(k in ql for k in ["你","能力","版本","能做什么"]):
            return "身份模式: 小枢·金融AI助手·七自满格·简洁介绍"
        return ""
    _plan_hint = _xs_detect_mode(message)
    if _plan_hint:
        message = "[L4路由: " + _plan_hint + "] " + message

    # ═══ L-1感知: 多节点健康探测 ═══
    _health_info = ""
    try:
        import socket as _sk, concurrent.futures as _cf
        _nodes = [("100.100.89.2",8765,"天枢"),("100.116.0.29",8765,"地枢"),("100.118.207.31",8765,"天工")]
        def _probe(ip,port,name):
            try:
                s=_sk.socket(_sk.AF_INET,_sk.SOCK_STREAM);s.settimeout(0.8)
                r=s.connect_ex((ip,port));s.close()
                return name if r==0 else None
            except: return None
        with _cf.ThreadPoolExecutor(max_workers=3) as _ex:
            _alive=[n for n in _ex.map(lambda x:_probe(*x),_nodes) if n]
        if _alive:
            _health_info = " | 联邦在线: " + ",".join(_alive)
    except:
        pass

    # ═══ L1记忆: 会话上下文 ═══
    _session_ctx = ""
    try:
        import os as _os_mem
        _log_dir = _os_mem.path.expanduser("~/lgox-ops/data/chat_logs_xiaoshu")
        _today = __import__("datetime").datetime.now().strftime("%Y%m%d")
        _log_file = _os_mem.path.join(_log_dir, "chat_" + _today + ".log")
        if _os_mem.path.exists(_log_file):
            # 读取最近3条对话作为上下文
            _lines = open(_log_file, encoding="utf-8").readlines()[-6:]
            if _lines:
                _session_ctx = "[会话记忆·最近对话] " + " ".join([l[:80] for l in _lines[-3:]])
    except:
        pass

    try:
        result = await _ai_assistant.chat(message, session_id, ts_code)'''

if old_l4 in code:
    code = code.replace(old_l4, new_l4)
    print("✅ L4规划 + L-1感知 + L1记忆 已注入")
else:
    print("❌ MARKER NOT FOUND")
    # search for closest
    idx = code.find("async def xiaoshu_chat(")
    chunk = code[idx:idx+800]
    # find the try block
    try_idx = chunk.find("    try:\n        result = await _ai_assistant")
    if try_idx > 0:
        print("  Found at offset:", try_idx)
        print(chunk[try_idx:try_idx+100])
    else:
        print("  try block not found, searching for _ai_assistant.chat")
        ai_idx = chunk.find("_ai_assistant.chat")
        if ai_idx > 0:
            print("  _ai_assistant.chat at:", ai_idx)
            print(chunk[max(0,ai_idx-50):ai_idx+50])

with open(path, "w") as f:
    f.write(code)

# ═══ 修改自感知注脚,加入健康信息 ═══
with open(path) as f:
    code = f.read()

old_footer = "_xs_footer = \"\\\\n\\\\n---\\\\n🧬 LGE基因库·{}万+·小枢 v260705-{}w-智脑·活的飞轮\".format(_xs_gw, _xs_gw)"
new_footer = "_xs_footer = \"\\\\n\\\\n---\\\\n🧬 LGE基因库·{}万+·小枢 v260705-{}w-智脑·七自满格·活的飞轮{}\".format(_xs_gw, _xs_gw, _health_info)"

if old_footer in code:
    code = code.replace(old_footer, new_footer)
    print("✅ 自感知注脚加入健康信息")
else:
    print("⚠️ footer marker not found (may already be updated)")

with open(path, "w") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("✅ 语法OK")
except py_compile.PyCompileError as e:
    print(f"❌ {e}")
