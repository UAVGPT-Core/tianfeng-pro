#!/usr/bin/env python3
"""Check local LGE approach"""
import json, os, glob

# Check genes directory
genes_dir = '/Users/a112233/lgox-ops/genes'
gene_files = [f for f in os.listdir(genes_dir) if f.endswith('.json')]
print(f"Gene JSON files: {len(gene_files)}")
# Read first one to see structure
if gene_files:
    with open(os.path.join(genes_dir, gene_files[0])) as f:
        d = json.load(f)
        print(f"Sample gene keys: {list(d.keys()) if isinstance(d, dict) else type(d).__name__}")

# Check LGE meta for total counts
meta_dir = '/Users/a112233/lgox-ops/lge-genes/meta'
meta_files = os.listdir(meta_dir)
print(f"\nLGE meta files: {len(meta_files)}")
# Look for any stats/summary
for mf in sorted(meta_files)[-5:]:
    mp = os.path.join(meta_dir, mf)
    try:
        with open(mp) as f:
            d = json.load(f)
        # Check for gene counts
        if isinstance(d, dict):
            for k in ['genes', 'gene_count', 'total', 'total_genes', 'count']:
                if k in d:
                    print(f"  {mf}: {k}={d[k]}")
    except:
        pass

# Check if LGE API is running locally
import urllib.request, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
for port in [8081, 8200, 5000, 8000]:
    try:
        req = urllib.request.Request(f'http://localhost:{port}/health', headers={'User-Agent': 'Check/1.0'})
        with urllib.request.urlopen(req, timeout=3, context=ctx) as r:
            data = r.read().decode()
            print(f"\nLocalhost:{port} - {data[:200]}")
    except Exception as e:
        pass

# Check running processes for LGE
import subprocess
try:
    r = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
    for line in r.stdout.split('\n'):
        if 'lge' in line.lower() or 'gene' in line.lower() or '8200' in line:
            print(f"Process: {line.strip()[:120]}")
except:
    pass
