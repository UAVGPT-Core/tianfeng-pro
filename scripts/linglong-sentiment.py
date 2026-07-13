#!/usr/bin/env python3
"""P2: 灵龙新闻情绪分析 - 每15分钟用Ollama分析市场情绪注入LGE"""
import http.client, json, subprocess
from datetime import datetime

LOG = "/Users/a112233/lgox-ops/logs/news-sentiment.log"

def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    with open(LOG, "a") as f:
        f.write(f"[{t}] {msg}\n")
    print(f"[{t}] {msg}")

def ollama_analyze():
    """调用Ollama deepseek-r1:7b分析市场情绪"""
    payload = {
        "model": "deepseek-r1:7b",
        "prompt": "用一句话描述当前中国A股市场的投资者情绪（看多/看空/中性），以及一个简短理由。格式：情绪:xxx 理由:xxx",
        "stream": False,
        "options": {"temperature": 0.3, "max_tokens": 100}
    }
    try:
        conn = http.client.HTTPConnection("localhost", 11434, timeout=30)
        conn.request("POST", "/api/generate", json.dumps(payload), {"Content-Type": "application/json"})
        resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        return data.get("response", "").strip()[:200]
    except Exception as e:
        return f""

def write_to_lge(content):
    """写入LGE基因库"""
    try:
        conn = http.client.HTTPConnection("100.116.0.29", 8200, timeout=15)
        payload = {
            "content": content[:1000],
            "memory_type": "semantic",
            "source": "linglong_sentiment",
            "tags": ["sentiment", "market", "linglong", "ollama", "emotion"],
            "metadata": {"model": "deepseek-r1:7b", "time": datetime.now().isoformat()}
        }
        conn.request("POST", "/genes/write", json.dumps(payload), {"Content-Type": "application/json"})
        resp = conn.getresponse()
        result = json.loads(resp.read())
        conn.close()
        return result.get("gene_id", "ok")
    except Exception as e:
        return f"error: {e}"

def run():
    log("🐉 灵龙情绪分析启动")
    sentiment = ollama_analyze()
    if sentiment:
        content = f"【{datetime.now().strftime('%Y-%m-%d %H:%M')} 灵龙情绪分析】{sentiment}"
        gid = write_to_lge(content)
        log(f"情绪: {sentiment[:60]}... → {gid[:20]}")
    else:
        log("Ollama无输出")
    log("🐉 灵龙情绪分析完成")

if __name__ == "__main__":
    run()
