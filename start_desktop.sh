#!/bin/bash
# ============================================================
# 发票管理系统 - 启动 PySide6 桌面客户端 (Linux/macOS)
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  发票管理系统 - 桌面客户端${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e ""

# 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活虚拟环境
if [ -d "venv" ]; then
    echo -e "${GREEN}[信息] 激活虚拟环境...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${GREEN}[信息] 激活虚拟环境 (.venv)...${NC}"
    source .venv/bin/activate
fi

# 检查图形环境
if [ -z "$DISPLAY" ] && [ "$(uname)" != "Darwin" ]; then
    echo -e "${YELLOW}[警告] 未检测到图形环境 (DISPLAY 变量未设置)${NC}"
    echo -e "        桌面客户端需要图形界面支持。"
    echo -e "        如果您在远程服务器上运行，请使用 X11 Forwarding 或本地运行。"
    echo -e ""
fi

echo -e "${GREEN}[*] 启动 PySide6 桌面客户端...${NC}"
echo -e ""

exec python -m desktop.main "$@"
