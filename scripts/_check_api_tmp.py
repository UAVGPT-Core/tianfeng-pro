#!/usr/bin/env python3
"""Temp script to check gene consistency APIs"""
import urllib.request, json, ssl, re
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'LGOX-GeneCheck/1.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode(errors='replace')
    except Exception as e:
        return f"ERROR: {e}"

# 1. API
print("=== API /api/stats/genes ===")
api = fetch("https://stock.uavgpt.com/api/stats/genes")
print(api[:500])

print("\n=== HTML Footer ===")
html = fetch("https://stock.uavgpt.com")
footer = re.findall(r'gene-count-live[^>]*>([^<]+)<', html)
print(f"Footer values: {list(set(footer))}")
target = re.findall(r'data-gene-target="full"[^>]*>\s*([^<]+)\s*<', html)
print(f"data-gene-target=full: {list(set(target))}")

print("\n=== xiaoshu JS ===")
xs = fetch("https://stock.uavgpt.com/public/public/js/xiaoshu-chat.js?v=100")
xs_ver = re.search(r"var\s+VER\s*=\s*'([^']*)'", xs)
xs_gene = re.search(r"_geneText\s*=\s*'([^']*)'", xs)
print(f"VER={xs_ver.group(1) if xs_ver else 'N/A'}")
print(f"_geneText={xs_gene.group(1) if xs_gene else 'N/A'}")

print("\n=== tianxun JS ===")
tx = fetch("https://stock.uavgpt.com/public/public/js/tianxun-v14-living.js?v=14")
tx_ver = re.search(r"var\s+VERSION\s*=\s*'([^']*)'", tx)
tx_gene = re.search(r"_geneText\s*=\s*'([^']*)'", tx)
print(f"VERSION={tx_ver.group(1) if tx_ver else 'N/A'}")
print(f"_geneText={tx_gene.group(1) if tx_gene else 'N/A'}")
