#!/usr/bin/env python3
"""天锋PRO 审批工作流·吸收OpenClaw exec-approval"""
import re,os
DANGEROUS=[(r"rm\s+-rf","🔴递归删除"),(r"sudo\s","🔴超级用户"),(r"chmod\s+777","🔴开放权限"),(r"curl.*\|.*(sh|bash)","🔴管道执行"),(r"mkfs\.","🔴格式化磁盘"),(r">\s*/etc/","🔴系统配置")]
MODE_FILE=os.path.expanduser("~/.tianfeng/approval_mode")
def get_mode():
    try:return open(MODE_FILE).read().strip()
    except:return "smart"
def set_mode(m):os.makedirs(os.path.dirname(MODE_FILE),exist_ok=True);open(MODE_FILE,"w").write(m);return m
def check_danger(cmd):
    for p,r in DANGEROUS:
        if re.search(p,cmd,re.I):return True,r
    return False,""
def require_approval(cmd,ctx="",interactive=True):
    d,r=check_danger(cmd)
    if not d:return True
    m=get_mode()
    if m=="off":return True
    if interactive:
        print(f"\n⚠ {r}\n   {cmd[:80]}")
        return input("  执行? [y/N]: ").strip().lower()=='y'
    return False
