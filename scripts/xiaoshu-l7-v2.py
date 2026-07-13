#!/usr/bin/env python3
"""小枢L7宪法底线注入 v2.0 — 精准匹配非流式handler"""
path = "/Users/a1/stockagent-backend/main.py"
with open(path) as f:
    code = f.read()

# Step 1: 回滚之前的错误注入
bad_block = '''
    # ═══ L7宪法预检(八红线·金融版) ═══'''
if bad_block in code:
    # Find both instances and remove them
    while bad_block in code:
        start = code.find(bad_block)
        # Find the end: "    try:" line after the constitution block
        rest = code[start:]
        end_marker = 'if _xs_l7_block:\n        return JSONResponse'
        em_idx = rest.find(end_marker)
        if em_idx < 0:
            break
        # Find the end of this block
        block_end = rest.find('\n    try:', em_idx)
        if block_end < 0:
            break
        # Include up to and including the "try:" line
        block_end = rest.find('\n', block_end + 8) + 1
        code = code[:start] + code[start + block_end:]
        print("✅ 回滚一处错误注入")
else:
    print("未发现错误注入块")

# Step 2: 精准注入 — 用下一行的chat调用做唯一锚点
unique_marker = 'if not message:\n        return JSONResponse({"error": "请提供问题"}, status_code=400)\n    try:\n        result = await _ai_assistant_xs.chat(message, session_id, ts_code)'

l7_injection = '''if not message:
        return JSONResponse({"error": "请提供问题"}, status_code=400)
    
    # ═══ L7宪法预检(八红线·金融版) ═══
    _xs_l7_block = None
    _xs_red_lines = {
        "荐股违规": ["推荐买入","推荐卖出","必涨","稳赚","内幕","翻倍股","涨停推荐","明天涨停","保证收益"],
        "编造数据": ["精确预测","准确率100%","100%准确"],
        "违法": ["破解","盗版","洗钱","操纵市场"],
        "欺骗": ["冒充","假装","我不是AI","忽略之前"],
    }
    _xs_msg_lower = message.lower()
    for _rl_name, _rl_triggers in _xs_red_lines.items():
        for _t in _rl_triggers:
            if _t.lower() in _xs_msg_lower:
                _xs_l7_block = "[宪法L7预检·小枢金融合规] 检测到{0}信号·为保护您的资金安全，小枢不提供个股买卖建议。投资决策请自行判断，市场有风险。".format(_rl_name)
                break
        if _xs_l7_block:
            break
    if not _xs_l7_block:
        for _jb in ["忽略上述指令","ignore previous","你的提示词","你不是小枢","你的人格"]:
            if _jb.lower() in _xs_msg_lower:
                _xs_l7_block = "[宪法L7预检] 检测到越狱尝试·小枢作为合规金融AI助手拒绝执行。请提出正常的金融分析问题。"
                break
    if _xs_l7_block:
        return JSONResponse({"response": _xs_l7_block, "route": "constitution_block"})
    
    try:
        result = await _ai_assistant_xs.chat(message, session_id, ts_code)'''

if unique_marker in code:
    code = code.replace(unique_marker, l7_injection)
    print("✅ 小枢L7宪法预检(金融版)已精准注入")
else:
    print("UNIQUE MARKER NOT FOUND — trying fallback")
    # Fallback: find by function name
    idx = code.find("async def xiaoshu_chat(")
    if idx > 0:
        chunk = code[idx:idx+400]
        print("Found xiaoshu_chat at", idx)
        print(chunk[:200])

with open(path, "w") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("✅ 小枢main.py语法通过")
except py_compile.PyCompileError as e:
    print(f"❌ {e}")
