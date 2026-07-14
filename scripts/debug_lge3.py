#!/usr/bin/env python3
import json, urllib.request
LGE = "http://100.116.0.29:8200"
KEY = "lgox-gene-key-2025"

# Test exact queries from the script
queries = [
    "AI machine learning neural network model training inference",
    "python code programming algorithm data structure function",
    "system architecture design pattern framework deployment",
    "database SQL query optimization performance indexing",
]

for q in queries:
    try:
        data = json.dumps({"query": q, "limit": 5, "min_score": 0.0, "status": "active"}).encode()
        req = urllib.request.Request(f"{LGE}/genes/search", data=data,
            headers={"Content-Type": "application/json", "X-LGE-Key": KEY})
        resp = urllib.request.urlopen(req, timeout=10)
        r = json.loads(resp.read())
        results = r.get("results", [])
        low = [g for g in results if g.get("fitness_score", 1.0) < 0.5]
        print(f"q={q[:50]:50s} total={r['count']} low_fitness={len(low)}")
        if results:
            print(f"  first: fitness={results[0].get('fitness_score')}, content={results[0].get('content','')[:60]}")
    except Exception as e:
        print(f"q={q[:50]:50s} ERROR: {e}")
