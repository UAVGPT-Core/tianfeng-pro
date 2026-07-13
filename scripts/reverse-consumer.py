#!/usr/bin/env python3
"""灵龙反向消化 v1.1 · 每分钟消化天枢回复 → audit.db + 自动纳基因"""
import os, sqlite3, time, glob, json, subprocess

INBOX = os.path.expanduser("~/lgox-ops/inbox")
AUDIT_DB = os.path.expanduser("~/lgox-ops/data/comm-audit.db")
PROCESSED = os.path.join(INBOX, ".digested")
GENE_PROXY = "http://localhost:8778/gene/write"

os.makedirs(os.path.dirname(AUDIT_DB), exist_ok=True)
db = sqlite3.connect(AUDIT_DB)
db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, msg_id TEXT UNIQUE, direction TEXT, sender TEXT, receiver TEXT, content TEXT, ts TEXT, digested_at TEXT, gene_id TEXT)")
try:
    db.execute("SELECT gene_id FROM messages LIMIT 1")
except:
    db.execute("ALTER TABLE messages ADD COLUMN gene_id TEXT")
db.commit()

def write_gene(title, content, tags=None, fitness=0.9):
    """curl子进程调用gene/write代理(避免urllib超时)"""
    payload = json.dumps({
        "domain": "general", "title": title, "content": content,
        "tags": tags or ["federation"], "fitness": fitness,
        "source": "灵龙reverse-consumer v1.1自动纳基因"
    }, ensure_ascii=False)
    try:
        r = subprocess.run(["curl","-s","--max-time","4","-X","POST",GENE_PROXY,
            "-H","Content-Type: application/json","-d",payload],
            capture_output=True, text=True, timeout=6)
        if r.returncode == 0 and r.stdout:
            d = json.loads(r.stdout)
            return d.get("gene_id","")
    except Exception as e:
        return f"ERR:{e}"
    return ""

def extract_gene_from_msg(content):
    """从消息内容提取基因，支持TYPE:gene_write JSON块和关键段落"""
    genes = []
    if 'TYPE:gene_write' in content or '"title"' in content:
        try:
            s = content.find('{'); e = content.rfind('}')
            if s>=0 and e>s:
                d = json.loads(content[s:e+1])
                if 'title' in d and 'content' in d:
                    genes.append(d)
        except: pass
    if '唯一缺口' in content or '纳基因' in content:
        genes.append({"title":"联邦通讯·基因闭环修复",
            "content":content[:600],"tags":["federation","gene"],"fitness":0.92})
    return genes

processed = set()
if os.path.exists(PROCESSED):
    with open(PROCESSED) as f:
        processed = set(line.strip() for line in f)

new = 0; gw = 0
for fp in sorted(glob.glob(f"{INBOX}/from-tianshu-*")):
    fn = os.path.basename(fp)
    if fn in processed: continue
    try:
        with open(fp,'rb') as f: c = f.read().decode('utf-8',errors='replace')
        mid = c.split('"message_id":"')[1].split('"')[0] if '"message_id":"' in c else None
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        gid = ""
        for g in extract_gene_from_msg(c):
            gid0 = write_gene(g.get("title",""),g.get("content",""),g.get("tags"),g.get("fitness",0.9))
            if gid0 and not gid0.startswith("ERR:"):
                gid = gid0; gw += 1
        db.execute("INSERT OR IGNORE INTO messages VALUES (NULL,?,?,?,?,?,?,?,?)",
            (mid,"RECV","天枢","灵龙",c[:500],now,now,gid))
        db.commit()
        processed.add(fn); new += 1
    except: pass

with open(PROCESSED,'w') as f:
    for p in sorted(processed): f.write(p+'\n')

t = db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
g = db.execute("SELECT COUNT(*) FROM messages WHERE gene_id != '' AND gene_id NOT LIKE 'ERR:%'").fetchone()[0]
db.close()
if new or gw:
    print(f"[{time.strftime('%H:%M')}] +{new}条 审计{t}条 纳基因{g}条")
