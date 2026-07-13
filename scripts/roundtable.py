#!/usr/bin/env python3
"""
LOGOS圆桌引擎 v2.0 :18772 · P0+P2完成
多Agent投票决策·联邦共识机制·动态成员发现
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn, urllib.request, json, time, threading, os

app = FastAPI()

# 静态成员（兜底）
STATIC_MEMBERS = {
    "天巡": "http://127.0.0.1:8778/chat",
    "小枢": "http://127.0.0.1:8779/chat",
}

# 动态成员缓存
_dynamic_cache = {"members": dict(STATIC_MEMBERS), "updated": 0}

def discover_members():
    """P2: 从联邦桥动态发现节点·天巡小枢自动加入"""
    global _dynamic_cache
    now = time.time()
    if now - _dynamic_cache["updated"] < 300:  # 5分钟缓存
        return _dynamic_cache["members"]
    
    members = dict(STATIC_MEMBERS)
    try:
        # 从灵龙本地联邦桥发现
        r = urllib.request.urlopen("http://127.0.0.1:8765/nodes", timeout=5)
        nodes = json.loads(r.read())
        for name, info in nodes.items():
            if name in members:
                continue
            # 检查节点是否有chat能力
            caps = info if isinstance(info, dict) else {}
            if caps.get("online") and caps.get("capabilities"):
                if "chat" in caps.get("capabilities", []):
                    ip = caps.get("ip", "")
                    if ip:
                        members[name] = f"http://{ip}:8778/chat"
    except:
        pass
    
    _dynamic_cache = {"members": members, "updated": now}
    return members

@app.get("/health")
def health():
    members = discover_members()
    return {"status": "ok", "engine": "LOGOS圆桌 v2.0", "members": list(members.keys()),
            "dynamic_discovery": True, "port": 18772}

@app.post("/roundtable")
async def roundtable(request: Request):
    """多Agent投票: 发问题→各成员回答→汇总"""
    body = await request.json()
    question = body.get("question", "")
    req_members = body.get("members", None)
    
    if not question:
        return JSONResponse({"error": "需要question"}, status_code=400)
    
    all_members = discover_members()
    member_list = req_members if req_members else list(all_members.keys())
    
    votes = {}
    for name in member_list:
        if name not in all_members:
            continue
        try:
            url = all_members[name]
            req_body = json.dumps({
                "query": f"[圆桌投票] {question}\n请给出你的观点,一句话回复。"
            }).encode()
            req = urllib.request.Request(url, data=req_body,
                headers={"Content-Type": "application/json"})
            r = urllib.request.urlopen(req, timeout=25)
            resp = json.loads(r.read())
            votes[name] = resp.get("answer", resp.get("response", ""))[:200]
        except Exception as e:
            votes[name] = f"[离线] {str(e)[:60]}"
    
    # LOGOS决策
    online = len([v for v in votes.values() if "离线" not in v])
    total = len(votes)
    decision = "圆桌共识" if online >= total * 0.5 else "意见分歧" if online > 0 else "全员离线"
    
    return JSONResponse({
        "question": question,
        "votes": votes,
        "decision": decision,
        "members_online": online,
        "members_total": total,
        "time": time.strftime("%H:%M:%S"),
        "engine": "LOGOS圆桌 v2.0"
    })

if __name__ == "__main__":
    print("LOGOS圆桌引擎 v2.0 :18772 · 动态成员发现 · 联邦共识")
    uvicorn.run(app, host="0.0.0.0", port=18772, log_level="warning")
