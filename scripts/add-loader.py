#!/usr/bin/env python3
"""补widget-loader到所有sub_filter </body>行"""
import re, subprocess, shutil

nginx_conf = "/opt/homebrew/etc/nginx/nginx.conf"
shutil.copy2(nginx_conf, nginx_conf + ".bak-v3")
print("备份完成")

with open(nginx_conf) as f:
    n = f.read()

lines = n.split('\n')
new_lines = []
added = 0

for line in lines:
    if "sub_filter" in line and "'</body>'" in line:
        if "widget-loader" not in line:
            # Add widget-loader before the existing content
            line = line.replace(
                "sub_filter '</body>' '",
                "sub_filter '</body>' '<script src=\\\"https://stock.uavgpt.com/public/public/js/widget-loader.js?v=1\\\"></script>"
            )
            added += 1
    new_lines.append(line)

n = '\n'.join(new_lines)
print(f"Added widget-loader to {added} lines")

with open(nginx_conf, "w") as f:
    f.write(n)

r = subprocess.run(["/opt/homebrew/bin/nginx", "-t"], capture_output=True, text=True)
if "syntax is ok" in r.stderr:
    print("✅ nginx -t OK")
    subprocess.run(["sudo", "/opt/homebrew/bin/nginx", "-s", "reload"])
    print("✅ reloaded")
else:
    print(f"❌ FAIL: {r.stderr[:300]}")
    shutil.copy2(nginx_conf + ".bak-v3", nginx_conf)
    print("已恢复备份")
