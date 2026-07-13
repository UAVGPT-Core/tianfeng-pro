#!/usr/bin/env python3
"""
无人机产业链 每日慢富化 v1.0
==========================
每天搜5家企业官网，BrowserAct浏览器搜 → 提取第一结果。
慢慢积累，不花钱。
"""
import csv, json, os, re, time, sys
import subprocess

CHAIN_DIR = os.path.expanduser("~/lgox-ops/data/drone-chain")
UNIFIED_CSV = f"{CHAIN_DIR}/unified.csv"
ENRICH_DIR = f"{CHAIN_DIR}/enrich"
STATE_FILE = f"{ENRICH_DIR}/daily-enrich-state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'last_index': 0, 'enriched_count': 0, 'last_run': None}

def save_state(state):
    os.makedirs(ENRICH_DIR, exist_ok=True)
    state['last_run'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def is_valid_url(s):
    """Quick check if URL looks like a real website"""
    if not s or len(s) < 5:
        return False
    if 'http' in s or re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-z]{2,}', s):
        return True
    return False

def main():
    # Load unified DB
    companies = []
    with open(UNIFIED_CSV, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            companies.append(row)
    
    state = load_state()
    start = state['last_index']
    
    # Find next 5 companies needing websites
    to_search = []
    i = start
    while len(to_search) < 5 and i < len(companies):
        c = companies[i]
        web = c.get('网址', '').strip()
        name = c.get('公司名', '').strip()
        if name and not is_valid_url(web):
            to_search.append((i, name))
        i += 1
    
    if not to_search:
        print("✅ 所有企业已完成富化(或已到末尾)")
        state['last_index'] = 0  # reset
        save_state(state)
        return
    
    print(f"每日慢富化: 搜索 {len(to_search)} 家")
    
    enriched = 0
    for idx, name in to_search:
        print(f"  🔍 {name[:35]}")
        
        # Use BrowserAct stealth-extract to search
        # Search on Baidu: 公司名 官网
        try:
            # Use curl to baidu search since BrowserAct is heavy
            import urllib.request, urllib.parse
            query = urllib.parse.quote(f"{name} 官网 site:com")
            
            # Try Bing (more lenient than Baidu)
            req = urllib.request.Request(
                f"https://www.bing.com/search?q={query}&setlang=zh-cn",
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'zh-CN,zh;q=0.9'
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='replace')
            
            # Extract first organic result URL
            # Bing format: <cite>domain.com</cite> or <a> with target URL
            cites = re.findall(r'<cite[^>]*>(.*?)</cite>', html)
            if cites:
                domain = re.sub(r'<[^>]+>', '', cites[0]).strip()
                if domain and '.' in domain and 'bing.com' not in domain:
                    if not domain.startswith('http'):
                        domain = 'https://' + domain
                    companies[idx]['网址'] = domain
                    companies[idx]['富化来源'] = 'Bing搜索'
                    companies[idx]['富化时间'] = time.strftime('%Y-%m-%d')
                    enriched += 1
                    print(f"    ✅ {domain[:60]}")
                    state['enriched_count'] += 1
                    continue
            
            # Check if we were blocked (bot detection)
            if 'captcha' in html.lower() or 'challenge' in html.lower() or 'robot' in html.lower() or len(html) < 1000:
                print(f"    🚫 搜索引擎封锁(bot检测/验证码) — 脚本需升级到API方案")
            elif len(cites) == 0:
                print(f"    ❌ 未找到(Bing返回0结果)")
            else:
                print(f"    ❌ 未找到")
            
        except Exception as e:
            err = str(e)
            if 'HTTP Error 403' in err:
                print(f"    🚫 Bing拒绝访问(403 Forbidden)")
            elif 'HTTP Error 429' in err:
                print(f"    🚫 Bing限流(429 Too Many Requests)")
            else:
                print(f"    ⚠️ {err[:50]}")
        
        time.sleep(2)  # polite delay
    
    # Save updated CSV
    fieldnames = list(companies[0].keys())
    for fn in ['富化来源', '富化时间']:
        if fn not in fieldnames:
            fieldnames.append(fn)
    
    enriched_csv = f"{ENRICH_DIR}/daily-enrich-{time.strftime('%Y%m%d-%H%M')}.csv"
    with open(enriched_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies)
    
    # Update state
    state['last_index'] = i
    save_state(state)
    
    print(f"\n✅ 本次: {enriched}/{len(to_search)} | 累计: {state['enriched_count']}")
    print(f"   下次从第{state['last_index']}家开始")

if __name__ == '__main__':
    main()
