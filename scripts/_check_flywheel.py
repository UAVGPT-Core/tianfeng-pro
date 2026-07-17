#!/usr/bin/env python3
import sqlite3
from pathlib import Path

HOME = Path.home()
db_path = HOME / "lgox-ops/data/gene-coding-flywheel.db"

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    # Get schema
    tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("Tables:", [t[0] for t in tables])
    
    for tname, in tables:
        print(f"\n=== {tname} schema ===")
        cols = c.execute(f"PRAGMA table_info({tname})").fetchall()
        for col in cols:
            print(f"  {col}")
    
    # Check flywheel_runs
    print("\n=== 最近 run_id 和 score ===")
    rows = c.execute('SELECT run_id, genes_searched, genes_injected, new_genes, score, duration_ms, created_at FROM flywheel_runs ORDER BY id DESC LIMIT 15').fetchall()
    for r in rows:
        print(f"  {r[0][:28]:30s} | 搜{r[1]} 注{r[2]} 新{r[3]} | {r[4]:.0f}分 | {r[5]}ms | {r[6]}")
    
    print(f"\n总计: {c.execute('SELECT COUNT(*) FROM flywheel_runs').fetchone()[0]} runs")
    print(f"代码基因: {c.execute('SELECT COUNT(*) FROM code_genes').fetchone()[0]} genes")
    
    conn.close()
else:
    print("DB not found!")
