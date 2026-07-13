#!/usr/bin/env python3
"""修复孤儿块 + 天巡bg7基因产出优化"""
gw_path = "/Users/a1/ai-gateway/gateway_extensions.py"
with open(gw_path) as f:
    gw = f.read()

# Step 1: 击毙孤儿JSONResponse块
orphan = '            # 联邦知识检索({\n                    "choices": [{"message": {"role": "assistant", "content": pre_block}}],\n                    "lgox_meta": {"route": "constitution_block", "model": "none", "cached": False}\n                })\n            \n            # ═══ L4轻量规划路由 v4.0 ═══'
replacement = '            # ═══ L4轻量规划路由 v4.0 ═══'
if orphan in gw:
    gw = gw.replace(orphan, replacement)
    print("✅ 孤儿块已击毙")
else:
    print("孤儿块未找到(可能已修复)")

# Step 2: 修复bg7基因产出(使用Unicode escapes版)
old_cond = "if len(u2)>5 and len(a2)>30:"
new_cond = "if len(u2)>3 and len(a2)>40:"
if old_cond in gw and new_cond not in gw:
    # 把整个if块替换
    old_full = '''                                if len(u2)>5 and len(a2)>30:
                                    kw=["\u65e0\u4eba\u673a","\u5de1\u68c0","\u4f4e\u7a7a","\u8054\u90a6","LGOX","\u91d1\u5b57\u5854","\u4e03\u81ea","\u57fa\u56e0","\u8f7b\u91cf\u5316","\u5baa\u6cd5","\u707e\u5907","\u98de\u8f6e"]
                                    hit=[k for k in kw if k in u2]
                                    if hit or len(u2)>30:
                                        s=a2[:300]
                                        for sep in ["\u7ed3\u8bba","\u6838\u5fc3","\u603b\u7ed3"]:
                                            if sep in s:s=s[s.index(sep):];break
                                        g=_j7.dumps({"content":"[\u5929\u5de1\u00b7\u81ea\u8fdb\u5316] Q:"+u2[:80]+" -> "+s,"memory_type":"semantic","source":"tianxun-evolution","tags":["\u5929\u5de1","\u81ea\u8fdb\u5316"]+hit[:3]}).encode()
                                        try:
                                            import urllib.request as _ur
                                            _ur.urlopen(_ur.Request("http://100.116.0.29:8200/genes/write",data=g,headers={"Content-Type":"application/json"}),timeout=5)
                                        except:pass'''
    
    new_full = '''                                if len(u2)>3 and len(a2)>40:
                                    # 基因产出优化v1.0: 全量对话→基因+本地fallback
                                    s=a2[:300]
                                    for sep in ["\u7ed3\u8bba","\u6838\u5fc3","\u603b\u7ed3","\u5173\u952e","\u5efa\u8bae","\u5206\u6790"]:
                                        if sep in s:s=s[s.index(sep):];break
                                    g=_j7.dumps({"content":"[\u5929\u5de1\u00b7\u81ea\u8fdb\u5316] Q:"+u2[:80]+" -> "+s,"memory_type":"semantic","source":"tianxun-evolution","tags":["\u5929\u5de1","\u81ea\u8fdb\u5316","v4.0"]}).encode()
                                    written=False
                                    try:
                                        import urllib.request as _ur
                                        _ur.urlopen(_ur.Request("http://100.116.0.29:8200/genes/write",data=g,headers={"Content-Type":"application/json"}),timeout=5)
                                        written=True
                                    except:
                                        pass
                                    if not written:
                                        try:
                                            _fb=_o7.path.join(_d,"gene-fallback-tianxun.log")
                                            open(_fb,"a",encoding="utf-8").write(_j7.dumps({"ts":_ts.isoformat(),"gene_len":len(gene_content)},ensure_ascii=False)+"\\n")
                                        except:
                                            pass'''
    
    if old_full in gw:
        gw = gw.replace(old_full, new_full)
        print("✅ 天巡bg7: 关键词过滤→全量对话+本地fallback")
    else:
        print("bg7完整块未匹配")
        # show what's there
        idx = gw.find("if len(u2)>5")
        if idx > 0:
            print(gw[idx:idx+500])

# Write back and verify
with open(gw_path, "w") as f:
    f.write(gw)

import py_compile
try:
    py_compile.compile(gw_path, doraise=True)
    print("✅ gateway_extensions.py 语法OK")
except py_compile.PyCompileError as e:
    print("SYNTAX ERROR:", e)
