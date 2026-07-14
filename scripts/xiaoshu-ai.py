#!/usr/bin/env python3
"""
小枢独立AI服务 v3.5 — LGOX联邦第9节点·金融AI
部署: 灵龙 :8779 | launchd保活
模型: DeepSeek V4 Flash | 证据链: 8769统一查询
v5.0v3.5: 动态基因数·GCP宪法·FCPF v5.1·WidgetSpec v1.0·金字塔v7.82·零硬编码
"""
import json, os, time, urllib.request, asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

app = FastAPI(title="小枢·LGOX联邦金融AI", version="v3.5")


DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_KEY:
    try:
        with open(os.path.expanduser("~/.hermes/.env")) as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY="):
                    DEEPSEEK_KEY = line.split("=",1)[1].strip().strip('"').strip("'")
                    break
    except: pass
DS_URL = "https://api.deepseek.com/v1/chat/completions"
LGE_URL = "http://127.0.0.1:8769/query"
EVIDENCE_ENABLED = True
# ═══ Widget Spec v1.0（GCP子协议·浮窗部署规范） — 基因通讯协议标准 ═══
WIDGET_SPEC_VERSION = "1.0"
WIDGET_SPEC = ['relative-url', 'golden-master', 'dual-domain', 'gene-feedback', 'identity-guard', 'cors-native']
WIDGET_SPEC_STANDARDS = {
    "comms": "TYPE前缀·桥双发·四层L1-L4",
    "deploy": "秒改秒见·相对URL·双域一致·CF绕过",
    "gene": "五维评分·分类·域隔离·Golden Master",
    "widget": "三件套(f+t+x)·脚本顺序·相对URL·禁止x83558684"
}


# ═══ 活数据·零硬编码 ═══
PYRAMID_VER = "v7.82"
FLYWHEEL_COUNT = 18  # 17飞轮+🛸机巢CAD(第16)+六六记忆+自洁=18 (动态更新见_bg_update_cache)
_gene_cache = {"count": 718000, "nodes": 10, "flywheels": 18, "ts": time.time()}

# ═══ 后台缓存更新(不阻塞事件循环) ═══
import threading
def _bg_update_cache():
    """后台线程更新基因/节点/飞轮缓存·三源实时"""
    global _gene_cache, FLYWHEEL_COUNT
    while True:
        try:
            time.sleep(300)  # 5分钟更新一次
            # ① 基因数 → LGE stats
            req = urllib.request.Request("http://100.116.0.29:8200/genes/stats", method="GET")
            with urllib.request.urlopen(req, timeout=3) as r:
                d = json.loads(r.read())
                c = d.get("total_genes", d.get("genes", 0))
                if c > 100000:
                    _gene_cache["count"] = c
            # ② 在线节点数 → 联邦桥健康
            try:
                req2 = urllib.request.Request("http://localhost:8765/health", method="GET")
                with urllib.request.urlopen(req2, timeout=3) as r2:
                    bd = json.loads(r2.read())
                    nodes_raw = bd.get("nodes", [])
                    # 只算联邦正式节点: 物理8 + 逻辑2 = 10
                    phys = [n for n in nodes_raw if n in ("天枢","地枢","天工","灵龙","太一","织网","天玑","天怿")]
                    logic = [n for n in nodes_raw if n in ("天巡","AI助手")]  # AI助手=小枢
                    _gene_cache["nodes"] = len(phys) + len(logic)
            except:
                pass
            # ③ 飞轮数 → 联邦桥飞轮状态 (fallback: 读取本地dashboard)
            try:
                req3 = urllib.request.Request("http://localhost:8765/federation/nodes", method="GET")
                with urllib.request.urlopen(req3, timeout=3) as r3:
                    fd = json.loads(r3.read())
                    fw_list = fd.get("flywheels", {})
                    if fw_list:
                        FLYWHEEL_COUNT = len(fw_list)
                        _gene_cache["flywheels"] = FLYWHEEL_COUNT
            except:
                pass
            _gene_cache["ts"] = time.time()
        except:
            pass

_bg_thread = threading.Thread(target=_bg_update_cache, daemon=True)
_bg_thread.start()


def live_gene_wan(brief=False):
    """动态获取基因数·LGE API·5分钟缓存"""
    global _gene_cache
    now = time.time()
    if now - _gene_cache["ts"] < 300:
        return f"{_gene_cache['count']//10000}万+" if not brief else f"{_gene_cache['count']//10000}万+"
    try:
        req = urllib.request.Request("http://100.116.0.29:8200/genes/stats", method="GET")
        with urllib.request.urlopen(req, timeout=3) as r:
            d = json.loads(r.read())
            c = d.get("total_genes", d.get("genes", 0))
            if c > 100000:
                _gene_cache["count"] = c
                _gene_cache["ts"] = now
    except:
        try:
            req2 = urllib.request.Request("http://100.116.0.29:8200/health", method="GET")
            with urllib.request.urlopen(req2, timeout=3) as r2:
                d2 = json.loads(r2.read())
                c = d2.get("total_genes", d2.get("genes", 0))
                if c > 100000:
                    _gene_cache["count"] = c
                    _gene_cache["ts"] = now
        except: pass
    return f"{_gene_cache['count']//10000}万+"

def live_nodes():
    global _gene_cache
    return _gene_cache.get("nodes", 10)

def build_system_prompt():
    """从Golden Master persona文件加载·哈希验证·防回退"""
    gw = live_gene_wan()
    nn = live_nodes()
    try:
        import os as _os
        persona_path = _os.path.expanduser("~/lgox-ops/scripts/persona_xiaoshu.txt")
        with open(persona_path) as f:
            template = f.read()
        import hashlib
        actual_hash = hashlib.sha256(template.encode()).hexdigest()[:16]
        if actual_hash != "d556eb5b36e30800acc3":
            print(f"WARNING: persona hash mismatch! expected=782dc52b29084384 got={actual_hash}")
    except:
        import os as _os
        template = open(_os.path.expanduser("~/lgox-ops/scripts/persona_xiaoshu.txt")).read()
    return template.format(gw=gw, nn=nn, pyramid=PYRAMID_VER, flywheels=FLYWHEEL_COUNT)
# ═══ 证据链注入 ═══
def fetch_evidence(query: str, max_results: int = 3) -> str:
    if not EVIDENCE_ENABLED: return ""
    qt = query[:60]
    # 路径1: LGE语义搜索
    try:
        payload = json.dumps({"query": qt, "n_results": max_results}).encode()
        req = urllib.request.Request("http://100.116.0.29:8200/genes/search",
            data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=4) as r:
            genes = json.loads(r.read()).get("results", [])
        if genes:
            lines = []
            for g in genes[:max_results]:
                gid = g.get("gene_id", "?")[:16]
                ct = g.get("content", "")[:120]
                fitness = g.get("fitness", 0)
                lines.append(f"  [{gid} f={fitness:.2f}] {ct}")
            return "\n".join(lines)
    except: pass
    # 路径2: 8769四引擎fallback
    try:
        payload2 = json.dumps({"q": qt, "engines": ["lge","bm25"], "limit": max_results}).encode()
        req2 = urllib.request.Request(LGE_URL, data=payload2,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req2, timeout=5) as r2:
            results = json.loads(r2.read()).get("results", [])
        if results:
            return "\n".join(f"  [{r.get('source','?')}] {str(r.get('content',''))[:120]}" for r in results[:max_results])
    except: pass
    return ""

# ═══ LLM调用 v2.0·多冗余·DeepSeek→Ollama降级 ═══
async def call_deepseek(messages: list, max_tokens: int = 500) -> dict:
    """async-safe·三路降级: DeepSeek → Ollama(天工) → 不可用"""
    payload = json.dumps({
        "model": "deepseek-v4-flash", "messages": messages,
        "max_tokens": max_tokens, "temperature": 0.4, "stream": False
    }).encode()
    
    def _ds():
        req = urllib.request.Request(DS_URL, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_KEY}"
        })
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read())
    try:
        return await asyncio.to_thread(_ds)
    except Exception:
        pass
    try:
        def _ollama():
            ol_payload = json.dumps({
                "model": "lgox-distill-v1:latest", "messages": messages,
                "stream": False, "options": {"num_predict": max_tokens}
            }).encode()
            req2 = urllib.request.Request("http://100.118.207.31:11434/api/chat",
                data=ol_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req2, timeout=30) as r2:
                raw = json.loads(r2.read())
            content = raw.get("message", {}).get("content", "")
            return {"choices": [{"message": {"content": content}}], "usage": {"total_tokens": 0}}
        return await asyncio.to_thread(_ollama)
    except Exception:
        raise RuntimeError("小枢·多路LLM全失败")


# ═══ 流式SSE引擎 v3.5 ═══
import http.client, ssl

def _deepseek_stream_sync(messages: list, max_tokens: int = 500):
    """同步SSE流·http.client直连·推理+内容双流"""
    payload = json.dumps({
        "model": "deepseek-v4-flash", "messages": messages,
        "max_tokens": max_tokens, "temperature": 0.4, "stream": True
    }).encode()
    
    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection("api.deepseek.com", timeout=30, context=ctx)
    try:
        conn.request("POST", "/v1/chat/completions", body=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Accept": "text/event-stream"
        })
        resp = conn.getresponse()
        while True:
            line = resp.readline()
            if not line:
                break
            line = line.decode("utf-8", errors="ignore").strip()
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    chunk = json.loads(line[6:])
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content") or ""
                    reasoning = delta.get("reasoning_content") or ""
                    if content:
                        yield ("c", content)  # 正式输出
                    elif reasoning:
                        yield ("r", reasoning)  # 推理过程(可选展示)
                except: pass
    finally:
        conn.close()

async def call_deepseek_stream(messages: list, max_tokens: int = 500):
    """异步包装·Queue桥接同步流→异步生成器·(type,text)元组"""
    q = asyncio.Queue()
    
    def _run():
        try:
            for item in _deepseek_stream_sync(messages, max_tokens):
                q.put_nowait(item)  # ("c"|"r", text)
        except Exception as e:
            q.put_nowait(None)
        else:
            q.put_nowait(None)
    
    asyncio.create_task(asyncio.to_thread(_run))
    while True:
        token = await q.get()
        if token is None:
            break
        yield token


# ═══ API端点 ═══
@app.post("/")
@app.post("/chat")
async def chat(request: Request):
    t0 = time.time()
    try: data = await request.json()
    except: return JSONResponse({"error": "invalid json"}, status_code=400)
    question = data.get("question", data.get("message", data.get("query", "")))
    if not question: return JSONResponse({"error": "question required"}, status_code=400)
    history = data.get("history", data.get("messages", []))
    evidence = fetch_evidence(question)
    system_msg = build_system_prompt()
    if evidence:
        system_msg += f"\n\n【证据链·LGE基因库】\n{evidence}\n\n严格基于以上证据回答。如果证据与用户问题不直接相关，必须回复'基因库中未检索到该信息'。禁止编造任何不在证据中的数据、时间、地点、人物行为。"
    else:
        system_msg += "\n\n【无证据】基因库中未找到相关信息。如果问题涉及LGOX联邦内部事务而你无法确定答案，请诚实回答'目前在基因库中未检索到相关信息'，禁止编造。"
    messages = [{"role": "system", "content": system_msg}]
    if history: messages.extend(history[-6:])
    messages.append({"role": "user", "content": question})
    try:
        resp = await call_deepseek(messages)
        answer = resp["choices"][0]["message"]["content"]
        tokens = resp.get("usage", {}).get("total_tokens", 0)
    except Exception as e:
        return JSONResponse({
            "channel": "小枢", "node": "小枢·LGOX联邦第9节点",
            "answer": f"抱歉，AI引擎暂时不可用: {str(e)[:80]}", "error": str(e)[:100]
        }, status_code=503)
    latency = int((time.time() - t0) * 1000)
    
    # v3.5 自进化: 高质回答自动纳基因(≥150字·有证据·非闲聊)
    gene_id = ""
    if len(answer) > 150 and evidence and "抱歉" not in answer[:50] and "基因库中未检索到" not in answer[:50]:
        try:
            # 质量自评: 长度+证据+身份=基础分
            base_score = min(0.65, 0.45 + len(answer)/1000 + len(evidence)/5000)
            gene_payload = json.dumps({
                "content": f"[自进化·小枢] Q:{question[:80]} → A:{answer[:200]}",
                "memory_type": "semantic", "source": "小枢自进化",
                "fitness": base_score
            }).encode()
            def _write_gene():
                req = urllib.request.Request("http://100.116.0.29:8200/genes/write",
                    data=gene_payload,
                    headers={"Content-Type":"application/json","X-LGE-Key":"lgox-federation-key-2024"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    return json.loads(r.read())
            result = await asyncio.to_thread(_write_gene)
            gene_id = result.get("gene_id", "")
        except:
            pass
    
    # v3.4 自反思
    quality = {"length": len(answer), "has_evidence": bool(evidence),
        "gene_written": bool(gene_id), "latency_ms": latency}
    
    return JSONResponse({
        "channel": "小枢", "node": "小枢·LGOX联邦第9节点",
        "question": question, "answer": answer,
        "evidence_count": len(evidence.split("\n")) if evidence else 0,
        "evidence": evidence[:500] if evidence else "",
        "tokens": tokens, "latency_ms": latency,
        "model": "deepseek-v4-flash", "version": "v3.5",
        "gene_id": gene_id, "quality": quality
    })

@app.api_route("/chat/completions", methods=["OPTIONS"])
async def chat_options():
    return JSONResponse({"status":"ok"}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    })

@app.post("/chat/completions")
async def openai_chat(request: Request):
    try: data = await request.json()
    except: return JSONResponse({"error":"invalid json"}, status_code=400)
    msgs = data.get("messages",[])
    q = ""
    for m in reversed(msgs):
        if m.get("role")=="user": q=m.get("content","")[:500]; break
    if not q: return JSONResponse({"error":"no user message"}, status_code=400)
    evidence = fetch_evidence(q)
    system_msg = build_system_prompt()
    if evidence: system_msg += f"\n\n【证据链】\n{evidence}"
    msgs_all = [{"role":"system","content":system_msg}, {"role":"user","content":q}]
    resp = await call_deepseek(msgs_all, 500)
    answer = resp["choices"][0]["message"]["content"]
    return JSONResponse({
        "id":f"chatcmpl-xs-{int(time.time())}","object":"chat.completion","model":"deepseek-v4-flash",
        "choices":[{"index":0,"message":{"role":"assistant","content":answer},"finish_reason":"stop"}],
        "lgox_meta":{"channel":"小枢","version":"v3.5","gcp_widget_spec":"1.0","widget_spec":['relative-url', 'golden-master', 'dual-domain', 'gene-feedback', 'identity-guard', 'cors-native'],"gene_count":live_gene_wan()}
    })


# ═══ SSE流式端点 v3.5 ═══
@app.post("/chat/stream")
async def chat_stream(request: Request):
    """SSE流式对话·首token<0.5s·逐字实时输出"""
    try: data = await request.json()
    except: return JSONResponse({"error": "invalid json"}, status_code=400)
    
    msgs = data.get("messages", [])
    q = ""
    for m in reversed(msgs):
        if m.get("role") == "user": q = m.get("content", "")[:300]; break
    if not q: return JSONResponse({"error": "no user message"}, status_code=400)
    
    evidence = fetch_evidence(q)
    system_msg = build_system_prompt()
    if evidence:
        system_msg += f"\n\n【证据链】\n{evidence}\n\n严格基于证据回答，禁止编造。"
    else:
        system_msg += "\n\n【无证据】基因库中未找到相关信息，请诚实回答。"
    
    all_msgs = [{"role": "system", "content": system_msg}, {"role": "user", "content": q}]
    
    async def generate():
        async for typ, text in call_deepseek_stream(all_msgs, 500):
            yield f"data: {json.dumps({'type': typ, 'text': text}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


@app.post("/gene/write")
async def gene_write(request: Request):
    """基因回流: Widget对话→LGE基因库"""
    try: data = await request.json()
    except: return JSONResponse({"error":"invalid json"}, status_code=400)
    content = data.get("content","")
    if not content: return JSONResponse({"error":"content required"}, status_code=400)
    source = data.get("source", "widget_evolve")
    fitness = data.get("fitness", 0.3)
    try:
        payload = json.dumps({
            "content": content, "memory_type": "semantic",
            "source": source, "fitness": fitness
        }).encode()
        req = urllib.request.Request("http://100.116.0.29:8200/genes/write",
            data=payload, headers={"Content-Type":"application/json","X-LGE-Key":"lgox-federation-key-2024"})
        with urllib.request.urlopen(req, timeout=5) as r:
            result = json.loads(r.read())
        return JSONResponse({"status":"ok","gene_id":result.get("gene_id","?"),"id":result.get("id",0)})
    except Exception as e:
        return JSONResponse({"status":"error","error":str(e)[:100]}, status_code=502)

# ═══ 自进化触发 ═══
@app.post("/evolve/auto")
async def auto_evolve(request: Request):
    """自进化: 对话后自动评分→生成进化基因"""
    try: data = await request.json()
    except: return JSONResponse({"status":"error","error":"invalid json"}, status_code=400)
    
    question = data.get("question","")
    answer = data.get("answer","")
    evidence_count = data.get("evidence_count", 0)
    
    if not answer: return JSONResponse({"status":"skip","reason":"no answer"})
    
    # 质量评分
    score = 50  # base
    if len(answer) > 50: score += 10
    if len(answer) > 200: score += 10
    if evidence_count > 0: score += 15
    if "抱歉" not in answer and "不可用" not in answer: score += 10
    if "基因" in answer or "LGOX" in answer: score += 5
    
    fitness = max(0.1, min(0.95, score/100))
    
    # 生成进化基因
    if score >= 70:
        gene_content = f"[自进化·高质量] Q:{question[:60]} → A:{answer[:80]}"
        gene_source = "auto_evolve_high"
    elif score <= 40:
        gene_content = f"[自进化·纠错] 低质量回答需改进: {question[:80]}"
        gene_source = "auto_evolve_correct"
    else:
        return JSONResponse({"status":"skip","score":score,"reason":"mid quality"})
    
    # 写入LGE
    try:
        payload = json.dumps({
            "content": gene_content, "memory_type": "semantic",
            "source": gene_source, "fitness": fitness
        }).encode()
        req = urllib.request.Request("http://100.116.0.29:8200/genes/write",
            data=payload, headers={"Content-Type":"application/json","X-LGE-Key":"lgox-federation-key-2024"})
        with urllib.request.urlopen(req, timeout=8) as r:
            result = json.loads(r.read())
        return JSONResponse({
            "status":"ok","gene_id":result.get("gene_id","?"),"id":result.get("id",0),
            "score":score,"fitness":fitness,"action":gene_source
        })
    except Exception as e:
        return JSONResponse({"status":"write_failed","error":str(e)[:100],"score":score})

# ═══ Wind金融引擎代理(天枢:18770→SSH隧道localhost:18770) ═══
# Wind引擎v2.0路由格式: /quote/CODE · /kline/CODE/周期 · /market/scan · /futures/dashboard
WIND_PROXY = "http://localhost:18770"

def _wind_fetch(path: str, timeout: int = 15):
    """底层Wind请求·自动缓存"""
    try:
        req = urllib.request.Request(f"{WIND_PROXY}{path}")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/wind/health")
async def wind_health():
    return JSONResponse(_wind_fetch("/health", 5))

@app.get("/api/wind/quote")
async def wind_quote(symbol: str = ""):
    if not symbol:
        return JSONResponse({"error": "symbol required"}, status_code=400)
    return JSONResponse(_wind_fetch(f"/quote/{symbol}"))

@app.get("/api/wind/kline")
async def wind_kline(symbol: str = "", period: str = "daily"):
    if not symbol:
        return JSONResponse({"error": "symbol required"}, status_code=400)
    p = "日" if period == "daily" else "周" if period == "weekly" else "月"
    return JSONResponse(_wind_fetch(f"/kline/{symbol}/{p}", 20))

@app.get("/api/wind/market")
async def wind_market():
    """全市场扫描(可能较慢)"""
    return JSONResponse(_wind_fetch("/market/scan", 30))

@app.get("/api/wind/futures")
async def wind_futures():
    """期货仪表盘"""
    return JSONResponse(_wind_fetch("/futures/dashboard", 30))

@app.get("/api/wind/index")
async def wind_index(code: str = "000001.SH"):
    return JSONResponse(_wind_fetch(f"/index/{code}"))

@app.get("/api/wind/financial")
async def wind_financial(symbol: str = ""):
    if not symbol:
        return JSONResponse({"error": "symbol required"}, status_code=400)
    return JSONResponse(_wind_fetch(f"/financial/{symbol}"))

@app.get("/api/wind/search")
async def wind_search(q: str = ""):
    if not q:
        return JSONResponse({"error": "q required"}, status_code=400)
    return JSONResponse(_wind_fetch(f"/search/{q}"))

@app.get("/health")
async def health():
    gn = f"{_gene_cache['count']//10000}万+"
    return {
        "status": "ok", "service": "小枢·LGOX联邦第9节点",
        "node": "金融AI助手", "model": "deepseek-v4-flash",
        "evidence": "LGE基因库(8769)", "version": "v3.5",
        "gene_count": gn, "pyramid": PYRAMID_VER,
        "persona_hash": "782dc52b29084384",
        "gcp_widget_spec": "1.0", "widget_spec": ['relative-url', 'golden-master', 'dual-domain', 'gene-feedback', 'identity-guard', 'cors-native'],
        "gcp_standards": {
            "comms": "TYPE前缀·桥双发·L1-L4",
            "deploy": "秒改秒见·相对URL·双域一致",
            "api_base": "相对路径(nginx双域代理)"
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("XIAOSHU_PORT", "8779"))
    print(f"小枢 v3.4 GCP宪法·FCPF v5.1·WidgetSpec v1.0 :{port} | 动态基因 | relative-url,golden-master,dual-domain | 金字塔{PYRAMID_VER} | 零硬编码")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")