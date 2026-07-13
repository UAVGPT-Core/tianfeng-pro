# BrowserAct 联邦调用技能

## 能力
- browser-act v1.0.1 已安装于灵龙
- AI Agent浏览器自动化CLI
- 三层反封锁: 环境伪装→验证码自动→人工接管
- Skill Forge: 自动生成站点Scraper

## 联邦调用
天枢及联邦节点通过SSH调用:
```bash
ssh a1@100.100.89.2 ~/lgox-ops/scripts/browser-act-wrapper.sh <cmd>
```

## 常用命令
```bash
# 提取受保护页面
browser-act stealth-extract https://example.com
# 完整浏览器自动化
browser-act --session task1 browser open stealth1 https://example.com
browser-act --session task1 state
browser-act --session task1 click 3
# 获取技能指引
browser-act get-skills core --skill-version 2.0.2
```

## 成本
- 免费版 ≤5 stealth浏览器
- 零外部API费用
- 自建代理可$0运行
