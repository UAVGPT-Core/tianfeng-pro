#!/usr/bin/env python3
"""基因产出优化 v1.0: 天巡+小枢双大使基因高产化"""
import sys

# ============================================================
# 天巡: _bg7 基因产出优化
# ============================================================
gw_path = "/Users/a1/ai-gateway/gateway_extensions.py"
with open(gw_path) as f:
    gw = f.read()

# OLD: keyword-filtered gene write (only 11 keywords → low output)
old_bg7 = '''                                if len(u2)>5 and len(a2)>30:
                                    kw=["无人机","巡检","低空","联邦","LGOX","金字塔","七自","基因","轻量化","宪法","灾备","飞轮"]
                                    hit=[k for k in kw if k in u2]
                                    if hit or len(u2)>30:
                                        s=a2[:300]
                                        for sep in ["结论","核心","总结"]:
                                            if sep in s:s=s[s.index(sep):];break
                                        g=_j7.dumps({"content":"[天巡·自进化] Q:"+u2[:80]+" -> "+s,"memory_type":"semantic","source":"tianxun-evolution","tags":["天巡","自进化"]+hit[:3]}).encode()
                                        try:
                                            import urllib.request as _ur
                                            _ur.urlopen(_ur.Request("http://100.116.0.29:8200/genes/write",data=g,headers={"Content-Type":"application/json"}),timeout=5)
                                        except:pass'''

# NEW: write gene for ALL substantive conversations + local fallback
new_bg7 = '''                                # 基因产出优化v1.0: 全量对话→基因(不再关键词过滤)
                                if len(u2)>3 and len(a2)>40:
                                    s=a2[:300]
                                    # 提取精华: 优先取结论/核心/总结段
                                    for sep in ["结论","核心","总结","关键","建议","分析"]:
                                        if sep in s:s=s[s.index(sep):];break
                                    gene_content="[天巡·自进化] Q:"+u2[:80]+" -> "+s
                                    g=_j7.dumps({"content":gene_content,"memory_type":"semantic","source":"tianxun-evolution","tags":["天巡","自进化","v4.0"]}).encode()
                                    # T1: LGE直写
                                    written=False
                                    try:
                                        import urllib.request as _ur
                                        _ur.urlopen(_ur.Request("http://100.116.0.29:8200/genes/write",data=g,headers={"Content-Type":"application/json"}),timeout=5)
                                        written=True
                                    except:
                                        pass
                                    # T2: 本地fallback(防LGE不可达导致基因丢失)
                                    if not written:
                                        try:
                                            _fb=_o7.path.join(_d,"gene-fallback.log")
                                            open(_fb,"a",encoding="utf-8").write(_j7.dumps({"ts":_ts.isoformat(),"gene":gene_content[:200]},ensure_ascii=False)+"\\n")
                                        except:
                                            pass'''

if old_bg7 in gw:
    gw = gw.replace(old_bg7, new_bg7)
    print("✅ 天巡基因: 关键词过滤→全量对话+本地fallback")
else:
    print("❌ 天巡 旧bg7未找到")

with open(gw_path, "w") as f:
    f.write(gw)

# ============================================================
# 小枢: 注入层补充基因写入
# ============================================================
xs_path = "/Users/a1/stockagent-backend/main.py"
with open(xs_path) as f:
    xs = f.read()

# Find the reflection block and add gene writing
old_xs_refl = '''                _xs_js2.dump(_xs_audit_data, open(_xs_audit, "w"), ensure_ascii=False, indent=2)'''

new_xs_refl = '''                _xs_js2.dump(_xs_audit_data, open(_xs_audit, "w"), ensure_ascii=False, indent=2)
                # 基因写入(注入层补充·全量对话→基因)
                if len(message) > 3 and len(_xs_reply2) > 40:
                    try:
                        import urllib.request as _xs_urw
                        _xs_s = _xs_reply2[:300]
                        for _xs_sep in ["结论","核心","总结","关键","建议","分析"]:
                            if _xs_sep in _xs_s:
                                _xs_s = _xs_s[_xs_s.index(_xs_sep):]
                                break
                        _xs_gene = _xs_js2.dumps({
                            "content": "[小枢·自进化] Q:" + message[:80] + " -> " + _xs_s,
                            "memory_type": "semantic",
                            "source": "xiaoshu-evolution-v2",
                            "tags": ["小枢","自进化","七自满格"]
                        }).encode()
                        _xs_urw.urlopen(_xs_urw.Request(
                            "http://100.116.0.29:8200/genes/write",
                            data=_xs_gene,
                            headers={"Content-Type": "application/json"}), timeout=3)
                    except:
                        # 本地fallback
                        try:
                            _xs_fb = _xs_os2.path.join(_xs_d, "gene-fallback-xiaoshu.log")
                            open(_xs_fb, "a", encoding="utf-8").write(
                                _xs_js2.dumps({"ts": _xs_ts.isoformat(), "u": message[:80]}, ensure_ascii=False) + "\\n")
                        except:
                            pass'''

if old_xs_refl in xs:
    xs = xs.replace(old_xs_refl, new_xs_refl)
    print("✅ 小枢基因: 注入层全量对话写LGE+fallback")
else:
    print("❌ 小枢 旧reflection未找到")
    idx = xs.find("xiaoshu-quality.json")
    if idx > 0:
        print("  context:", xs[idx:idx+200])

with open(xs_path, "w") as f:
    f.write(xs)

# ============================================================
# 验证语法
# ============================================================
import py_compile
errors = []
for p in [gw_path, xs_path]:
    try:
        py_compile.compile(p, doraise=True)
        print(f"✅ {p.split('/')[-1]} 语法OK")
    except py_compile.PyCompileError as e:
        print(f"❌ {p.split('/')[-1]}: {e}")
        errors.append(p)

if errors:
    sys.exit(1)
print("\n基因产出优化完成: 天巡全量+小枢补充 → 目标80+/30+ 每天")
