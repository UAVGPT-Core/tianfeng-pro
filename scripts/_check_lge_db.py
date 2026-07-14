#!/usr/bin/env python3
"""Check LGE local DB for gene count"""
import sqlite3, os, json

# Try local LGE sqlite DB
db_path = os.path.expanduser('/Users/a112233/lgox-ops/lge.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Check what tables exist
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print(f"Tables: {[t[0] for t in tables]}")
    for t in tables:
        try:
            c.execute(f"SELECT COUNT(*) FROM {t[0]}")
            print(f"  {t[0]}: {c.fetchone()[0]} rows")
        except:
            pass
    conn.close()
else:
    print(f"DB not found at {db_path}")

# Check local gene directory
genes_dir = '/Users/a112233/lgox-ops/genes'
if os.path.exists(genes_dir):
    files = [f for f in os.listdir(genes_dir) if f.endswith('.json')]
    print(f"Genes directory: {len(files)} JSON files")

# Check LGE meta
lge_meta = '/Users/a112233/lgox-ops/lge-genes/meta'
if os.path.exists(lge_meta):
    metas = os.listdir(lge_meta)
    print(f"LGE meta files: {metas[:10]}")
    for m in metas[:2]:
        mp = os.path.join(lge_meta, m)
        if os.path.isfile(mp):
            d = json.load(open(mp))
            print(f"  {m}: {json.dumps(d, indent=2)[:200]}")
