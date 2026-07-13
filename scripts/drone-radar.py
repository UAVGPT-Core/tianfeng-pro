#!/usr/bin/env python3
"""
无人机产业链 活体雷达 v1.0
=======================
功能: 持续扫描互联网无人机产业新信息
扫描源:
  1. 36氪/虎嗅 低空经济 tag
  2. 百度新闻 无人机/低空经济
  3. 企查查/天眼查 新注册无人机公司
  4. UASE展会官网 (每年5月更新)
  5. 无人机网 (uav.cn) 行业资讯
  
输出: LGE基因库 + drone-chain/enrich/ 增量CSV
频率: 每6小时 (cron)
成本: $0 (全免费源)
"""
import json, csv, re, time, os, sys
import urllib.request, urllib.parse
from datetime import datetime, timedelta

# ═══ 配置 ═══
CHAIN_DIR = os.path.expanduser("~/lgox-ops/data/drone-chain")
ENRICH_DIR = f"{CHAIN_DIR}/enrich"
RADAR_LOG = "/tmp/drone-radar.log"
RADAR_STATE = f"{ENRICH_DIR}/radar-state.json"

# 免费扫描源（优选中国大陆可达、中文内容丰富的源）
SOURCES = {
    "sogou_news": {
        "name": "搜狗新闻-无人机低空",
        "url": "https://news.sogou.com/news?query=%E6%97%A0%E4%BA%BA%E6%9C%BA+%E4%BD%8E%E7%A9%BA%E7%BB%8F%E6%B5%8E&sort=1",
        "type": "news",
        "parser": "html_title"
    },
    "baidu_news_drone": {
        "name": "百度新闻-无人机",
        "url": "https://news.baidu.com/ns?word=%E6%97%A0%E4%BA%BA%E6%9C%BA+%E4%BD%8E%E7%A9%BA%E7%BB%8F%E6%B5%8E&pn=0&cl=2&ct=1&tn=news&rn=20",
        "type": "news",
        "parser": "html_title"
    },
    "baidu_news_evtol": {
        "name": "百度新闻-eVTOL",
        "url": "https://news.baidu.com/ns?word=eVTOL+%E9%A3%9E%E8%A1%8C%E6%B1%BD%E8%BD%A6&pn=0&cl=2&ct=1&tn=news&rn=10",
        "type": "news",
        "parser": "html_title"
    }
}

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(RADAR_LOG, 'a') as f:
        f.write(line + '\n')

def fetch_url(url, timeout=10):
    """Fetch URL with browser UA to avoid blocking"""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        log(f"  ⚠️ {url[:60]}... 不可达: {e}")
        return ''

def scan_36kr():
    """Scan 36Kr for low-altitude economy news"""
    html = fetch_url(SOURCES["36kr_lowalt"]["url"])
    if not html:
        return []
    
    # Extract article titles and URLs
    articles = []
    # 36Kr search results contain article cards
    titles = re.findall(r'<a[^>]*class="article-item-title[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
    
    for url, title_raw in titles[:10]:
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        if title and len(title) > 4:
            articles.append({
                'source': '36氪',
                'title': title,
                'url': url if url.startswith('http') else f'https://36kr.com{url}',
                'date': time.strftime('%Y-%m-%d'),
                'tags': ['低空经济', '无人机']
            })
    return articles

def scan_baidu_news_evtol():
    """Scan Baidu News for eVTOL news"""
    html = fetch_url(SOURCES["baidu_news_evtol"]["url"])
    if not html:
        return []
    return scan_baidu_news_internal(html, '百度新闻-eVTOL', ['eVTOL', '飞行汽车'])

def scan_baidu_news_internal(html, source_name, tags):
    """Parse Baidu News HTML"""
    if not html:
        return []
    articles = []
    results = re.findall(r'<a[^>]*href="(https?://[^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
    for url, title_raw in results[:15]:
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        if title and len(title) > 6 and '百度' not in title and '新闻' not in title:
            articles.append({
                'source': source_name,
                'title': title,
                'url': url,
                'date': time.strftime('%Y-%m-%d'),
                'tags': tags
            })
    return articles

def scan_baidu_news():
    """Scan Baidu News for drone industry"""
    html = fetch_url(SOURCES["baidu_news_drone"]["url"])
    return scan_baidu_news_internal(html, '百度新闻', ['无人机'])

def scan_sogou_news():
    """Scan Sogou News for drone/low-altitude economy"""
    html = fetch_url(SOURCES["sogou_news"]["url"])
    if not html:
        return []
    
    articles = []
    # Sogou news results: look for result titles
    titles = re.findall(r'<h3[^>]*class="[^"]*vr-title[^"]*"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
    if not titles:
        # Alternative pattern
        titles = re.findall(r'<a[^>]*href="(https?://[^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
    
    for url, title_raw in titles[:15]:
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        # Filter out nav/ads
        skip_keywords = ['搜狗', '下一页', '上一页', '登录', '注册', '首页']
        if title and len(title) > 6 and not any(k in title for k in skip_keywords):
            articles.append({
                'source': '搜狗新闻',
                'title': title,
                'url': url if url.startswith('http') else url,
                'date': time.strftime('%Y-%m-%d'),
                'tags': ['无人机', '低空经济']
            })
    return articles

def detect_new_companies(articles):
    """Detect new company names from article titles"""
    new_companies = []
    # Pattern: XX公司/XX科技/XX航空/XX智能
    company_pattern = re.compile(r'([\u4e00-\u9fff]{2,10}(?:公司|科技|航空|智能|无人机|飞行器|通航))')
    
    for a in articles:
        matches = company_pattern.findall(a['title'])
        for m in matches:
            if len(m) >= 4:
                new_companies.append({
                    'name': m,
                    'found_in': a['title'],
                    'source_url': a['url'],
                    'source_name': a['source'],
                    'date': a['date']
                })
    
    return new_companies

def load_state():
    """Load radar state (last scan time, known companies)"""
    if os.path.exists(RADAR_STATE):
        with open(RADAR_STATE) as f:
            return json.load(f)
    return {'last_scan': None, 'articles_count': 0, 'companies_found': 0}

def save_state(state):
    os.makedirs(os.path.dirname(RADAR_STATE), exist_ok=True)
    state['last_scan'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(RADAR_STATE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def save_results(all_articles, new_companies):
    """Save scan results to enrich directory"""
    os.makedirs(ENRICH_DIR, exist_ok=True)
    ts = time.strftime('%Y%m%d-%H%M')
    
    # Articles
    art_file = f"{ENRICH_DIR}/radar-articles-{ts}.json"
    with open(art_file, 'w') as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    
    # New company leads
    if new_companies:
        leads_file = f"{ENRICH_DIR}/radar-new-leads-{ts}.csv"
        
        # Load existing leads
        all_leads_file = f"{ENRICH_DIR}/radar-all-leads.csv"
        existing_names = set()
        if os.path.exists(all_leads_file):
            with open(all_leads_file, encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    existing_names.add(row.get('name', ''))
        
        new_count = 0
        with open(leads_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['公司名', '发现来源', '来源URL', '时间'])
            for c in new_companies:
                if c['name'] not in existing_names:
                    writer.writerow([c['name'], c['found_in'], c['source_url'], c['date']])
                    new_count += 1
        
        # Append to all leads
        file_exists = os.path.exists(all_leads_file)
        with open(all_leads_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['公司名', '发现来源', '来源URL', '时间'])
            for c in new_companies:
                if c['name'] not in existing_names:
                    writer.writerow([c['name'], c['found_in'], c['source_url'], c['date']])
        
        return new_count, leads_file, art_file
    
    return 0, None, art_file

def generate_report(all_articles, new_count, state):
    """Generate a summary report"""
    report = f"""
╔══════════════════════════════════╗
║  🛸 无人机产业链雷达扫描报告    ║
╠══════════════════════════════════╣
║  时间: {time.strftime('%Y-%m-%d %H:%M')}
║  上次扫描: {state.get('last_scan', '首次')}
╠══════════════════════════════════╣
║  文章抓取: {len(all_articles)}篇
║  新线索: {new_count}家
╠══════════════════════════════════╣
"""
    for a in all_articles[:5]:
        report += f"║  📰 [{a['source']}] {a['title'][:40]}\n"
    
    report += """╚══════════════════════════════════╝
"""
    return report

def main():
    log("╔══════════════════════════════════╗")
    log("║  🛸 无人机产业链 活体雷达 v1.0 ║")
    log("╚══════════════════════════════════╝")
    
    state = load_state()
    all_articles = []
    
    # Scan all sources
    sources = {
        '搜狗新闻': scan_sogou_news,
        '百度新闻-无人机': scan_baidu_news,
        '百度新闻-eVTOL': lambda: scan_baidu_news_evtol(),
    }
    
    for name, scanner in sources.items():
        try:
            log(f"  📡 扫描 {name}...")
            articles = scanner()
            all_articles.extend(articles)
            log(f"     → {len(articles)}篇")
        except Exception as e:
            log(f"     ⚠️ 异常: {e}")
    
    # Detect new companies
    new_companies = detect_new_companies(all_articles)
    log(f"  🏢 检测到 {len(new_companies)} 个潜在新公司名")
    
    # Save results
    new_count, leads_file, art_file = save_results(all_articles, new_companies)
    
    # Update state
    state['articles_count'] = state.get('articles_count', 0) + len(all_articles)
    state['companies_found'] = state.get('companies_found', 0) + new_count
    save_state(state)
    
    # Report
    report = generate_report(all_articles, new_count, state)
    log(report)
    
    # Write LGE gene (if LGE is available)
    try:
        gene_content = json.dumps({
            'type': 'drone_radar_scan',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'articles': len(all_articles),
            'new_leads': new_count,
            'top_articles': [a['title'][:80] for a in all_articles[:3]],
            'report': report
        }, ensure_ascii=False)
        
        # Try LGE write (port 8200 on localhost or 地枢)
        req = urllib.request.Request(
            'http://127.0.0.1:8200/genes',
            data=gene_content.encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            urllib.request.urlopen(req, timeout=3)
            log("  🧬 LGE基因写入成功")
        except:
            log("  ⚠️ LGE不可达(本地),尝试地枢...")
    except Exception as e:
        log(f"  ⚠️ LGE写入跳过: {e}")
    
    log(f"\n✅ 雷达扫描完成")
    log(f"  文章: {len(all_articles)} | 新线索: {new_count}")
    log(f"  数据: {ENRICH_DIR}/")
    
    return {
        'articles': len(all_articles),
        'new_leads': new_count,
        'leads_file': leads_file,
        'articles_file': art_file
    }

if __name__ == '__main__':
    main()
