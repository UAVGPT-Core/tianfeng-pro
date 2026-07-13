#!/usr/bin/env python3
"""天锋PRO 开源飞轮·GitHub+PyPI指标采集→基因进化"""
import json,time,os,sys,urllib.request
from pathlib import Path
R="UAVGPT-Core/tianfeng-pro";P="tianfeng-pro-lgox"
D=Path.home()/"lgox-ops/data/opensource";M=D/"opensource-metrics.json"
def fetch(u):
    try:return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"tianfeng"})))
    except:return{}
def collect():
    D.mkdir(parents=True,exist_ok=True)
    gh=fetch(f"https://api.github.com/repos/{R}")
    pi=fetch(f"https://pypi.org/pypi/{P}/json")
    m={"time":time.strftime("%m%d-%H%M"),"github":{"stars":gh.get("stargazers_count",0),"forks":gh.get("forks_count",0),"issues":gh.get("open_issues_count",0)},"pypi":{"version":pi.get("info",{}).get("version","?"),"downloads":"N/A"}}
    json.dump(m,M.open("w"),ensure_ascii=False,indent=2)
    try:
        import subprocess
        subprocess.run(["scp","-i",str(Path.home()/".ssh/id_ed25519"),"-o","IdentitiesOnly=yes","-o","ConnectTimeout=5",str(M),"a1@100.100.89.2:/Volumes/990Pro/public-web/data/opensource-metrics.json"],capture_output=True,timeout=15)
    except:pass
    return m
if __name__=="__main__":
    r=collect()
    print(f"⭐{r['github']['stars']} 🍴{r['github']['forks']} 📥{r['pypi']['version']}")
