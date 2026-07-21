#!/usr/bin/env python3
"""太一NGC轻量基因引擎 · Windows兼容·NGC免费API·5条/30min"""
import urllib.request, json, time
from datetime import datetime

NGC_KEY = "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"
NGC_API = "https://integrate.api.nvidia.com/v1/chat/completions"
NGC_MODEL = "meta/llama-3.1-8b-instruct"
LGE_URL = "http://100.116.0.29:8200"

TOPICS = [
    "AI Agent memory architecture design patterns",
    "Knowledge graph construction for enterprise AI",
    "Edge computing model optimization techniques", 
    "Federated learning privacy preservation methods",
    "Multi-modal AI data fusion pipelines"
]

def ngc_gen(prompt):
    data = json.dumps({"model":NGC_MODEL,"messages":[{"role":"user","content":prompt}],
        "max_tokens":300,"temperature":0.7}).encode()
    req = urllib.request.Request(NGC_API, data=data,
        headers={"Authorization":"Bearer "+NGC_KEY,"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=25).read())["choices"][0]["message"]["content"]

def lge_write(content):
    try:
        data = json.dumps({"content":content,"memory_type":"semantic","source":"太一NGC",
            "tags":["taiyi","ngc"],"fitness":0.5}).encode()
        req = urllib.request.Request(f"{LGE_URL}/genes/write", data=data,
            headers={"Content-Type":"application/json"})
        return json.loads(urllib.request.urlopen(req,timeout=12).read()).get("gene_id","?")
    except: return None

if __name__ == "__main__":
    ts = datetime.now().strftime("%m%d-%H%M")
    print(f"[{ts}] 太一NGC引擎启动")
    ok = 0
    for topic in TOPICS:
        try:
            c = ngc_gen(f"Generate concise AI knowledge gene about: {topic}. Under 250 chars.")
            if c and len(c) > 30:
                gid = lge_write(c)
                if gid: ok += 1; print(f"  ✅ {gid[:25]}")
        except Exception as e:
            print(f"  ⚠️ {topic[:25]}: {str(e)[:60]}")
        time.sleep(1.5)
    print(f"[{ts}] 完成: +{ok}/5")
