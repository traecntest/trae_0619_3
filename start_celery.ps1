# -*- coding: utf-8 -*-
<#
.SYNOPSIS
启动 Celery Worker 异步任务处理服务
#>

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  发票管理系统 - Celery Worker" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (Test-Path "venv") {
    & ".\venv\Scripts\Activate.ps1"
}

Write-Host "[*] 启动 Celery Worker..." -ForegroundColor Green
Write-Host "[*] Broker:  redis://localhost:6379/1" -ForegroundColor Green
Write-Host "[*] Backend: redis://localhost:6379/2" -ForegroundColor Green
Write-Host ""

celery -A backend.core.celery_app.celery_app worker `
    --loglevel=info `
    --concurrency=4 `
    -Q invoice_parse,invoice_verify,invoice_archive,invoice_default
