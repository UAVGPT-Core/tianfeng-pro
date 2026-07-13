#!/usr/bin/env python3
"""小枢全绿 v2: L-1感知改为非阻塞·修复hang"""
path = "/Users/a1/stockagent-backend/main.py"
with open(path) as f:
    code = f.read()

# Remove the blocking L-1 probe, keep L4 + L1
old_blocking = '''    # ═══ L-1感知: 多节点健康探测 ═══
    _health_info = ""
    try:
        import socket as _sk, concurrent.futures as _cf
        _nodes = [("100.100.89.2",8765,"天枢"),("100.116.0.29",8765,"地枢"),("100.118.207.31",8765,"天工")]
        def _probe(ip,port,name):
            try:
                s=_sk.socket(_sk.AF_INET,_sk.SOCK_STREAM);s.settimeout(0.8)
                r=s.connect_ex((ip,port));s.close()
                return name if r==0 else None
            except Exception as e: return None
        with _cf.ThreadPoolExecutor(max_workers=3) as _ex:
            _alive=[n for n in _ex.map(lambda x:_probe(*x),_nodes) if n]
        if _alive:
            _health_info = " | 联邦在线: " + ",".join(_alive)
    except Exception as e:
        pass'''

new_nonblocking = '''    # ═══ L-1感知: 多节点健康探测(缓存·非阻塞) ═══
    _health_info = ""
    try:
        # 读缓存(由后台线程定期更新)
        import os as _os_probe, json as _js_probe
        _cache = _os_probe.path.expanduser("~/lgox-ops/data/xiaoshu-health-cache.json")
        if _os_probe.path.exists(_cache):
            _age = __import__("time").time() - _os_probe.path.getmtime(_cache)
            if _age < 120:  # 2min内缓存有效
                _cdata = _js_probe.load(open(_cache))
                _alive = _cdata.get("alive",[])
                if _alive:
                    _health_info = " | 联邦在线: " + ",".join(_alive)
    except Exception as e:
        pass'''

if old_blocking in code:
    code = code.replace(old_blocking, new_nonblocking)
    print("✅ L-1感知: 阻塞→缓存(非阻塞)")
else:
    print("⚠️ blocking L-1 not found - checking for nonblocking")
    if "xiaoshu-health-cache" in code:
        print("   already non-blocking")
    else:
        # Check what's there
        idx = code.find("async def xiaoshu_chat(")
        chunk = code[idx:idx+1500]
        if "L-1感知" in chunk:
            print("   L-1 exists but format differs")
        else:
            print("   L-1 not found")

with open(path, "w") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("✅ 语法OK")
except py_compile.PyCompileError as e:
    print(f"❌ {e}")
