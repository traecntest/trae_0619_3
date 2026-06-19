# -*- coding: utf-8 -*-
<#
.SYNOPSIS
发票管理系统 - 完整启动脚本
启动顺序: PostgreSQL → Redis → 后端API → Celery Worker → 桌面客户端

.EXAMPLE
.\start_full_system.ps1
启动所有服务（后端+Celery+桌面端）

.EXAMPLE
.\start_full_system.ps1 -BackendOnly
仅启动后端服务（API + Celery）

.EXAMPLE
.\start_full_system.ps1 -DesktopOnly
仅启动桌面客户端
#>

param(
    [switch]$BackendOnly,
    [switch]$DesktopOnly
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  发票管理系统 v1.0.0 - 完整启动" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (Test-Path "venv") {
    Write-Host "[信息] 激活虚拟环境..." -ForegroundColor Green
    & ".\venv\Scripts\Activate.ps1"
}

if (-not $DesktopOnly) {
    Write-Host ""
    Write-Host "[步骤 1/5] 检查环境..." -ForegroundColor Yellow

    Write-Host "[1/3] 检查 PostgreSQL..." -ForegroundColor Gray
    try {
        $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
        if ($pgService) {
            $running = $pgService | Where-Object { $_.Status -eq "Running" }
            if ($running) {
                Write-Host "[OK] PostgreSQL 服务运行中" -ForegroundColor Green
            } else {
                Write-Host "[警告] PostgreSQL 服务未运行" -ForegroundColor Yellow
                Write-Host "       请启动 PostgreSQL 服务后继续" -ForegroundColor Yellow
            }
        } else {
            Write-Host "[警告] 未检测到 PostgreSQL 服务" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[提示] 请确保 PostgreSQL 已启动" -ForegroundColor Yellow
    }

    Write-Host "[2/3] 检查 Redis..." -ForegroundColor Gray
    try {
        $redisRunning = Get-Process redis-server -ErrorAction SilentlyContinue
        if ($redisRunning) {
            Write-Host "[OK] Redis 运行中" -ForegroundColor Green
        } else {
            Write-Host "[警告] Redis 未运行" -ForegroundColor Yellow
            Write-Host "       请启动 Redis 服务: redis-server" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[提示] 请确保 Redis 已启动" -ForegroundColor Yellow
    }

    Write-Host "[3/3] 检查数据库..." -ForegroundColor Gray
    try {
        python -m backend.core.db_initializer
    } catch {
        Write-Host "[警告] 数据库初始化失败，请检查配置" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "[步骤 2/5] 启动后端 API 服务..." -ForegroundColor Yellow
    Write-Host "         API 地址: http://localhost:8000" -ForegroundColor White
    Write-Host "         API 文档: http://localhost:8000/docs" -ForegroundColor White

    $backendJob = Start-Job -ScriptBlock {
        Set-Location $using:ProjectRoot
        if (Test-Path "venv") { & ".\venv\Scripts\Activate.ps1" }
        python -m backend.main 2>&1
    } -Name "BackendAPI"

    Write-Host "[OK] 后端服务已启动 (PID: $($backendJob.Id))" -ForegroundColor Green

    Start-Sleep -Seconds 3

    Write-Host ""
    Write-Host "[步骤 3/5] 启动 Celery Worker..." -ForegroundColor Yellow

    $celeryJob = Start-Job -ScriptBlock {
        Set-Location $using:ProjectRoot
        if (Test-Path "venv") { & ".\venv\Scripts\Activate.ps1" }
        celery -A backend.core.celery_app.celery_app worker --loglevel=info --concurrency=4 2>&1
    } -Name "CeleryWorker"

    Write-Host "[OK] Celery Worker 已启动 (PID: $($celeryJob.Id))" -ForegroundColor Green

    Start-Sleep -Seconds 2
}

if (-not $BackendOnly) {
    Write-Host ""
    Write-Host "[步骤 4/5] 启动 PySide6 桌面客户端..." -ForegroundColor Yellow
    Write-Host "         这将打开图形界面窗口" -ForegroundColor White

    $desktopProcess = Start-Process python -ArgumentList "-m desktop.main" -PassThru

    Write-Host "[OK] 桌面客户端已启动 (PID: $($desktopProcess.Id))" -ForegroundColor Green

    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "[步骤 5/5] 系统启动完成！" -ForegroundColor Green
Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  服务管理命令：" -ForegroundColor White
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
if (-not $DesktopOnly) {
    Write-Host "  查看后端日志:   Receive-Job BackendAPI -Keep" -ForegroundColor Gray
    Write-Host "  查看Celery日志: Receive-Job CeleryWorker -Keep" -ForegroundColor Gray
    Write-Host "  停止后端服务:   Stop-Job BackendAPI, CeleryWorker" -ForegroundColor Gray
}
Write-Host "  停止桌面端:     关闭窗口或 Stop-Process $($desktopProcess.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  使用说明：" -ForegroundColor White
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  1. 桌面端会自动检测后端服务连接状态" -ForegroundColor White
Write-Host "  2. 如果后端未启动，桌面端会显示离线模式（模拟数据）" -ForegroundColor White
Write-Host "  3. 后端服务启动后，桌面端会自动切换到真实数据" -ForegroundColor White
Write-Host "  4. 三个功能标签页：发票管理 / 发票导入 / 数据统计" -ForegroundColor White
Write-Host ""
Write-Host "  发票导入支持格式: PDF, JPG, JPEG, PNG, BMP, TIFF, OFD" -ForegroundColor White
Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""

if (-not $DesktopOnly) {
    Write-Host "[提示] 按 Ctrl+C 停止后台服务，或使用 Stop-Job 命令" -ForegroundColor Yellow
    Write-Host ""

    try {
        $jobs = @()
        if (Get-Job -Name BackendAPI -ErrorAction SilentlyContinue) { $jobs += "BackendAPI" }
        if (Get-Job -Name CeleryWorker -ErrorAction SilentlyContinue) { $jobs += "CeleryWorker" }

        if ($jobs.Count -gt 0) {
            Write-Host "[后台服务运行中...] 等待服务结束，或按 Ctrl+C 退出" -ForegroundColor Yellow
            Wait-Job -Name $jobs
        }
    } catch {
        Write-Host ""
        Write-Host "[信息] 正在停止后台服务..." -ForegroundColor Yellow
        Get-Job -Name BackendAPI, CeleryWorker -ErrorAction SilentlyContinue | Stop-Job
        Write-Host "[完成] 所有后台服务已停止" -ForegroundColor Green
    }
}
