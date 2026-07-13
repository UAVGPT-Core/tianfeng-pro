#!/usr/bin/env python3
"""
大疆版本追踪 v1.0
每季度检查大疆SDK最新版本 + Release Notes更新
免费,零人类干预
"""
import urllib.request, json, re, time, os

VERSIONS_FILE = os.path.expanduser("~/lgox-ops/data/dji/versions.json")
KB_FILE = os.path.expanduser("~/lgox-ops/data/dji/dji-knowledge-base.md")

CHECK_URLS = {
    "cloud_api": "https://developer.dji.com/doc/cloud-api-tutorial/en/",
    "mobile_sdk": "https://developer.dji.com/doc/mobile-sdk-tutorial/en/",
    "edge_sdk": "https://developer.dji.com/doc/edge-sdk-tutorial/en/",
    "payload_sdk": "https://developer.dji.com/doc/payload-sdk-tutorial/en/",
}

def check_versions():
    """Check current versions from DJI developer site"""
    current = {}
    
    for name, url in CHECK_URLS.items():
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='replace')
            
            # Extract version numbers
            versions = re.findall(r'v?(\d+\.\d+\.\d+)', html)
            if versions:
                current[name] = versions[0]
            else:
                current[name] = "unknown"
        except Exception as e:
            current[name] = f"error: {e}"
    
    return current

def main():
    # Load previous
    previous = {}
    if os.path.exists(VERSIONS_FILE):
        with open(VERSIONS_FILE) as f:
            previous = json.load(f)
    
    # Check current
    current = check_versions()
    
    # Compare
    changed = []
    for name in CHECK_URLS:
        prev = previous.get(name, "none")
        curr = current.get(name, "unknown")
        if prev != curr and curr != "unknown":
            changed.append(f"{name}: {prev} → {curr}")
    
    # Save
    current['last_check'] = time.strftime('%Y-%m-%d')
    with open(VERSIONS_FILE, 'w') as f:
        json.dump(current, f, indent=2)
    
    # Report
    report = f"""
📡 大疆版本追踪 {time.strftime('%Y-%m-%d %H:%M')}
{'='*50}
Cloud API:  {current.get('cloud_api', '?')}
Mobile SDK: {current.get('mobile_sdk', '?')}
Edge SDK:   {current.get('edge_sdk', '?')}
Payload SDK:{current.get('payload_sdk', '?')}

{'🔄 版本变更: ' + ', '.join(changed) if changed else '✅ 无变化'}
"""
    print(report)
    
    # If changed, flag for human review
    if changed:
        print("⚠️ 版本变更! 需检查Release Notes并更新知识库")
        print(f"   手动复查: https://developer.dji.com/cloud-api/")

if __name__ == '__main__':
    main()
