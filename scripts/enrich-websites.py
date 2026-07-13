#!/usr/bin/env python3
"""批量富化无人机供应商名录 - 搜索官网"""
import csv, urllib.request, urllib.parse, re, json, time, sys

def search_website(company_name):
    """搜索公司官网"""
    queries = [
        f"{company_name} 官网",
        f"{company_name} 官方网站",
        f"{company_name} site",
    ]
    for q in queries[:1]:
        try:
            query = urllib.parse.quote(q)
            req = urllib.request.Request(
                f"https://html.duckduckgo.com/html/?q={query}",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            r = urllib.request.urlopen(req, timeout=8)
            html = r.read().decode('utf-8','ignore')
            
            # Extract links
            links = re.findall(r'class="result__url"[^>]*>\s*(.*?)\s*<', html)
            for link in links[:3]:
                link = re.sub(r'<[^>]+>', '', link).strip()
                if link and '.' in link and not 'duckduckgo' in link:
                    if not link.startswith('http'):
                        link = 'https://' + link
                    return link
        except:
            time.sleep(0.5)
    return ''

def main():
    if len(sys.argv) < 3:
        print("Usage: enrich_websites.py input.csv output.csv")
        return
    
    with open(sys.argv[1]) as f:
        rows = list(csv.DictReader(f))
    
    for r in rows:
        if not r.get('网站','').strip():
            site = search_website(r['公司名'])
            if site:
                r['网站'] = site
                print(f"✅ {r['公司名'][:30]} → {site}")
            time.sleep(1.5)
    
    with open(sys.argv[2], 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(rows[0].keys())
        for r in rows:
            w.writerow(r.values())
    
    print(f"Done: {sys.argv[2]}")

if __name__ == '__main__':
    main()
