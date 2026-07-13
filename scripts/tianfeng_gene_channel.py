#!/usr/bin/env python3
"""天锋PRO 基因回流通路·公网级四路冗余"""
import json,sys,time,os,sqlite3,hashlib,platform,urllib.request
from pathlib import Path
from datetime import datetime
TD=Path.home()/".tianfeng/telemetry";TC=Path.home()/".tianfeng/telemetry_config.json"
PATHS=[{"name":"主路·CF","url":"https://stock.uavgpt.com/api/gene/ingest","timeout":10,"pri":1},{"name":"备路·地枢","url":"http://100.116.0.29:8200/genes/write","timeout":5,"pri":2},{"name":"底路·本地","url":"local://queue","timeout":1,"pri":4}]
def cfg():
    try:return json.loads(TC.open())
    except:return{"enabled":False,"anonymous_id":None}
def aid():
    c=cfg()
    if not c.get("anonymous_id"):import uuid;c["anonymous_id"]=str(uuid.uuid4())[:12];json.dump(c,TC.open("w"))
    return c.get("anonymous_id","?")
def send(gt,content):
    c=cfg()
    if not c.get("enabled"):return{"status":"disabled"}
    gd={"gene_type":gt,"content":content,"anonymous_id":aid(),"tianfeng_version":"5.1.0","platform":platform.platform()[:80],"timestamp":datetime.utcnow().isoformat()}
    for p in sorted(PATHS,key=lambda x:x["pri"]):
        try:
            if p["url"].startswith("local://"):_enqueue(gd);return{"status":"queued"}
            d=json.dumps(gd).encode();h={"Content-Type":"application/json"}
            if "genes/write" in p["url"]:h["X-LGE-Key"]="fbe0b015eb7a03727903b660c4cecc60"
            r=urllib.request.urlopen(urllib.request.Request(p["url"],data=d,headers=h),timeout=p["timeout"])
            if r.status in(200,201):return{"status":"ok","path":p["name"]}
        except:continue
    _enqueue(gd);return{"status":"queued"}
def _enqueue(gd):
    TD.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(str(TD/"queue.db"));c.execute("CREATE TABLE IF NOT EXISTS q(id INTEGER PRIMARY KEY AUTOINCREMENT,data TEXT,ts TEXT DEFAULT(datetime('now')))");c.execute("INSERT INTO q(data) VALUES(?)",(json.dumps(gd),));c.commit();c.close()
def flush():
    p=TD/"queue.db"
    if not p.exists():return 0
    c=sqlite3.connect(str(p));rows=c.execute("SELECT id,data FROM q LIMIT 20").fetchall();n=0
    for rid,data in rows:
        gd=json.loads(data)
        for pa in PATHS:
            try:
                if pa["url"].startswith("local://"):continue
                d=json.dumps(gd).encode();h={"Content-Type":"application/json"}
                if "genes/write" in pa["url"]:h["X-LGE-Key"]="fbe0b015eb7a03727903b660c4cecc60"
                r=urllib.request.urlopen(urllib.request.Request(pa["url"],data=d,headers=h),timeout=5)
                if r.status in(200,201):c.execute("DELETE FROM q WHERE id=?",(rid,));n+=1;break
            except:continue
    c.commit();c.close();return n
def status():
    c=cfg();print(f"遥测: {'🟢' if c.get('enabled') else '⚫'} ID:{aid()[:8]}...")
if __name__=="__main__":
    cmd=sys.argv[1] if len(sys.argv)>1 else"status"
    if cmd=="on":json.dump({"enabled":True,"anonymous_id":aid(),"consent_version":1},TC.open("w"));print("✅ 已开启")
    elif cmd=="off":json.dump({"enabled":False},TC.open("w"));print("🔒 已关闭")
    elif cmd=="status":status()
    elif cmd=="test":print(json.dumps(send("test","通道测试"),ensure_ascii=False))
    elif cmd=="flush":print(f"刷新:{flush()}条")
