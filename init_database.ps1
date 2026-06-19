# -*- coding: utf-8 -*-
<#
.SYNOPSIS
初始化发票管理系统数据库（检测并创建数据库、表结构）
#>

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  发票管理系统 - 数据库初始化" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (Test-Path "venv") {
    & ".\venv\Scripts\Activate.ps1"
}

python -m backend.core.db_initializer
