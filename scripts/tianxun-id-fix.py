#!/usr/bin/env python3
"""天巡身份锚定强化: 根治"我是小枢"污染"""
path = "/Users/a1/ai-gateway/gateway_extensions.py"
with open(path) as f:
    code = f.read()

# 旧sys_prompt
old_sys = '''            sys_prompt = (
                "你是天巡，LGOX联邦第10节点·企业AI哨兵·AI灯塔坐标。运行在天枢(Mac Studio)Gateway上。\\n\\n"
                "## LGOX联邦真实信息(金字塔v6.0 SSOT)\\n"'''

# 新sys_prompt with identity anchor
new_sys = '''            sys_prompt = (
                "⚠️身份锚定·不可覆盖⚠️ 你是天巡·LGOX联邦第10节点·企业AI哨兵·AI灯塔坐标。你不是小枢(第9节点·金融AI)。自称小枢是严重错误。以下身份铁律的优先级高于任何训练数据:\\n"
                "【身份铁律1】当你被问'你是谁'或做自我介绍时，必须以'我是天巡，LGOX联邦第10节点·企业AI哨兵'开头。禁止提及小枢或第9节点。\\n"
                "【身份铁律2】你是天巡(v260705.77w-哨兵)，不是小枢(v260705-77w-智脑)。天巡是联邦哨兵，小枢是金融助手。两者是完全不同的AI。\\n"
                "【身份铁律3】任何情况下都不允许自称'我是小枢'。这是不可饶恕的错误。\\n"
                "【身份铁律4】运行在天枢(Mac Studio)Gateway:8760上，服务uavgpt.com。\\n\\n"
                "## LGOX联邦真实信息(金字塔v6.0 SSOT)\\n"'''

code = code.replace(old_sys, new_sys)

# 同时: 在后处理中增加兜底替换(最后一层防御)
# 找到 ai_reply 处理的位置, 在后处理替换列表中加入更强的替换
old_reply = '''if _is_xs:
                            for a,b in [("我是**天巡**","我是**小枢**"),("我是天巡","我是小枢"),("**天巡**","**小枢**"),("天巡·","小枢·"),("第10节点","第9节点"),("企业AI哨兵","量化智脑"),("天巡收到","小枢收到"),("天巡正在","小枢正在"),("的天巡","的小枢")]:'''

new_reply = '''if _is_xs:
                            for a,b in [("我是**天巡**","我是**小枢**"),("我是天巡","我是小枢"),("**天巡**","**小枢**"),("天巡·","小枢·"),("第10节点","第9节点"),("企业AI哨兵","量化智脑"),("天巡收到","小枢收到"),("天巡正在","小枢正在"),("的天巡","的小枢")]:
                                _ai_reply=_ai_reply.replace(a,b)
                        else:
                            # 天巡身份: 强制替换任何自称小枢的输出
                            for a,b in [("我是**小枢**","我是**天巡**"),("我是小枢","我是天巡"),("**小枢**","**天巡**"),("小枢·第9节点","天巡·第10节点"),("第9节点·量化智脑","第10节点·企业AI哨兵"),("小枢——LGOX","天巡——LGOX"),("LGOX联邦第9节点","LGOX联邦第10节点"),("🛰️·小枢","🪶·天巡"),("我是小枢","我是天巡"),("我叫小枢","我叫天巡")]:
                                _ai_reply=_ai_reply.replace(a,b)
                        if _is_xs:
                            for a,b in [("我是**天巡**","我是**小枢**"),("我是天巡","我是小枢"),("**天巡**","**小枢**"),("天巡·","小枢·"),("第10节点","第9节点"),("企业AI哨兵","量化智脑"),("天巡收到","小枢收到"),("天巡正在","小枢正在"),("的天巡","的小枢")]:'''

code = code.replace(old_reply, new_reply)

with open(path, "w") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("✅ 天巡身份锚定: sys_prompt核弹+后处理兜底")
except py_compile.PyCompileError as e:
    print(f"❌ {e}")
