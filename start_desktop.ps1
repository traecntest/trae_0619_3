# -*- coding: utf-8 -*-
<#
.SYNOPSIS
启动发票管理系统桌面客户端
#>

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  发票管理系统 - 桌面客户端" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (Test-Path "venv") {
    & ".\venv\Scripts\Activate.ps1"
}

Write-Host "[*] 启动 PySide6 桌面客户端..." -ForegroundColor Green
Write-Host ""

python -m desktop.main
