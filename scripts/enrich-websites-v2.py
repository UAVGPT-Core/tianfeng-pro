#!/usr/bin/env python3
"""
无人机产业链 免费富化引擎 v2.0
==============================
对缺网址的企业：搜索引擎 → 提取官网
方法: DuckDuckGo HTML页面搜索 (免费,无需API Key)
策略: 公司名 site:com → 提取第一个URL
"""
import csv, json, re, urllib.request, urllib.parse, time, sys, os
from urllib.error import URLError, HTTPError

CHAIN_DIR = os.path.expanduser("~/lgox-ops/data/drone-chain")
UNIFIED_CSV = f"{CHAIN_DIR}/unified.csv"
OUTPUT_CSV = f"{CHAIN_DIR}/enrich/websites-enriched-{time.strftime('%Y%m%d-%H%M')}.csv"
LOG_FILE = f"/tmp/drone-enrich-{time.strftime('%Y%m%d-%H%M')}.log"

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def is_valid_url(s):
    """Check if string looks like a URL"""
    if not s or len(s) < 5:
        return False
    s = s.strip()
    # Must have a TLD or common patterns
    if re.match(r'^https?://', s):
        return True
    if re.search(r'\.[a-z]{2,}(/|$)', s):
        return True
    # Check if it's garbled data (product description, phone number, etc.)
    if re.search(r'[\u4e00-\u9fff]{6,}', s):  # >6 Chinese chars = likely product desc
        return False
    if re.match(r'^[\d\-\s()+]+$', s):  # purely phone number
        return False
    return '.' in s and len(s) < 200

def search_website_duckduckgo(company_name):
    """Search for company website using DuckDuckGo HTML (free, no API)"""
    query = urllib.parse.quote(f"{company_name} 官网")
    url = f"https://html.duckduckgo.com/html/?q={query}"
    
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        log(f"  ⚠️ 搜索失败 {company_name[:20]}: {e}")
        return ''
    
    # Extract result URLs (DuckDuckGo HTML format)
    urls = re.findall(r'class="result__url"[^>]*>(.*?)<', html, re.DOTALL)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)<', html, re.DOTALL)
    
    candidates = []
    for u in urls[:5]:
        u = re.sub(r'<[^>]+>', '', u).strip()
        u = u.replace(' ', '')
        # Filter out known non-official domains
        skip_domains = ['baidu.com', 'zhihu.com', 'weixin.qq.com', 'qixin.com',
                       'tianyancha.com', 'aiqicha.baidu.com', 'wikipedia.org',
                       'linkedin.com', 'facebook.com', 'youtube.com']
        if any(s in u for s in skip_domains):
            continue
        if u and not u.startswith('http'):
            u = 'https://' + u
        if u:
            candidates.append(u)
    
    return candidates[0] if candidates else ''

def extract_from_product_field(product_str):
    """Try to extract URL from product description field (for 2022-2024 data)"""
    if not product_str:
        return ''
    # Look for URLs in product description
    urls = re.findall(r'(https?://[^\s，,。]+|[a-z0-9][-a-z0-9]*\.[a-z]{2,}[^\s，,。]*)', product_str)
    if urls:
        for u in urls:
            u = u.strip('.,;，；。')
            if '.' in u and len(u) > 5:
                if not u.startswith('http'):
                    u = 'https://' + u
                return u
    return ''

def main():
    log("══════════════════════════════════")
    log(" 无人机产业链 免费富化引擎 v2.0")
    log("══════════════════════════════════")
    
    # Load unified CSV (Chinese headers)
    companies = []
    with open(UNIFIED_CSV, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            companies.append(row)
    
    total = len(companies)
    
    # Count who needs enrichment
    has_web = 0
    no_web = 0
    to_enrich = []
    
    for c in companies:
        web = c.get('网址', '').strip()
        if is_valid_url(web):
            has_web += 1
        else:
            # Try to extract from product field
            product = c.get('产品', '')
            extracted = extract_from_product_field(product)
            if extracted:
                c['网址'] = extracted
                has_web += 1
            else:
                no_web += 1
                to_enrich.append(c)
    
    log(f"总企业: {total}")
    log(f"已有网址: {has_web} ({100*has_web//total}%)")
    log(f"需富化: {no_web} ({100*no_web//total}%)")
    log(f"")
    
    # Prioritize: lower priority to high-value targets
    to_enrich.sort(key=lambda c: (
        int(c.get('浏览量', '0') or '0') > 100,
        c.get('合并状态', ''),  # actually '融合状态' in the new CSV
    ), reverse=True)
    
    # Enrich first N (limit to avoid rate limiting)
    BATCH_SIZE = 50
    batch = to_enrich[:BATCH_SIZE]
    
    log(f"本批次富化: {len(batch)}家 (免费DuckDuckGo搜索)")
    log(f"剩余 {len(to_enrich)-len(batch)} 家留待下次月度升级")
    log(f"")
    
    enriched = 0
    for i, c in enumerate(batch):
        name = c.get('公司名', '')
        if not name:
            continue
        
        log(f"  [{i+1}/{len(batch)}] 搜索: {name[:35]}")
        
        # Try DuckDuckGo search
        website = search_website_duckduckgo(name)
        
        if website:
            c['网址'] = website
            c['富化方法'] = 'DuckDuckGo免费搜索'
            c['富化时间'] = time.strftime('%Y-%m-%d')
            enriched += 1
            log(f"    ✅ {website[:60]}")
        else:
            # Mark as needing deeper search
            c['富化方法'] = '待深度搜索'
            log(f"    ❌ 未找到")
        
        # Be polite to the search engine
        if i % 5 == 4:
            time.sleep(1.5)
    
    log(f"\n✅ 本次富化: {enriched}/{len(batch)} ({100*enriched//len(batch)}%)")
    
    # Save enriched version
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    fieldnames = list(companies[0].keys()) + ['富化方法', '富化时间']
    
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies)
    
    log(f"📁 输出: {OUTPUT_CSV}")
    log(f"📁 日志: {LOG_FILE}")
    
    # Return summary
    return {
        'total': total,
        'has_web': has_web,
        'enriched_this_run': enriched,
        'remaining': len(to_enrich) - len(batch),
        'output': OUTPUT_CSV,
        'log': LOG_FILE
    }

if __name__ == '__main__':
    result = main()
    print("\n" + json.dumps(result, ensure_ascii=False))
