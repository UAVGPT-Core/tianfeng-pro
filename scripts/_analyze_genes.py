#!/usr/bin/env python3
"""Analyze hot_genes to understand gene count"""
import sqlite3

db_path = '/Users/a112233/lgox-ops/data/gene-hotcache.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check hot_genes schema
c.execute("PRAGMA table_info(hot_genes)")
cols = c.fetchall()
print(f"hot_genes columns: {[(c[1], c[2]) for c in cols]}")

# Get a few rows
c.execute("SELECT * FROM hot_genes LIMIT 5")
rows = c.fetchall()
for r in rows:
    print(f"  {r}")

# Check total distinct genes
c.execute("SELECT COUNT(*) FROM hot_genes")
total = c.fetchone()[0]
print(f"\nTotal rows: {total}")

# Check for any count/summary data
c.execute("SELECT key, value FROM hot_genes WHERE key LIKE '%total%' OR key LIKE '%count%' OR key LIKE '%stat%' LIMIT 10")
rows = c.fetchall()
if rows:
    for r in rows:
        print(f"  {r}")
else:
    print("No count/summary keys found")

# Check the lga.db for gene counts
db_path2 = '/Users/a112233/lgox-ops/data/lga.db'
conn2 = sqlite3.connect(db_path2)
c2 = conn2.cursor()
c2.execute("PRAGMA table_info(genes)")
cols2 = c2.fetchall()
print(f"\nlga.db genes columns: {[(c[1], c[2]) for c in cols2]}")
c2.execute("SELECT COUNT(*) FROM genes")
cnt2 = c2.fetchone()[0]
print(f"  Total genes: {cnt2}")
c2.execute("SELECT * FROM genes LIMIT 3")
for r in c2.fetchall():
    print(f"  {r}")

conn.close()
conn2.close()
