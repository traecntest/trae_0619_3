# -*- coding: utf-8 -*-
<#
.SYNOPSIS
一键启动发票管理系统所有服务（后端 + Celery Worker）
#>

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  发票管理系统 - 一键启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (Test-Path "venv") {
    & ".\venv\Scripts\Activate.ps1"
}

Write-Host "[*] 启动 Redis 检查..." -ForegroundColor Green
try {
    $redisPing = redis-cli ping 2>$null
    if ($redisPing -eq "PONG") {
        Write-Host "[✓] Redis 运行正常" -ForegroundColor Green
    } else {
        Write-Host "[!] Redis 未运行，请启动 Redis 服务" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[!] 无法检测 Redis，请确保已安装并启动" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[*] 启动服务..." -ForegroundColor Green
Write-Host ""

$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:ProjectRoot
    if (Test-Path "venv") { & ".\venv\Scripts\Activate.ps1" }
    python -m backend.main
} -Name "BackendAPI"

$celeryJob = Start-Job -ScriptBlock {
    Set-Location $using:ProjectRoot
    if (Test-Path "venv") { & ".\venv\Scripts\Activate.ps1" }
    celery -A backend.core.celery_app.celery_app worker --loglevel=info --concurrency=4
} -Name "CeleryWorker"

Write-Host "========================================" -ForegroundColor Green
Write-Host "  服务启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  后端 API:    http://localhost:8000" -ForegroundColor White
Write-Host "  API 文档:    http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  启动桌面端:  .\start_desktop.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "  查看后端日志: Receive-Job BackendAPI -Keep" -ForegroundColor Gray
Write-Host "  查看Celery:   Receive-Job CeleryWorker -Keep" -ForegroundColor Gray
Write-Host "  停止服务:     Stop-Job BackendAPI, CeleryWorker" -ForegroundColor Gray
Write-Host ""
