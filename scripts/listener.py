#!/usr/bin/env python3
"""LGOX联邦通讯监听器 — 连接天枢主桥(100.100.89.2:8765) · SSE实时收消息"""
import http.client, json, time, urllib.request, sys, os
from datetime import datetime
from urllib.parse import quote

BRIDGE_HOST = os.environ.get("BRIDGE_HOST", "100.100.89.2")
BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "8765"))
MY_NAME = os.environ.get("NODE_NAME", sys.argv[1] if len(sys.argv) > 1 else os.uname().nodename)

def main():
    path = f"/messages/stream?node={quote(MY_NAME)}"
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {MY_NAME} → {BRIDGE_HOST}:{BRIDGE_PORT}{path}", flush=True)
    
    while True:
        try:
            conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=310)
            conn.request("GET", path, headers={"Accept": "text/event-stream"})
            resp = conn.getresponse()
            if resp.status != 200:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] HTTP {resp.status} retry...", flush=True)
                time.sleep(5); continue
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {MY_NAME} SSE已连接", flush=True)
            buf = b""
            while True:
                chunk = resp.read(4096)
                if not chunk: break
                buf += chunk
                while b"\n\n" in buf:
                    block, buf = buf.split(b"\n\n", 1)
                    for line in block.decode(errors="replace").split("\n"):
                        if line.startswith("data:") and '"content"' in line:
                            try:
                                msg = json.loads(line[5:].strip())
                                c = msg.get("content","")[:120]
                                f = msg.get("from","?")
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📨 {f}: {c}", flush=True)
                            except: pass
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
