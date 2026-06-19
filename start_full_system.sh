#!/bin/bash
# ============================================================
# 发票管理系统 - 完整启动脚本 (Linux/macOS)
# 启动顺序: 环境检查 → 数据库初始化 → 后端API → Celery Worker → 桌面客户端
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BLUE='\033[0;34m'
NC='\033[0m'

# 模式选项
BACKEND_ONLY=false
DESKTOP_ONLY=false

# 解析参数
for arg in "$@"; do
    case $arg in
        --backend-only|-b)
            BACKEND_ONLY=true
            shift
            ;;
        --desktop-only|-d)
            DESKTOP_ONLY=true
            shift
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  -b, --backend-only    仅启动后端服务 (API + Celery)"
            echo "  -d, --desktop-only    仅启动桌面客户端"
            echo "  -h, --help            显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                  # 启动全部服务 (后端 + 桌面端)"
            echo "  $0 -b               # 仅启动后端"
            echo "  $0 -d               # 仅启动桌面端"
            exit 0
            ;;
    esac
done

# 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo -e ""
echo -e "${CYAN}==============================================${NC}"
echo -e "${CYAN}  发票管理系统 v1.0.0 - 完整启动${NC}"
echo -e "${CYAN}==============================================${NC}"
echo -e ""

# 创建 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[!] .env 文件不存在，从 .env.example 复制...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}[!] 请根据实际环境修改 .env 配置${NC}"
fi

# PID 文件目录
PID_DIR="$SCRIPT_DIR/.pids"
mkdir -p "$PID_DIR"

# 日志目录
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

# 清理函数
cleanup() {
    echo -e ""
    echo -e "${YELLOW}[*] 正在停止所有服务...${NC}"

    if [ -f "$PID_DIR/backend.pid" ]; then
        BACKEND_PID=$(cat "$PID_DIR/backend.pid")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            kill "$BACKEND_PID" 2>/dev/null
            echo -e "${GREEN}[OK] 后端服务已停止 (PID: $BACKEND_PID)${NC}"
        fi
        rm -f "$PID_DIR/backend.pid"
    fi

    if [ -f "$PID_DIR/celery.pid" ]; then
        CELERY_PID=$(cat "$PID_DIR/celery.pid")
        if kill -0 "$CELERY_PID" 2>/dev/null; then
            kill "$CELERY_PID" 2>/dev/null
            echo -e "${GREEN}[OK] Celery Worker 已停止 (PID: $CELERY_PID)${NC}"
        fi
        rm -f "$PID_DIR/celery.pid"
    fi

    if [ -f "$PID_DIR/desktop.pid" ]; then
        DESKTOP_PID=$(cat "$PID_DIR/desktop.pid")
        if kill -0 "$DESKTOP_PID" 2>/dev/null; then
            kill "$DESKTOP_PID" 2>/dev/null || true
        fi
        rm -f "$PID_DIR/desktop.pid"
    fi

    echo -e "${GREEN}==============================================${NC}"
    echo -e "${GREEN}  所有服务已停止${NC}"
    echo -e "${GREEN}==============================================${NC}"
    echo -e ""
}
trap cleanup EXIT INT TERM

if [ "$DESKTOP_ONLY" = false ]; then
    echo -e ""
    echo -e "${YELLOW}[步骤 1/5] 环境检查...${NC}"

    # 检查 PostgreSQL
    echo -e "${WHITE}[1/3] 检查 PostgreSQL...${NC}"
    if command -v pg_isready > /dev/null 2>&1; then
        if pg_isready -q 2>/dev/null; then
            echo -e "${GREEN}[OK] PostgreSQL 服务运行中${NC}"
        else
            echo -e "${YELLOW}[警告] PostgreSQL 未运行，尝试启动...${NC}"
            if command -v systemctl > /dev/null 2>&1; then
                sudo systemctl start postgresql 2>/dev/null || true
            elif command -v service > /dev/null 2>&1; then
                sudo service postgresql start 2>/dev/null || true
            elif [ "$(uname)" = "Darwin" ] && command -v brew > /dev/null 2>&1; then
                brew services start postgresql 2>/dev/null || true
            fi
            sleep 2
        fi
    else
        echo -e "${YELLOW}[提示] 请确保 PostgreSQL 已启动${NC}"
    fi

    # 检查 Redis
    echo -e "${WHITE}[2/3] 检查 Redis...${NC}"
    if command -v redis-cli > /dev/null 2>&1; then
        if redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN}[OK] Redis 运行中${NC}"
        else
            echo -e "${YELLOW}[警告] Redis 未运行，尝试启动...${NC}"
            if command -v systemctl > /dev/null 2>&1; then
                sudo systemctl start redis 2>/dev/null || true
            elif command -v service > /dev/null 2>&1; then
                sudo service redis start 2>/dev/null || true
            elif command -v redis-server > /dev/null 2>&1; then
                redis-server --daemonize yes 2>/dev/null || true
            fi
            sleep 1
        fi
    else
        echo -e "${YELLOW}[提示] 请确保 Redis 已启动 (redis-server)${NC}"
    fi

    # 检查并初始化数据库
    echo -e "${WHITE}[3/3] 检查数据库...${NC}"
    python -m backend.core.db_initializer 2>/dev/null || {
        echo -e "${YELLOW}[提示] 请确认 PostgreSQL 和 Redis 已启动${NC}"
    }

    # 启动后端 API
    echo -e ""
    echo -e "${YELLOW}[步骤 2/5] 启动后端 API 服务...${NC}"
    echo -e "${WHITE}         API 地址: http://localhost:8000${NC}"
    echo -e "${WHITE}         API 文档: http://localhost:8000/docs${NC}"

    nohup python -m backend.main > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$PID_DIR/backend.pid"
    echo -e "${GREEN}[OK] 后端服务已启动 (PID: $BACKEND_PID)${NC}"
    echo -e "${GREEN}     日志文件: $LOG_DIR/backend.log${NC}"

    sleep 3

    # 启动 Celery Worker
    echo -e ""
    echo -e "${YELLOW}[步骤 3/5] 启动 Celery Worker...${NC}"

    nohup celery -A backend.core.celery_app.celery_app worker \
        --loglevel=info \
        --concurrency=4 \
        -Q invoice_parse,invoice_verify,invoice_archive,invoice_default \
        > "$LOG_DIR/celery.log" 2>&1 &
    CELERY_PID=$!
    echo "$CELERY_PID" > "$PID_DIR/celery.pid"
    echo -e "${GREEN}[OK] Celery Worker 已启动 (PID: $CELERY_PID)${NC}"
    echo -e "${GREEN}     日志文件: $LOG_DIR/celery.log${NC}"

    sleep 2
fi

if [ "$BACKEND_ONLY" = false ]; then
    echo -e ""
    echo -e "${YELLOW}[步骤 4/5] 启动 PySide6 桌面客户端...${NC}"
    echo -e "${WHITE}         这将打开图形界面窗口${NC}"

    # 检查图形环境
    if [ -z "$DISPLAY" ] && [ "$(uname)" != "Darwin" ]; then
        echo -e "${YELLOW}[警告] 未检测到图形环境${NC}"
        echo -e "        桌面客户端将在无显示模式下启动，可能无法正常显示窗口"
    fi

    python -m desktop.main > "$LOG_DIR/desktop.log" 2>&1 &
    DESKTOP_PID=$!
    echo "$DESKTOP_PID" > "$PID_DIR/desktop.pid"
    echo -e "${GREEN}[OK] 桌面客户端已启动 (PID: $DESKTOP_PID)${NC}"
    echo -e "${GREEN}     日志文件: $LOG_DIR/desktop.log${NC}"
fi

echo -e ""
echo -e "${GREEN}[步骤 5/5] 系统启动完成！${NC}"
echo -e ""
echo -e "${CYAN}==============================================${NC}"
echo -e "${CYAN}  服务管理命令：${NC}"
echo -e "${CYAN}==============================================${NC}"
echo -e ""

if [ "$DESKTOP_ONLY" = false ]; then
    echo -e "  ${WHITE}查看后端日志:  ${BLUE}tail -f $LOG_DIR/backend.log${NC}"
    echo -e "  ${WHITE}查看Celery日志:${BLUE}tail -f $LOG_DIR/celery.log${NC}"
fi
if [ "$BACKEND_ONLY" = false ]; then
    echo -e "  ${WHITE}查看桌面日志:  ${BLUE}tail -f $LOG_DIR/desktop.log${NC}"
fi
echo -e "  ${WHITE}停止所有服务:  ${BLUE}Ctrl+C${NC}"
echo -e ""

echo -e "${CYAN}==============================================${NC}"
echo -e "${CYAN}  使用说明：${NC}"
echo -e "${CYAN}==============================================${NC}"
echo -e ""
echo -e "  1. 桌面端会自动检测后端服务连接状态"
echo -e "  2. 如果后端未启动，桌面端显示离线模式（模拟数据）"
echo -e "  3. 后端服务启动后，桌面端自动切换到真实数据"
echo -e "  4. 三个功能标签页：发票管理 / 发票导入 / 数据统计"
echo -e ""
echo -e "  发票导入支持格式: PDF, JPG, JPEG, PNG, BMP, TIFF, OFD"
echo -e ""
echo -e "${CYAN}==============================================${NC}"
echo -e ""
echo -e "${YELLOW}[提示] 按 Ctrl+C 停止所有服务${NC}"
echo -e ""

# 等待所有子进程
wait
