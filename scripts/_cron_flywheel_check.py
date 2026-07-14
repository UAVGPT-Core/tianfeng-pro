#!/usr/bin/env python3
import sqlite3, json
from pathlib import Path
HOME = Path.home()
FLYWHEEL_DB = HOME / 'lgox-ops/data/gene-coding-flywheel.db'
conn = sqlite3.connect(str(FLYWHEEL_DB))
c = conn.cursor()
print('=== LAST 10 RUNS ===')
c.execute('SELECT run_id, genes_searched, genes_injected, new_genes, score, duration_ms, created_at FROM flywheel_runs ORDER BY id DESC LIMIT 10')
for r in c.fetchall():
    print(f'{r[0][:22]:22s} s={r[1]} i={r[2]} n={r[3]} score={r[4]:3d} dur={r[5]}ms {r[6]}')
print()
r = c.execute('SELECT COUNT(*), AVG(score), SUM(new_genes), SUM(genes_injected), SUM(genes_searched) FROM flywheel_runs').fetchone()
print(f'Total runs: {r[0]}, Avg score: {r[1]:.1f}, New genes: {r[2]}, Injected: {r[3]}, Searched: {r[4]}')
print()
r = c.execute('SELECT COUNT(*) FROM code_genes').fetchone()
print(f'Code genes in DB: {r[0]}')
c.execute('SELECT score FROM flywheel_runs ORDER BY id DESC LIMIT 10')
scores = [s[0] for s in c.fetchall()]
print(f'Recent avg score: {sum(scores)/len(scores):.1f}')
conn.close()
