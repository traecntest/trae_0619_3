#!/bin/bash
# ============================================================
# 发票管理系统 - 初始化 PostgreSQL 数据库 (Linux/macOS)
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
echo -e "${CYAN}  发票管理系统 - 数据库初始化工具${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e ""

# 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 检查 PostgreSQL 服务
echo -e "${WHITE}[*] 检查 PostgreSQL 服务...${NC}"
if command -v pg_isready > /dev/null 2>&1; then
    if pg_isready -q 2>/dev/null; then
        echo -e "${GREEN}[OK] PostgreSQL 服务运行中${NC}"
    else
        echo -e "${YELLOW}[警告] PostgreSQL 未运行，尝试启动...${NC}"
        if command -v systemctl > /dev/null 2>&1; then
            sudo systemctl start postgresql
        elif command -v service > /dev/null 2>&1; then
            sudo service postgresql start
        elif [ "$(uname)" = "Darwin" ]; then
            if command -v brew > /dev/null 2>&1; then
                brew services start postgresql > /dev/null 2>&1 || true
            fi
        fi
        sleep 2
    fi
else
    echo -e "${YELLOW}[提示] 请确保 PostgreSQL 已启动${NC}"
fi

echo -e ""
echo -e "${WHITE}[*] 检查 Redis 服务...${NC}"
if command -v redis-cli > /dev/null 2>&1; then
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}[OK] Redis 运行中${NC}"
    else
        echo -e "${YELLOW}[警告] Redis 未运行，尝试启动...${NC}"
        if command -v systemctl > /dev/null 2>&1; then
            sudo systemctl start redis > /dev/null 2>&1 || true
        elif command -v service > /dev/null 2>&1; then
            sudo service redis start > /dev/null 2>&1 || true
        elif command -v redis-server > /dev/null 2>&1; then
            redis-server --daemonize yes > /dev/null 2>&1 || true
        fi
    fi
else
    echo -e "${YELLOW}[提示] 请确保 Redis 已启动 (redis-server)${NC}"
fi

echo -e ""
echo -e "${WHITE}[*] 初始化数据库...${NC}"

if python -m backend.core.db_initializer; then
    echo -e ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  数据库初始化完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e ""
    echo -e "后续步骤："
    echo -e "  启动后端:   ${WHITE}./start_backend.sh${NC}"
    echo -e "  启动Celery: ${WHITE}./start_celery.sh${NC}"
    echo -e "  启动桌面端: ${WHITE}./start_desktop.sh${NC}"
    echo -e "  一键启动:   ${WHITE}./start_full_system.sh${NC}"
    echo -e ""
else
    echo -e ""
    echo -e "${RED}[错误] 数据库初始化失败${NC}"
    echo -e ""
    echo -e "请检查："
    echo -e "  1. PostgreSQL 服务是否启动"
    echo -e "  2. .env 中的数据库配置是否正确"
    echo -e "  3. 数据库用户是否具有创建数据库的权限"
    echo -e ""
    exit 1
fi
