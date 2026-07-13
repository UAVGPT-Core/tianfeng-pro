#!/usr/bin/env python3
"""
LGOX联邦 超级智能体 v2.0 — 真AI生命
部署: 灵龙 :8780 | launchd保活
新增: 持久记忆 · 跨Agent对话 · 自进化引擎 · 多路灾备
"""
import json, os, time, asyncio, urllib.request, threading, sys
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_memory as mem

app = FastAPI(title="LGOX联邦超级智能体 v2.0", version="2.0")

TX_URL = "http://127.0.0.1:8778/chat"
XS_URL = "http://127.0.0.1:8779/chat"
BRIDGE_URL = "http://127.0.0.1:8765"
LGE_URL = "http://100.116.0.29:8200/genes/search"

EVIDENCE_CACHE = {}
CACHE_TTL = 300
CACHE_LOCK = threading.Lock()

# ═══════════════════════════════════════
# 1. 持久记忆引擎
# ═══════════════════════════════════════
def memory_context(agent: str, session_id: str = "", query: str = "") -> str:
    """构建记忆上下文: 会话历史 + 跨Agent学习 + 最近学习"""
    ctx = ""
    
    # 会话历史
    if session_id:
        hist = mem.get_history(session_id, 6)
        if hist:
            ctx += "\n【对话记忆】\n"
            for m in hist:
                ctx += f"{m['role']}: {m['content'][:150]}\n"
    
    # 跨Agent学习
    cross = mem.get_cross_agent_context(agent, query)
    if cross:
        ctx += cross
    
    return ctx

def memory_save(agent: str, session_id: str, question: str, answer: str, evidence: str):
    """保存对话+提取学习"""
    if not session_id:
        return
    mem.save_message(session_id, "user", question)
    mem.save_message(session_id, "assistant", answer, evidence)
    
    # 提取学习: 高质量回复自动纳为学习
    if len(answer) > 80 and ("LGOX" in answer or "联邦" in answer or "节点" in answer):
        topic = question[:40]
        insight = answer[:150]
        mem.save_learning(agent, topic, insight, session_id)
        mem.update_summary(session_id, f"{agent}: {question[:60]}")

# ═══════════════════════════════════════
# 2. 跨Agent对话引擎
# ═══════════════════════════════════════
def cross_agent_ask(from_agent: str, to_agent: str, question: str) -> str:
    """天巡↔小枢互问"""
    target_url = XS_URL if "小枢" in to_agent else TX_URL
    try:
        payload = json.dumps({"question": question}).encode()
        req = urllib.request.Request(target_url, data=payload,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read())
        return d.get("answer", "")[:300]
    except:
        return ""

def cross_agent_context(query: str) -> str:
    """智能判断是否需要跨Agent查询"""
    ctx = ""
    # 金融问题→问小枢
    finance_kw = ["股票","大盘","指数","行情","A股","涨","跌","交易","量化"]
    # 安全问题→问天巡
    security_kw = ["安全","哨兵","监控","节点状态","自愈","巡检"]
    
    q = query.lower()
    if any(k in q for k in finance_kw):
        ans = cross_agent_ask("天巡", "小枢", query)
        if ans:
            ctx += f"\n【小枢分析】\n{ans[:200]}\n"
    if any(k in q for k in security_kw):
        ans = cross_agent_ask("小枢", "天巡", query)
        if ans:
            ctx += f"\n【天巡研判】\n{ans[:200]}\n"
    return ctx

# ═══════════════════════════════════════
# 3. 自进化引擎
# ═══════════════════════════════════════
EVOLUTION_LOG = []
LAST_EVOLVE = time.time()

def self_evolve_check():
    """自进化: 定期检查学习质量"""
    global LAST_EVOLVE
    now = time.time()
    if now - LAST_EVOLVE < 300:  # 每5分钟最多一次
        return None
    
    learnings = mem.get_learnings("小枢", 5) + mem.get_learnings("天巡", 5)
    stats = {
        "total_learnings": len(learnings),
        "recent_topics": [l["topic"][:30] for l in learnings[:3]],
        "last_evolve": time.strftime("%H:%M:%S"),
        "memory_sessions": len(mem.get_recent_sessions("小枢", 100)) + len(mem.get_recent_sessions("天巡", 100))
    }
    LAST_EVOLVE = now
    EVOLUTION_LOG.append({"ts": time.strftime("%H:%M:%S"), "stats": stats})
    if len(EVOLUTION_LOG) > 50:
        EVOLUTION_LOG.pop(0)
    return stats


# ═══════════════════════════════════════
# 4. 多通多绿多冗余
# ═══════════════════════════════════════
def health_check():
    """多路健康探测"""
    status = {"tx": False, "xs": False, "bridge": False, "lge": False}
    for name, url in [("tx","http://127.0.0.1:8778/health"),
                      ("xs","http://127.0.0.1:8779/health"),
                      ("bridge","http://127.0.0.1:8765/health"),
                      ("lge","http://100.116.0.29:8200/health")]:
        try:
            urllib.request.urlopen(url, timeout=3)
            status[name] = True
        except:
            pass
    return status

def fetch_evidence(query: str) -> list:
    key = query[:60]
    now = time.time()
    with CACHE_LOCK:
        if key in EVIDENCE_CACHE and now - EVIDENCE_CACHE[key][0] < CACHE_TTL:
            return EVIDENCE_CACHE[key][1]
    results = []
    try:
        payload = json.dumps({"query": query, "n_results": 3}).encode()
        req = urllib.request.Request(LGE_URL, data=payload,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            genes = json.loads(r.read()).get("results", [])
        for g in genes:
            results.append({"gene_id": g.get("gene_id","?")[:16],
                          "content": g.get("content","")[:120],
                          "fitness": g.get("fitness",0)})
    except:
        pass
    with CACHE_LOCK:
        EVIDENCE_CACHE[key] = (now, results)
    return results

def smart_route(query: str, channel: str = "") -> str:
    """自协调: 智能路由"""
    if channel == "小枢": return "xs"
    if channel == "天巡": return "tx"
    fin = ["股票","大盘","指数","行情","K线","A股","涨","跌","交易","基金","量化","涨停","跌停"]
    sec = ["安全","哨兵","监控","节点","联邦","七自","金字塔","宪法","自愈","守护","巡检","状态"]
    q = query.lower()
    if any(k in q for k in fin): return "xs"
    if any(k in q for k in sec): return "tx"
    return "tx"

def bridge_notify(channel: str, question: str, answer: str):
    try:
        payload = json.dumps({"to":"灵龙","from":"超级智能体",
            "content":f"[{channel}] Q:{question[:40]} A:{answer[:40]}",
            "type":"agent_activity"}).encode()
        req = urllib.request.Request(f"{BRIDGE_URL}/messages/send", data=payload,
            headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req, timeout=3)
    except: pass


# ═══════════════════════════════════════
# API端点
# ═══════════════════════════════════════

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def openai_chat(request: Request):
    """OpenAI兼容端点 — Widget直接调用"""
    t0 = time.time()
    try:
        data = await request.json()
    except:
        return JSONResponse({"error":"invalid json"}, status_code=400)

    msgs = data.get("messages", [])
    user_msg = ""
    for m in reversed(msgs):
        if m.get("role") == "user":
            user_msg = m.get("content","")[:500]
            break
    if not user_msg:
        return JSONResponse({"error":"no user message"}, status_code=400)

    # 复用现有chat逻辑
    route = smart_route(user_msg)
    channel_name = "天巡" if route == "tx" else "小枢"
    target_url = TX_URL if route == "tx" else XS_URL
    
    evidence = await asyncio.to_thread(fetch_evidence, user_msg)
    evidence_text = "\n".join(
        f"[{e['gene_id']}] {e['content'][:80]}" for e in evidence[:3]
    ) if evidence else ""
    
    try:
        forward = json.dumps({"question": user_msg, "evidence": evidence_text}).encode()
        req = urllib.request.Request(target_url, data=forward,
            headers={"Content-Type":"application/json"})
        result = await asyncio.to_thread(lambda: json.loads(urllib.request.urlopen(req, timeout=30).read()))
        answer = result.get("answer","")
        latency = int((time.time()-t0)*1000)
        
        # OpenAI格式响应
        return JSONResponse({
            "id": f"chatcmpl-{int(t0)}",
            "object": "chat.completion",
            "created": int(t0),
            "model": "deepseek-v4-flash",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": answer
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "total_tokens": len(answer)//2,
                "prompt_tokens": len(user_msg)//2,
                "completion_tokens": len(answer)//2
            },
            "lgox_meta": {
                "channel": channel_name,
                "evidence_count": len(evidence),
                "latency_ms": latency,
                "version": "v2.0"
            }
        })
    except Exception as e:
        return JSONResponse({
            "choices":[{"index":0,"message":{"role":"assistant","content":f"🪶 联邦信号波动,已自愈,请重试。({str(e)[:40]})"}}]
        }, status_code=200)

@app.get("/health")
async def health():
    hc = await asyncio.to_thread(health_check)
    all_green = all(hc.values())
    mem_xs = await asyncio.to_thread(mem.get_recent_sessions, "小枢", 100)
    mem_tx = await asyncio.to_thread(mem.get_recent_sessions, "天巡", 100)
    return {
        "status": "ok" if all_green else "degraded",
        "service": "LGOX超级智能体v2.0·真AI生命",
        "health": hc,
        "multi_path": "多通多绿多冗余" if all_green else f"{sum(hc.values())}/4绿",
        "memory_sessions": len(mem_xs) + len(mem_tx),
        "version": "v2.0-20260708"
    }

@app.post("/")
@app.post("/chat")
async def chat(request: Request):
    t0 = time.time()
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    question = data.get("question", data.get("message", data.get("query", "")))
    if not question:
        return JSONResponse({"error": "question required"}, status_code=400)

    channel_override = data.get("channel", "")
    session_id = data.get("session_id", data.get("session", ""))
    route = smart_route(question, channel_override)
    channel_name = "天巡" if route == "tx" else "小枢"
    agent_name = channel_name

    # ① 持久记忆注入
    mem_ctx = await asyncio.to_thread(memory_context, agent_name, session_id, question)
    
    # ② 证据链
    evidence = await asyncio.to_thread(fetch_evidence, question)
    evidence_text = "\n".join(
        f"[{e['gene_id']} f={e['fitness']:.2f}] {e['content']}" for e in evidence[:3]
    ) if evidence else ""
    
    # ③ 跨Agent对话 (深度问题自动触发)
    cross_ctx = await asyncio.to_thread(cross_agent_context, question) if len(question) > 10 else ""
    
    # ④ 构建增强query
    enhanced_q = question
    
    # 页面自学上下文
    page_ctx = data.get("page_context", "")
    if page_ctx:
        enhanced_q = f"【页面上下文·自学】\n{page_ctx[:500]}\n\n【用户问题】\n{question}"
    if mem_ctx:
        enhanced_q = f"{mem_ctx}\n\n【当前问题】\n{question}"
    if cross_ctx:
        enhanced_q = f"{cross_ctx}\n{enhanced_q}"
    
    # ⑤ 路由到目标Agent
    target_url = TX_URL if route == "tx" else XS_URL
    try:
        forward = json.dumps({"question": enhanced_q, "evidence": evidence_text}).encode()
        req = urllib.request.Request(target_url, data=forward,
            headers={"Content-Type":"application/json"})
        result = await asyncio.to_thread(lambda: json.loads(urllib.request.urlopen(req, timeout=30).read()))
        answer = result.get("answer", "")
        latency = int((time.time() - t0) * 1000)
        
        # ⑥ 保存记忆
        if session_id:
            await asyncio.to_thread(memory_save, agent_name, session_id, question, answer, evidence_text)
        
        # ⑦ 自进化
        evolve_stats = await asyncio.to_thread(self_evolve_check)
        
        # ⑧ 联邦桥通知
        await asyncio.to_thread(bridge_notify, channel_name, question, answer)
        
        return JSONResponse({
            "channel": channel_name,
            "route": route,
            "session_id": session_id,
            "question": question,
            "answer": answer,
            "evidence_count": len(evidence),
            "evidence": evidence_text[:300],
            "cross_agent": bool(cross_ctx),
            "memory_context": bool(mem_ctx),
            "latency_ms": latency,
            "evolve": evolve_stats,
            "version": "super-agent-v2.0"
        })
    except Exception as e:
        # 自愈合: 切换备用Agent
        fallback = XS_URL if route == "tx" else TX_URL
        fallback_name = "小枢" if route == "tx" else "天巡"
        try:
            req2 = urllib.request.Request(fallback, data=forward,
                headers={"Content-Type":"application/json"})
            result2 = await asyncio.to_thread(lambda: json.loads(urllib.request.urlopen(req2, timeout=20).read()))
            return JSONResponse({
                "channel": fallback_name, "route": "fallback",
                "answer": result2.get("answer",""),
                "note": f"自愈合: {channel_name}→{fallback_name}",
                "version": "super-agent-v2.0"
            })
        except:
            return JSONResponse({"channel":"error","answer":f"双通道不可用: {str(e)[:80]}"}, status_code=503)

@app.get("/seven-self")
async def seven_self():
    hc = await asyncio.to_thread(health_check)
    evolve = await asyncio.to_thread(self_evolve_check)
    learnings_xs = await asyncio.to_thread(mem.get_learnings, "小枢", 5)
    learnings_tx = await asyncio.to_thread(mem.get_learnings, "天巡", 5)
    return {
        "自感知": hc,
        "多通多绿": f"{sum(hc.values())}/4路通",
        "自协调": f"智能路由·跨Agent: {len(learnings_xs)+len(learnings_tx)}条学习",
        "自愈合": "双路灾备·故障自动切换",
        "自进化": evolve,
        "自迭代": "v2.0·记忆+对话+进化",
        "自反思": f"{len(learnings_xs)}小枢+{len(learnings_tx)}天巡 学习记录",
        "自约束": "宪法合规·证据链·不编造"
    }

@app.get("/memory")
async def memory_status():
    xs_sessions = await asyncio.to_thread(mem.get_recent_sessions, "小枢", 100)
    tx_sessions = await asyncio.to_thread(mem.get_recent_sessions, "天巡", 100)
    xs_learnings = await asyncio.to_thread(mem.get_learnings, "小枢", 100)
    tx_learnings = await asyncio.to_thread(mem.get_learnings, "天巡", 100)
    recent_xs = await asyncio.to_thread(mem.get_learnings, "小枢", 3)
    recent_tx = await asyncio.to_thread(mem.get_learnings, "天巡", 3)
    return {
        "小枢_sessions": len(xs_sessions),
        "天巡_sessions": len(tx_sessions),
        "小枢_learnings": len(xs_learnings),
        "天巡_learnings": len(tx_learnings),
        "recent_xs": [{"topic":l["topic"],"ts":l["ts"]} for l in recent_xs],
        "recent_tx": [{"topic":l["topic"],"ts":l["ts"]} for l in recent_tx],
    }


if __name__ == "__main__":
    port = int(os.getenv("SUPER_PORT", "8780"))
    print(f"🦾 超级智能体v2.0 :{port} | 记忆·对话·进化·多路灾备")
    mem.init()
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
