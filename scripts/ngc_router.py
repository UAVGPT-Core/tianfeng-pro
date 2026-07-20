#!/usr/bin/env python3
"""NGC智能路由引擎 v1.0 -- 联邦飞轮的免费燃料"""
import json, os, time, urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

NV_URL = 'https://integrate.api.nvidia.com/v1'

WORKING_MODELS = {
    'fast': [
        'meta/llama-3.2-3b-instruct', 'meta/llama-3.2-1b-instruct',
        'google/gemma-2-2b-it', 'mistralai/mistral-7b-instruct-v0.3',
    ],
    'medium': [
        'meta/llama-3.1-8b-instruct', 'deepseek-ai/deepseek-v4-flash',
        'google/gemma-3-4b-it', 'nvidia/llama-3.1-nemotron-nano-8b-v1',
        'mistralai/mistral-large-2-instruct', 'stepfun-ai/step-3.5-flash',
        'google/gemma-3n-e2b-it', 'google/gemma-3n-e4b-it',
    ],
    'slow': [
        'deepseek-ai/deepseek-v4-pro', 'meta/llama-3.1-70b-instruct',
        'meta/llama-3.3-70b-instruct', 'nvidia/llama-3.1-nemotron-70b-instruct',
        'google/gemma-3-12b-it', 'nvidia/nemotron-3-nano-30b-a3b',
        'nvidia/nemotron-4-340b-instruct', 'qwen/qwen3.5-397b-a17b',
    ],
}

ALL_MODELS = []
for v in WORKING_MODELS.values():
    ALL_MODELS.extend(v)

def get_ngc_key():
    for k in [os.environ.get('NVIDIA_API_KEY',''), os.environ.get('NVIDIA_NIM_API_KEY','')]:
        if k: return k
    for p in [os.path.expanduser('~/.hermes/.env'), os.path.expanduser('~/.bashrc')]:
        if os.path.exists(p):
            for l in open(p):
                if 'NVIDIA_API_KEY' in l and 'nvapi' in l:
                    return l.split('=',1)[1].strip().strip("'").strip('"')
            for l in open(p):
                if 'NVIDIA_NIM_API_KEY' in l and 'nvapi' in l:
                    return l.split('=',1)[1].strip().strip("'").strip('"')
    return ''

def call(model, messages, max_tokens=256, temperature=0.7, timeout=60):
    nk = get_ngc_key()
    if not nk: return None
    body = json.dumps({'model':model,'messages':messages,'max_tokens':max_tokens,'temperature':temperature}).encode()
    req = urllib.request.Request(NV_URL+'/chat/completions', data=body,
        headers={'Authorization':'Bearer '+nk,'Content-Type':'application/json'})
    d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return d.get('choices',[{}])[0].get('message',{}).get('content','').strip()

def smart_call(prompt, system='', max_tokens=256, tier='auto', temperature=0.7):
    if tier == 'auto':
        if len(prompt) < 100:
            tier = 'fast'
        elif len(prompt) < 500:
            tier = 'medium'
        else:
            tier = 'slow'
    models = WORKING_MODELS.get(tier, ALL_MODELS)
    messages = [{'role':'user','content':prompt}]
    if system:
        messages.insert(0, {'role':'system','content':system})
    h = datetime.now().hour
    start_idx = (h * 7) % len(models)
    for offset in range(len(models)):
        model = models[(start_idx + offset) % len(models)]
        try:
            c = call(model, messages, max_tokens, temperature)
            if c and len(c) > 10:
                return c
        except:
            continue
    return None

def probe_models(max_workers=10):
    nk = get_ngc_key()
    if not nk: return []
    try:
        req = urllib.request.Request(NV_URL+'/models', headers={'Authorization':'Bearer '+nk})
        d = json.loads(urllib.request.urlopen(req).read())
        candidates = [m['id'] for m in d.get('data',[])]
    except:
        candidates = ALL_MODELS
    print('Probing ' + str(len(candidates)) + ' models...')
    working = []
    def probe(m):
        try:
            body = json.dumps({'model':m,'messages':[{'role':'user','content':'hi'}],'max_tokens':8}).encode()
            t0=time.time()
            req = urllib.request.Request(NV_URL+'/chat/completions', data=body,
                headers={'Authorization':'Bearer '+nk,'Content-Type':'application/json'})
            d = json.loads(urllib.request.urlopen(req, timeout=15).read())
            t=time.time()-t0
            if d.get('choices'):
                return (m, True, t)
        except:
            pass
        return (m, False, 0)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fs = {ex.submit(probe, m):m for m in candidates}
        for f in as_completed(fs):
            m, ok, t = f.result()
            if ok:
                short = m.rsplit('/',1)[-1]
                working.append((m, t))
                print('  + ' + short + ' ' + str(round(t,1)) + 's')
    working.sort(key=lambda x: x[1])
    print('Available: ' + str(len(working)) + '/' + str(len(candidates)))
    return [m for m,_ in working]

def gene_produce(topic, tier='fast'):
    prompt = 'Write a technical gene about: ' + topic + '. Max 200 chars. Chinese.'
    c = smart_call(prompt, max_tokens=200, tier=tier)
    if not c or len(c) < 30: return None
    lge_url = os.environ.get('LGE_URL', 'http://100.116.0.29:8200')
    ldata = json.dumps({'content':c[:500],'memory_type':'semantic','source':'ngc-router','tags':['ngc','gene']}).encode()
    try:
        lreq = urllib.request.Request(lge_url+'/genes/write', data=ldata, headers={'Content-Type':'application/json'})
        lr = json.loads(urllib.request.urlopen(lreq, timeout=10).read())
        return lr.get('gene_id','?')
    except:
        return None

if __name__ == '__main__':
    import sys
    key_ok = bool(get_ngc_key())
    print('NGC Router | Key:' + ('OK' if key_ok else 'MISS') + ' | Models:' + str(len(ALL_MODELS)))
    if '--probe' in sys.argv:
        probe_models()
    else:
        for tier, models in WORKING_MODELS.items():
            names = [m.rsplit('/',1)[-1] for m in models]
            print('  ' + tier + '(' + str(len(models)) + '): ' + ', '.join(names))
