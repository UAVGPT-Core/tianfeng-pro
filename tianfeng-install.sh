#!/bin/bash
# 天锋PRO v5.0 一键安装脚本
# curl -sL https://stock.uavgpt.com/scripts/tianfeng-install.sh | bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
GOLD='\033[0;33m'
NC='\033[0m'

echo -e "${GOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║  天锋PRO v5.0 · 一键安装                   ║"
echo "║  LGOX联邦旗舰产品 · 9引擎融合              ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# 检测平台
OS=$(uname -s)
echo -e "${CYAN}[1/4]${NC} 检测平台: $OS"

# 检查Python
if command -v python3 &>/dev/null; then
    PY=$(python3 --version 2>&1)
    echo -e "${GREEN}✓${NC} Python: $PY"
else
    echo -e "${RED}✗${NC} 需要 Python 3.9+"
    exit 1
fi

# pip安装
echo -e "${CYAN}[2/4]${NC} 安装天锋PRO..."
pip3 install tianfeng-pro-lgox==5.0.0 2>/dev/null || {
    echo -e "${GOLD}⚠${NC} PyPI未发布，从源码安装..."
    TMPDIR=$(mktemp -d)
    cd "$TMPDIR"
    curl -sL https://stock.uavgpt.com/scripts/tianfeng-pro-lgox.tar.gz -o tianfeng-pro-lgox.tar.gz 2>/dev/null || {
        echo -e "${RED}✗${NC} 下载失败，请手动安装: https://stock.uavgpt.com/tianfeng"
        exit 1
    }
    tar xzf tianfeng-pro-lgox.tar.gz
    cd tianfeng-pro
    pip3 install -e . --quiet
    cd /
    rm -rf "$TMPDIR"
}

echo -e "${GREEN}✓${NC} 天锋PRO v5.0.0 已安装"

# 验证
echo -e "${CYAN}[3/4]${NC} 验证安装..."
if command -v tianfeng &>/dev/null; then
    tianfeng version
    echo -e "${GREEN}✓${NC} CLI可用"
else
    echo -e "${RED}✗${NC} CLI未找到，检查PATH"
    exit 1
fi

# 完成
echo ""
echo -e "${CYAN}[4/4]${NC} ${GREEN}安装完成！${NC}"
echo ""
echo -e "  快速开始:"
echo -e "    ${GOLD}tianfeng code \"写一个Python爬虫\"${NC}"
echo -e "    ${GOLD}tianfeng review app.py${NC}"
echo -e "    ${GOLD}tianfeng dashboard${NC}"
echo ""
echo -e "  文档: ${CYAN}https://stock.uavgpt.com/tianfeng${NC}"
echo -e "  源码: ${CYAN}https://github.com/lgox/tianfeng-pro${NC}"
echo ""
