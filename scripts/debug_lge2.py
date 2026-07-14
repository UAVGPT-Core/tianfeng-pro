#!/usr/bin/env python3
import json, urllib.request
LGE = "http://100.116.0.29:8200"
KEY = "lgox-gene-key-2025"
for q in ["AI", "system", "data", "code", "LGOX", "model", "neural", "python", "federation"]:
    try:
        data = json.dumps({"query": q, "limit": 3, "min_score": 0.0}).encode()
        req = urllib.request.Request(f"{LGE}/genes/search", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": KEY})
        resp = urllib.request.urlopen(req, timeout=10)
        r = json.loads(resp.read())
        results = r.get("results", [])
        if results:
            r0 = results[0]
            fs = r0.get("fitness_score", "MISSING")
            print(f"q={q:15s} count={r['count']} first_fitness={fs} keys={list(r0.keys())[:8]}")
        else:
            print(f"q={q:15s} count=0")
    except Exception as e:
        print(f"q={q:15s} ERROR: {e}")
