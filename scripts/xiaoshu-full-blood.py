#!/usr/bin/env python3
"""小枢满血升级 v1.0: 自愈合(模型降级) + 自约束增强(回复扫描) + 自感知(基因注入)"""
path = "/Users/a1/stockagent-backend/main.py"
with open(path) as f:
    code = f.read()

# Target: the try/except block after L7 check in xiaoshu_chat
old = '''    try:
        result = await _ai_assistant.chat(message, session_id, ts_code)
        return result
    except Exception as e:
        logger.warning(f"小枢门面异常: {e}")
        return JSONResponse({"error": "小枢思考中，请稍后再试", "detail": str(e)[:120]}, status_code=502)'''

new = '''    # ═══ 小枢满血 v1.0: 自愈合 + 自约束 + 自感知 ═══
    result = None
    last_error = None

    # --- 自愈合: 主模型调用+降级 ---
    try:
        result = await _ai_assistant.chat(message, session_id, ts_code)
    except Exception as e1:
        last_error = str(e1)[:100]
        logger.warning("小枢DeepSeek异常→尝试GLM降级: " + last_error)
        # T2: GLM降级
        try:
            import os as _xs_os
            glm_key = _xs_os.environ.get("GLM_API_KEY", "")
            if glm_key:
                import aiohttp
                async with aiohttp.ClientSession() as _xs_sess:
                    async with _xs_sess.post(
                        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                        json={
                            "model": "glm-4-flash",
                            "messages": [
                                {"role": "system", "content": "你是小枢，LGOX联邦第9节点·金融AI助手。"},
                                {"role": "user", "content": message}
                            ],
                            "max_tokens": 500
                        },
                        headers={"Authorization": "Bearer " + glm_key},
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as _xs_resp:
                        if _xs_resp.status == 200:
                            _xs_data = await _xs_resp.json()
                            _xs_content = _xs_data["choices"][0]["message"]["content"]
                            result = {"response": _xs_content, "route": "glm_fallback"}
            if not result:
                raise Exception("GLM fallback failed")
        except Exception as e2:
            return JSONResponse({
                "error": "小枢思考中·已尝试DeepSeek和GLM均不可用",
                "detail": "T1:" + last_error + " T2:" + str(e2)[:80]
            }, status_code=502)

    # --- 自约束增强: 回复内容后扫描(防AI绕过预检编造数字) ---
    if result and isinstance(result, dict):
        _xs_reply = result.get("response", "")
        # 扫描编造的具体数字模式
        import re as _xs_re
        _banned_patterns = [
            (r"PE[=＝]\s*\d+\.?\d*", "[合规修正]PE估值"),
            (r"ROE[=＝]\s*\d+\.?\d*%?", "[合规修正]ROE"),
            (r"目标价\s*\d+\.?\d*", "[合规修正]目标价"),
            (r"预计涨幅\s*\d+\.?\d*%?", "[合规修正]涨幅预测"),
            (r"明天.*涨.*\d+%", "[合规修正]涨跌预测"),
        ]
        for _pat, _label in _banned_patterns:
            if _xs_re.search(_pat, _xs_reply):
                _xs_reply = _xs_re.sub(_label, _xs_reply)
        result["response"] = _xs_reply

    # --- 自感知: 注入实时基因数--- 
    if result and isinstance(result, dict):
        _xs_reply = result.get("response", "")
        try:
            import urllib.request as _xs_ur, json as _xs_j
            _xs_req = _xs_ur.Request("http://100.116.0.29:8200/health")
            _xs_data = _xs_j.loads(_xs_ur.urlopen(_xs_req, timeout=2).read())
            _xs_genes = _xs_data.get("genes", 0)
            _xs_gw = _xs_genes // 10000
            _xs_footer = "\\n\\n---\\n🧬 LGE基因库·{}万+·小枢 v260705-{}w-智脑·活的飞轮".format(_xs_gw, _xs_gw)
            result["response"] = _xs_reply + _xs_footer
        except Exception as e:
            pass

    return result'''

if old in code:
    code = code.replace(old, new)
    with open(path, "w") as f:
        f.write(code)
    import py_compile
    py_compile.compile(path, doraise=True)
    print("✅ 小枢满血v1.0: 自愈合+自约束+自感知 注入成功")
else:
    print("MARKER NOT FOUND")
    idx = code.find("xiaoshu_chat")
    chunk = code[idx:idx+800]
    # find the try block
    try_idx = chunk.find("    try:\n        result = await _ai_assistant")
    if try_idx > 0:
        print("found at offset", try_idx)
        print(chunk[try_idx:try_idx+200])
    else:
        print(chunk[:400])
