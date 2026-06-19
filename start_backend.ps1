# -*- coding: utf-8 -*-
<#
.SYNOPSIS
启动发票管理系统后端服务
#>

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  发票管理系统 - 后端服务启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not (Test-Path ".env")) {
    Write-Host "[!] .env 文件不存在，从 .env.example 复制..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[✓] 请修改 .env 配置文件后重新运行" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "[*] 检查 Python 虚拟环境..." -ForegroundColor Green
if (-not (Test-Path "venv")) {
    Write-Host "[*] 创建虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "[✓] 虚拟环境创建完成" -ForegroundColor Green
}

Write-Host "[*] 激活虚拟环境..." -ForegroundColor Green
& ".\venv\Scripts\Activate.ps1"

Write-Host "[*] 安装依赖..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host ""
Write-Host "[*] 启动 FastAPI 后端服务..." -ForegroundColor Green
Write-Host "[*] 服务地址: http://localhost:8000" -ForegroundColor Green
Write-Host "[*] API文档:   http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""

python -m backend.main
