#!/usr/bin/env python3
"""Check LGE cached data from various sources"""
import json, os, re, sqlite3

# Check lge_mirror.db
db_path = '/Users/a112233/lgox-ops/data/lge_mirror.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    print(f"lge_mirror.db tables: {tables}")
    for t in tables:
        try:
            c.execute(f"SELECT * FROM \"{t}\" LIMIT 5")
            rows = c.fetchall()
            cols = [desc[0] for desc in c.description]
            print(f"  {t}: cols={cols}, rows={len(rows)}")
            if rows:
                print(f"    {rows[0]}")
        except Exception as e:
            print(f"  {t}: error={e}")
    conn.close()
else:
    print("lge_mirror.db not found")

# Check lge.db
db_path2 = '/Users/a112233/lgox-ops/lge.db'
if os.path.exists(db_path2):
    conn = sqlite3.connect(db_path2)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    print(f"\nlge.db tables: {tables}")
    conn.close()
else:
    print("\nlge.db not found or empty")

# Check gene_ingest.db for last known counts
db_path3 = '/Users/a112233/lgox-ops/data/gene_ingest.db'
if os.path.exists(db_path3):
    conn = sqlite3.connect(db_path3)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    print(f"\ngene_ingest.db tables: {tables}")
    for t in tables:
        c.execute(f"SELECT * FROM \"{t}\"")
        rows = c.fetchall()
        print(f"  {t}: {rows}")
    conn.close()

# Check gene-hotcache.db for count
db_path4 = '/Users/a112233/lgox-ops/data/gene-hotcache.db'
if os.path.exists(db_path4):
    conn = sqlite3.connect(db_path4)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    print(f"\ngene-hotcache.db tables: {tables}")
    for t in tables:
        if t.startswith('hot_genes') and not t.endswith('_fts'):
            c.execute(f"SELECT COUNT(*) FROM \"{t}\"")
            cnt = c.fetchone()[0]
            print(f"  {t}: {cnt} rows")
    conn.close()
