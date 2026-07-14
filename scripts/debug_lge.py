#!/usr/bin/env python3
"""Debug: inspect LGE search response format"""
import json, urllib.request

LGE_URL = "http://100.116.0.29:8200"
LGE_KEY = "lgox-gene-key-2025"

# Test search
data = json.dumps({"query": "技术 AI", "limit": 5, "min_score": 0.0, "status": "active"}).encode()
req = urllib.request.Request(f"{LGE_URL}/genes/search", data=data,
    headers={"Content-Type": "application/json", "X-LGE-Key": LGE_KEY})
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read())

print(f"Keys: {list(result.keys())}")
results = result.get("results", [])
print(f"Count: {len(results)}")
if results:
    r0 = results[0]
    print(f"First result keys: {list(r0.keys())}")
    for k in r0:
        v = r0[k]
        if isinstance(v, str) and len(v) > 80:
            v = v[:80] + "..."
        print(f"  {k}: {v}")
    # Check fitness values
    for r in results[:5]:
        fs = r.get("fitness_score", "MISSING")
        gid = r.get("gene_id", "?")[:20]
        print(f"  gene={gid} fitness={fs}")
else:
    print("NO RESULTS")
