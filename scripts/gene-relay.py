#!/usr/bin/env python3
"""
灵龙基因中继站 — 多路基因写入代理
接收天枢的基因写入请求，转发到地枢LGE
Path1: 地枢直连(8200) · Path2: 灵龙桥转发 · Path3: 本地缓存兜底
"""
import http.server, json, urllib.request, sys, os, threading

PORT = 18770
LGE_URL = "http://100.116.0.29:8200/genes/write"
CACHE_DIR = os.path.expanduser("~/lgox-ops/lge-genes/pending")

os.makedirs(CACHE_DIR, exist_ok=True)

class GeneRelay(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        
        # Path1: 地枢直连
        result = None
        for path_name, url in [
            ("地枢直连", LGE_URL),
            ("地枢export转发", "http://100.116.0.29:8200/genes/write"),
        ]:
            try:
                req = urllib.request.Request(url, data=body,
                    headers={"Content-Type": "application/json"}, method="POST")
                r = urllib.request.urlopen(req, timeout=5)
                result = {"path": path_name, "status": r.status, "body": r.read().decode()[:200]}
                break
            except Exception as e:
                continue
        
        if not result:
            # Path3: 缓存兜底 — 写入本地pending目录，cron定期重试
            ts = __import__('time').strftime("%Y%m%d-%H%M%S")
            cache_file = os.path.join(CACHE_DIR, f"gene-{ts}.json")
            with open(cache_file, 'wb') as f:
                f.write(body)
            result = {"path": "cache", "status": "cached", "file": cache_file}
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
    
    def do_GET(self):
        # Health + 缓存状态
        pending = len([f for f in os.listdir(CACHE_DIR) if f.endswith('.json')])
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "service": "基因中继站",
            "status": "ok",
            "pending_cache": pending,
            "lge": LGE_URL
        }, ensure_ascii=False).encode())

if __name__ == "__main__":
    server = http.server.HTTPServer(('0.0.0.0', PORT), GeneRelay)
    print(f"基因中继站启动 :{PORT}")
    server.serve_forever()
