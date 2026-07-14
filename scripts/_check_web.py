#!/usr/bin/env python3
"""Check local web/genome endpoints for gene count"""
import urllib.request, json, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'LGOX-GeneCheck/1.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode(errors='replace')
    except Exception as e:
        return f"ERROR: {e}"

# Check stock.uavgpt.com API with longer timeout
print("=== stock.uavgpt.com checks ===")
for ep in ['/api/stats/genes', '/api/genes/count', '/api/stats', '/health']:
    result = fetch(f"https://stock.uavgpt.com{ep}", timeout=15)
    print(f"{ep}: {result[:200]}")

# Check HTML footer more carefully  
print("\n=== HTML Footer ===")
html = fetch("https://stock.uavgpt.com", timeout=15)
if html and not html.startswith("ERROR"):
    # Find all gene-related patterns
    gene_patterns = re.findall(r'gene[^>]*>([^<]+)<', html)
    print(f"gene patterns: {gene_patterns[:20]}")
    count_patterns = re.findall(r'[\d.]+万[+]?', html)
    print(f"count patterns: {count_patterns[:20]}")
else:
    print(f"HTML fetch error: {html}")

# Check local unified-query-api
print("\n=== Unified Query API (local) ===")
for port in [8080, 8081, 9090]:
    for ep in ['/health', '/api/genes']:
        result = fetch(f"http://localhost:{port}{ep}", timeout=3)
        if not result.startswith("ERROR"):
            print(f"localhost:{port}{ep}: {result[:200]}")
