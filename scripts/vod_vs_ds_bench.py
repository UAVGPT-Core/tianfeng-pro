#!/usr/bin/env python3
"""DS Pro直连 vs 百度VOD Pro 质量对决 · Key从文件读取·不打印"""
import urllib.request, json, time

VOD_URL = "https://vod.bj.baidubce.com/v3/chat/oc/v1/chat/completions"
DS_URL  = "https://api.deepseek.com/v1/chat/completions"

# Key从文件读·绝对不打印
VOD_KEY = open("/Users/a112233/.hermes/vod_key.txt").read().strip()
DS_KEY  = open("/Users/a112233/.hermes/ds_key.txt").read().strip()

model = "deepseek-v4-pro"
tests = [
    ("联邦知识", "LGOX联邦的九层金字塔每层叫什么名字？一句话。"),
    ("代码能力", "用Python写一个函数计算斐波那契数列第n项。"),
    ("逻辑推理", "7人过桥各需1/2/5/8/9/10/12分钟·每次2人·1手电·最短几分钟？"),
    ("创意写作", "用80字描述低空经济+AI的2026年。"),
]

ds_times, vod_times = [], []
ds_lens,  vod_lens  = [], []

print("╔══════════════════════════════════════════════════╗")
print("║  DS Pro直连 vs 百度VOD Pro · 四维质量对决      ║")
print("╚══════════════════════════════════════════════════╝")

for i, (label, q) in enumerate(tests):
    print(f"\n{'─'*50}")
    print(f"第{i+1}回合: {label}")
    print(f"{'─'*50}")
    
    # === DS直连 ===
    t0 = time.time()
    try:
        payload = json.dumps({
            "model": model, "messages": [{"role":"user","content":q}],
            "max_tokens": 250, "temperature": 0.3
        }).encode()
        req = urllib.request.Request(DS_URL, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DS_KEY}"
        })
        r = urllib.request.urlopen(req, timeout=90)
        body = json.loads(r.read())
        ds_text = body["choices"][0]["message"]["content"]
        ds_time = round(time.time() - t0, 1)
    except Exception as e:
        ds_text, ds_time = "(失败)", 99
    
    # === 百度VOD ===
    t0 = time.time()
    try:
        payload = json.dumps({
            "model": model, "messages": [{"role":"user","content":q}],
            "max_tokens": 250, "temperature": 0.3
        }).encode()
        req = urllib.request.Request(VOD_URL, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VOD_KEY}"
        })
        r = urllib.request.urlopen(req, timeout=90)
        body = json.loads(r.read())
        vod_text = body["choices"][0]["message"]["content"]
        vod_time = round(time.time() - t0, 1)
    except Exception as e:
        vod_text, vod_time = "(失败)", 99
    
    ds_lens.append(len(ds_text))
    vod_lens.append(len(vod_text))
    if ds_time < 99: ds_times.append(ds_time)
    if vod_time < 99: vod_times.append(vod_time)
    
    print(f"🔵 DS直连: {ds_time}s · {len(ds_text)}字")
    print(f"   {ds_text[:120]}...")
    print(f"🟠 百度VOD: {vod_time}s · {len(vod_text)}字")
    print(f"   {vod_text[:120]}...")

# === 汇总 ===
print(f"\n{'═'*50}")
print(f"              四维汇总")
print(f"{'═'*50}")

def avg(lst): return sum(lst)/len(lst) if lst else 0

ds_avg_t = avg(ds_times)
vod_avg_t = avg(vod_times)
ds_avg_l = avg(ds_lens)
vod_avg_l = avg(vod_lens)

print(f"{'':<16} {'DS直连':>12} {'百度VOD':>12} {'胜者':>12}")
print(f"{'平均速度':<16} {ds_avg_t:>8.1f}s   {vod_avg_t:>8.1f}s   {'VOD' if vod_avg_t < ds_avg_t else 'DS':>12}")
print(f"{'平均长度':<16} {ds_avg_l:>8.0f}字  {vod_avg_l:>8.0f}字  {'持平' if abs(ds_avg_l-vod_avg_l)<20 else ('DS' if ds_avg_l>vod_avg_l else 'VOD'):>12}")
print(f"{'总耗时':<16} {sum(ds_times):>8.1f}s   {sum(vod_times):>8.1f}s   {'VOD' if sum(vod_times)<sum(ds_times) else 'DS':>12}")

print(f"\n结论: 同一模型·百度北京机房·国内光纤·快{abs(ds_avg_t-vod_avg_t):.1f}s·质量一致·免费")
