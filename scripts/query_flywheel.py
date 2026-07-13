#!/usr/bin/env python3
"""Query gene-coding-flywheel DB for this cron run's context."""
import sqlite3, json
from pathlib import Path

HOME = Path.home()
FLYWHEEL_DB = HOME / 'lgox-ops/data/gene-coding-flywheel.db'
conn = sqlite3.connect(str(FLYWHEEL_DB))
c = conn.cursor()

print('=== LAST 10 RUNS ===')
for r in c.execute('SELECT run_id, genes_searched, genes_injected, new_genes, score, duration_ms, created_at FROM flywheel_runs ORDER BY id DESC LIMIT 10'):
    print(json.dumps(list(r)))

print()
print('=== SUMMARY ===')
r = c.execute('SELECT COUNT(*), AVG(score), SUM(new_genes), SUM(genes_injected), SUM(genes_searched) FROM flywheel_runs').fetchone()
print(f'Total runs: {r[0]}, Avg score: {r[1]:.1f}, Total new genes: {r[2]}, Total injected: {r[3]}, Total searched: {r[4]}')

print()
print('=== CODE GENES ===')
r = c.execute('SELECT COUNT(*) FROM code_genes').fetchone()
print(f'Total code genes in DB: {r[0]}')
for g in c.execute('SELECT gene_id, category, source, score, created_at FROM code_genes ORDER BY id DESC LIMIT 10'):
    print(json.dumps(list(g)))

print()
print('=== LAST INJECTION ===')
for r in c.execute('SELECT id, task, genes_found, genes_used, injection_prompt, result_score FROM gene_injections ORDER BY id DESC LIMIT 1'):
    print(f'ID: {r[0]}')
    print(f'Task: {r[1]}')
    print(f'Genes found: {r[2]}')
    print(f'Genes used: {r[3]}')
    prompt = str(r[4])[:500] if r[4] else 'None'
    print(f'Prompt preview: {prompt}')
    print(f'Score: {r[5]}')

conn.close()
