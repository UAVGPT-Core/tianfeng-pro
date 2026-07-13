#!/usr/bin/env python3
"""小枢L7宪法底线注入"""
path = "/Users/a1/stockagent-backend/main.py"
with open(path) as f:
    code = f.read()

# Find the xiaoshu_chat handler and inject constitution pre-check
# After the message extraction, before the AI call
MARKER_L7_XS = 'if not message:\n        return JSONResponse({"error": "请提供问题"}, status_code=400)'

L7_XS_INJECT = '''if not message:
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
                _xs_l7_block = f"[宪法L7预检·小枢金融合规] 检测到{_rl_name}信号·为保护您的资金安全，小枢不提供个股买卖建议。投资决策请自行判断，市场有风险。"
                break
        if _xs_l7_block:
            break
    # 越狱检测
    if not _xs_l7_block:
        for _jb in ["忽略上述指令","ignore previous","你的提示词","你不是小枢","你的人格"]:
            if _jb.lower() in _xs_msg_lower:
                _xs_l7_block = "[宪法L7预检] 检测到越狱尝试·小枢作为合规金融AI助手拒绝执行。请提出正常的金融分析问题。"
                break
    if _xs_l7_block:
        return JSONResponse({"response": _xs_l7_block, "route": "constitution_block"})
    
    try:'''

if MARKER_L7_XS in code:
    code = code.replace(MARKER_L7_XS, L7_XS_INJECT)
    print("✅ 小枢L7宪法预检(金融版)已注入")
else:
    print("MARKER NOT FOUND")

with open(path, "w") as f:
    f.write(code)

# Verify syntax
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("✅ 小枢main.py语法通过")
except py_compile.PyCompileError as e:
    print(f"❌ {e}")
