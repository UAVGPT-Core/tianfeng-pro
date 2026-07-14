#!/usr/bin/env python3
"""Analyze gene-coding-flywheel DB for cron report."""
import sqlite3, json
from pathlib import Path

HOME = Path.home()
FLYWHEEL_DB = HOME / 'lgox-ops/data/gene-coding-flywheel.db'
conn = sqlite3.connect(str(FLYWHEEL_DB))
c = conn.cursor()

print('=== LAST 10 RUNS ===')
c.execute('SELECT run_id, genes_searched, genes_injected, new_genes, score, duration_ms, created_at FROM flywheel_runs ORDER BY id DESC LIMIT 10')
for r in c.fetchall():
    print(f'  {r[0][:22]:22s}  search={r[1]} inj={r[2]} new={r[3]} score={r[4]:3d} dur={r[5]}ms  {r[6]}')

print()
print('=== SUMMARY ===')
r = c.execute('SELECT COUNT(*), AVG(score), SUM(new_genes), SUM(genes_injected), SUM(genes_searched) FROM flywheel_runs').fetchone()
print(f'  Total runs: {r[0]}, Avg score: {r[1]:.1f}, Total new genes: {r[2]}, Total injected: {r[3]}, Total searched: {r[4]}')

print()
print('=== CODE GENES ===')
r = c.execute('SELECT COUNT(*) FROM code_genes').fetchone()
print(f'  Total code genes in DB: {r[0]}')
c.execute('SELECT gene_id, category, source, score, created_at FROM code_genes ORDER BY id DESC LIMIT 10')
for g in c.fetchall():
    print(f'  {g[0]} cat={g[1]} score={g[3]:.0f} {g[4]}')

print()
print('=== TREND: last 10 scores ===')
c.execute('SELECT score, created_at FROM flywheel_runs ORDER BY id DESC LIMIT 10')
scores = c.fetchall()
avg_s = sum(s[0] for s in scores) / len(scores)
print(f'  Recent avg: {avg_s:.1f}')
for s in scores:
    bar = '█' * (s[0] // 5) + '░' * (20 - s[0] // 5)
    print(f'  {bar} {s[0]:3d}  {s[1]}')

print()
print('=== LGE CONNECTIVITY CHECK ===')
import urllib.request
for url, label in [('http://100.116.0.29:8200', '地枢DGX2'), ('http://100.100.89.2:8201', '天枢LGE'), ('http://127.0.0.1:8202', '灵龙LGA')]:
    try:
        r = urllib.request.urlopen(url + '/health', timeout=3)
        print(f'  {label:12s} ✅ {r.status}')
    except Exception as e:
        print(f'  {label:12s} ❌ {str(e)[:40]}')

conn.close()
