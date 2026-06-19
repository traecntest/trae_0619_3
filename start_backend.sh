#!/bin/bash
# 启动发票管理系统后端服务

set -e

echo "========================================"
echo "  发票管理系统 - 后端服务启动脚本"
echo "========================================"
echo ""

cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
    echo "[!] .env 文件不存在，从 .env.example 复制..."
    cp .env.example .env
    echo "[✓] 请修改 .env 配置文件后重新运行"
    echo ""
fi

if [ -d "venv" ]; then
    source venv/bin/activate
fi

pip install -r requirements.txt

echo ""
echo "[*] 启动 FastAPI 后端服务..."
echo "[*] 服务地址: http://localhost:8000"
echo "[*] API文档:   http://localhost:8000/docs"
echo ""

python -m backend.main
