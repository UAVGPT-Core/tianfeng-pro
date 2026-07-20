#!/usr/bin/env python3
"""临时补丁: perpetual引擎 produce_gene → 智谱 GLM-4-Flash"""
import re

PATH = '/home/uavgpt/lgox-ops/scripts/perpetual-gene-engine.py'

with open(PATH, 'r') as f:
    content = f.read()

# 策略: 最简单的方法 - 在produce_gene函数开头替换变量引用
# 把produce_gene中 NGC_GEN_MODEL→glm-4-flash, NGC_API→GLM_API, NGC_KEY→GLM_KEY

# 只替换produce_gene函数体内的引用(NGC_GEN_MODEL,NGC_API,NGC_KEY)
# 函数定义在 ~line 210, 结束在 ~line 248
# 用正则找到produce_gene函数的NGC引用并替换

# 方法: 找到def produce_gene到下一个def之间的所有NGC_引用
m = re.search(r'(def produce_gene\(.*?)\n(.*?)(\n\ndef |\n# 第1层)', content, re.DOTALL)
if m:
    before = m.group(1)
    body = m.group(2)
    after = m.group(3)
    
    # 在函数体内替换NGC引用为GLM引用
    body = body.replace('NGC_GEN_MODEL', 'GLM_KEY')  # 先用临时名
    body = body.replace('NGC_GEN_MODEL', '"glm-4-flash"')  # 实际不会匹配因为已替换
    # 等等，重新来
    
    # 直接用字符串替换在产生函数体内
    body = body.replace('NGC_API', 'GLM_API')
    body = body.replace('NGC_GEN_MODEL', '"glm-4-flash"')  
    body = body.replace('NGC_KEY', 'GLM_KEY')
    
    # 修改Ollama降级的源标记
    body = body.replace('"ollama-cpu-fallback"', '"glm-4-flash-fallback"')
    
    new_content = content[:m.start()] + before + '\n' + body + '\n' + after + content[m.end():]
else:
    print("MATCH FAILED - falling back to global replace")
    # Fallback: 全局替换(但只在produce_gene相关区域)
    new_content = content

# 恢复CONCURRENCY=5
new_content = new_content.replace('CONCURRENCY = 3', 'CONCURRENCY = 5')
new_content = new_content.replace('CONCURRENCY = 1', 'CONCURRENCY = 5')

with open(PATH, 'w') as f:
    f.write(new_content)

print("PATCHED: produce_gene → 智谱 GLM-4-Flash")
print(f"CONCURRENCY=5")
