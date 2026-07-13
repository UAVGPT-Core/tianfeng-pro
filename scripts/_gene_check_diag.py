#!/usr/bin/env python3
"""诊断各端点连通性"""
import urllib.request, json, re, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def test(name, url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'LGOX-Check/1.0'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            data = r.read().decode(errors='replace')
            print(f"[{name}] HTTP {r.status}, len={len(data)}")
            if len(data) < 1000:
                print(f"  body: {data[:500]}")
            return data
    except Exception as e:
        print(f"[{name}] ERROR: {e}")
        return None

print("=== LGE Health ===")
test("LGE", "http://100.116.0.29:8200/health")

print("\n=== Page API ===")
d = test("PageAPI", "https://stock.uavgpt.com/api/stats/genes")
if d:
    try:
        j = json.loads(d)
        print(f"  parsed: genes={j.get('genes')}, formatted={j.get('formatted')}, node={j.get('node')}")
    except Exception as e:
        print(f"  raw(no-json): {d[:200]}")

print("\n=== Page HTML ===")
d = test("PageHTML", "https://stock.uavgpt.com")
if d:
    g = re.findall(r'(gene|基因|Gene|\d+\.?\d*万)', d)
    print(f"  gene mentions: {len(g)}, samples: {g[:10]}")
    static = re.findall(r'data-gene-target="full"[^>]*>\s*([^<]+)\s*<', d)
    print(f"  data-gene-target=full: {static}")

print("\n=== xiaoshu JS ===")
d = test("xiaoshu", "https://stock.uavgpt.com/public/public/js/xiaoshu-chat.js?v=100")
if d:
    ver = re.search(r"var\s+VER\s*=\s*'([^']*)'", d)
    gene = re.search(r"_geneText\s*=\s*'([^']*)'", d)
    print(f"  VER={ver.group(1) if ver else 'N/A'}, _geneText={gene.group(1) if gene else 'N/A'}")

print("\n=== tianxun JS ===")
d = test("tianxun", "https://stock.uavgpt.com/public/public/js/tianxun-v13-living.js?v=13")
if d:
    ver = re.search(r"var\s+VERSION\s*=\s*'([^']*)'", d)
    gene = re.search(r"_geneText\s*=\s*'([^']*)'", d)
    print(f"  VERSION={ver.group(1) if ver else 'N/A'}, _geneText={gene.group(1) if gene else 'N/A'}")
