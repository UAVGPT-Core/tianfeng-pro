#!/usr/bin/env python3
"""Check more local sources for gene count"""
import json, os, glob, re, sqlite3, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Check localhost:8000 for more endpoints
for endpoint in ['/', '/health', '/api/stats/genes', '/api/genes/count', '/stats']:
    try:
        req = urllib.request.Request(f'http://localhost:8000{endpoint}', headers={'User-Agent': 'Check/1.0'})
        with urllib.request.urlopen(req, timeout=3, context=ctx) as r:
            data = r.read().decode()
            print(f"localhost:8000{endpoint} -> {data[:300]}")
    except Exception as e:
        pass

# Check unified-query-api
for endpoint in ['/health', '/api/genes/stats', '/api/stats/genes']:
    for port in [8080, 8081, 9090, 5000]:
        try:
            req = urllib.request.Request(f'http://localhost:{port}{endpoint}', headers={'User-Agent': 'Check/1.0'})
            with urllib.request.urlopen(req, timeout=2, context=ctx) as r:
                data = r.read().decode()
                print(f"localhost:{port}{endpoint} -> {data[:200]}")
        except:
            pass

# Count gene JSON files content for totals
genes_dir = '/Users/a112233/lgox-ops/genes'
total_genes = 0
for f in os.listdir(genes_dir):
    if f.endswith('.json'):
        fp = os.path.join(genes_dir, f)
        try:
            with open(fp) as fh:
                d = json.load(fh)
            if isinstance(d, dict):
                # Count unique entries
                if 'content' in d and d['content']:
                    total_genes += 1
        except:
            pass
print(f"\nTotal gene files with content: {total_genes}")

# Check inbox for gene counts
inbox_dir = '/Users/a112233/lgox-ops/inbox'
inbox_files = [f for f in os.listdir(inbox_dir) if f.endswith('.json')]
print(f"Inbox gene files: {len(inbox_files)}")

# Check any lge database
for db_file in glob.glob('/Users/a112233/lgox-ops/**/*.db', recursive=True):
    print(f"DB: {db_file}")
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        for t in tables:
            tn = t[0]
            c.execute(f"SELECT COUNT(*) FROM \"{tn}\"")
            cnt = c.fetchone()[0]
            print(f"  Table {tn}: {cnt} rows")
        conn.close()
    except:
        pass
