#!/usr/bin/env python3
"""
LGOX智能应答代理 v1.0 — 证据链+评测三联
端口:8773
流程: 用户提问→8769证据链→转发LLM→8771评测→返回(答案+证据+评分)
基因ID: GENE-PRO-smart-proxy-v1
"""
import json, time, threading, urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

QUERY_URL = "http://127.0.0.1:8769/query"
EVAL_URL = "http://127.0.0.1:8771/eval"

# 天巡后端(地枢·Qwen)
TIANKUN_URL = "http://100.116.0.29:8761/v1/chat/completions"
# 小枢后端(地枢·Qwen)
XIAOSHU_URL = "http://100.116.0.29:8001/v1/chat/completions"

def query_evidence(question: str) -> list:
    """查询证据链"""
    try:
        payload = json.dumps({"query": question, "timeout": 5}).encode()
        req = urllib.request.Request(QUERY_URL, data=payload,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as r:
            d = json.loads(r.read())
        return d.get("evidence", [])
    except:
        return []

def call_llm(question: str, backend: str = "tianxun") -> str:
    """调用LLM后端"""
    url = TIANKUN_URL if backend == "tianxun" else XIAOSHU_URL
    try:
        payload = json.dumps({
            "model": "qwen2.5-coder:7b",
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 300, "temperature": 0.3
        }).encode()
        req = urllib.request.Request(url, data=payload,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
        return d["choices"][0]["message"]["content"]
    except:
        return "[LLM不可达] 请稍后重试"

def async_eval(question: str, answer: str):
    """异步评测"""
    def _eval():
        try:
            payload = json.dumps({"question": question, "answer": answer}).encode()
            req = urllib.request.Request(EVAL_URL, data=payload,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3)
        except:
            pass
    threading.Thread(target=_eval, daemon=True).start()

class SmartProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path == "/health":
            self._json({"status":"ok","service":"LGOX智能应答代理","version":"1.0",
                "tianxun_backend": TIANKUN_URL, "features": ["证据链","评测三联"]})

    def do_POST(self):
        path = urlparse(self.path).path
        content_len = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_len)) if content_len else {}

        if path == "/chat" or path == "/chat/tianxun":
            question = body.get("question", body.get("q", body.get("message", "")))
            backend = body.get("backend", "tianxun")
            if not question:
                self._json({"error": "question必填"}, 400)
                return

            t0 = time.time()
            # Phase 1: 证据链
            evidence = query_evidence(question)
            # Phase 2: LLM应答
            answer = call_llm(question, backend)
            # Phase 3: 异步评测
            async_eval(question, answer)

            self._json({
                "question": question,
                "answer": answer,
                "evidence": evidence[:5],
                "evidence_count": len(evidence),
                "backend": backend,
                "latency_ms": round((time.time() - t0) * 1000)
            })
        elif path == "/chat/xiaoshu":
            body["backend"] = "xiaoshu"
            self.do_POST()  # fallback to /chat handler
        else:
            self._json({"error": "use POST /chat or /chat/tianxun"}, 404)

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    def log_message(self, *args): pass

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8773
    print(f"🧠 智能应答代理 :{port} → 8769证据·LLM应答·8771评测")
    HTTPServer(('127.0.0.1', port), SmartProxyHandler).serve_forever()
