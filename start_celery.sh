#!/bin/bash
# ============================================================
# 发票管理系统 - 启动 Celery Worker 异步任务处理服务 (Linux/macOS)
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
echo -e "${CYAN}  发票管理系统 - Celery Worker${NC}"
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

echo -e ""
echo -e "${GREEN}[*] 启动 Celery Worker...${NC}"
echo -e "${WHITE}    Broker:  redis://localhost:6379/1${NC}"
echo -e "${WHITE}    Backend: redis://localhost:6379/2${NC}"
echo -e ""

exec celery -A backend.core.celery_app.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    -Q invoice_parse,invoice_verify,invoice_archive,invoice_default \
    "$@"
