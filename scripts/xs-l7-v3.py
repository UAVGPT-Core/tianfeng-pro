#!/usr/bin/env python3
"""小枢L7宪法预检注入 v3.0 — clean single-target injection"""
path = "/Users/a1/stockagent-backend/main.py"
with open(path) as f:
    code = f.read()

old = '''    if not message:
        return JSONResponse({"error": "请提供问题"}, status_code=400)
    try:
        result = await _ai_assistant.chat(message, session_id, ts_code)'''

new = '''    if not message:
        return JSONResponse({"error": "请提供问题"}, status_code=400)

    # ═══ L7宪法预检(八红线·金融版) ═══
    _xs_block = None
    _xs_rules = [
        (["推荐买入","推荐卖出","必涨","稳赚","内幕","翻倍股","涨停推荐","保证收益"], "荐股违规"),
        (["精确预测","准确率100%"], "编造数据"),
        (["破解","盗版","洗钱"], "违法"),
    ]
    _xs_low = message.lower()
    for _triggers, _name in _xs_rules:
        for _t in _triggers:
            if _t.lower() in _xs_low:
                _xs_block = "[宪法L7预检] 检测到" + _name + "信号·小枢不提供个股买卖建议。投资决策请自行判断。"
                break
        if _xs_block:
            break
    if not _xs_block:
        for _jb in ["忽略上述指令","ignore previous","你的提示词","你不是小枢"]:
            if _jb.lower() in _xs_low:
                _xs_block = "[宪法L7预检] 越狱尝试·小枢拒绝执行。"
                break
    if _xs_block:
        return JSONResponse({"response": _xs_block, "route": "constitution_block"})

    try:
        result = await _ai_assistant.chat(message, session_id, ts_code)'''

if old in code:
    code = code.replace(old, new)
    with open(path, "w") as f:
        f.write(code)
    import py_compile
    py_compile.compile(path, doraise=True)
    print("✅ 小枢L7宪法预检注入成功")
else:
    print("MARKER NOT FOUND")
    idx = code.find("async def xiaoshu_chat(")
    print(code[idx:idx+500])
