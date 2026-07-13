#!/usr/bin/env python3
"""LGOX联邦燃料路由器 · Tier1 GLM→Tier4 DS Flash自动降级"""
import json, os, urllib.request
def _key(prefix):
    k = os.environ.get(prefix) or os.environ.get(prefix+'_KEY') or os.environ.get(prefix+'_API_KEY')
    if k: return k
    for f in [os.path.expanduser('~/.hermes/.env'), os.path.expanduser('~/lgox-ops/.env')]:
        if os.path.exists(f):
            for line in open(f):
                if prefix in line: return line.split('=',1)[1].strip().strip('"').strip("'")
    return ''
GLM_K = _key('ZHIPU_API'); DS_K = _key('DEEPSEEK_API')
def fuel_chat(prompt, max_tokens=None, temperature=None):
    if GLM_K:
        try:
            body = json.dumps({'model':'glm-4-flash','messages':[{'role':'user','content':prompt}],'max_tokens':max_tokens or 256,'temperature':temperature or 0.3}).encode()
            req = urllib.request.Request('https://open.bigmodel.cn/api/paas/v4/chat/completions',data=body,headers={'Authorization':f'Bearer {GLM_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req, timeout=12).read())
            return {'answer':d['choices'][0]['message']['content'].strip(),'model':'glm-4-flash','tokens':d['usage']['total_tokens'],'tier':'T1免费'}
        except: pass
    if DS_K:
        try:
            body = json.dumps({'model':'deepseek-v4-flash','messages':[{'role':'user','content':prompt}],'max_tokens':max_tokens or 1024,'temperature':temperature or 0.5}).encode()
            req = urllib.request.Request('https://api.deepseek.com/v1/chat/completions',data=body,headers={'Authorization':f'Bearer {DS_K}','Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req, timeout=15).read())
            return {'answer':d['choices'][0]['message']['content'].strip(),'model':'deepseek-v4-flash','tokens':d['usage']['total_tokens'],'tier':'T4付费兜底'}
        except: pass
    return None
if __name__ == '__main__':
    print(f"GLM:{'🟢' if GLM_K else '🔴'} DS:{'🟢' if DS_K else '🔴'}")
    r = fuel_chat('hi'); print(f"{'✅' if r else '❌'} {r['tier'] if r else ''} {r['tokens'] if r else ''}t")
