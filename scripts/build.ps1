#requires -Version 5.1
<#
.SYNOPSIS
    构建 Windows 桌面程序（默认文件夹版，可用 -OneFile 生成单文件）。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\build.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\build.ps1 -OneFile
#>

param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root

try {
    Write-Host "==> 检查 Python" -ForegroundColor Cyan
    python --version
    if ($LASTEXITCODE -ne 0) {
        throw "未找到 Python，请先安装 Python 3.10+ 并加入 PATH。"
    }

    Write-Host "==> 运行单元测试" -ForegroundColor Cyan
    $env:PYTHONUTF8 = "1"
    python -m unittest discover -s tests -t . -v
    if ($LASTEXITCODE -ne 0) {
        throw "单元测试失败，已中止打包。"
    }

    Write-Host "==> 安装打包依赖" -ForegroundColor Cyan
    python -m pip install --disable-pip-version-check -q pyinstaller pillow
    if ($LASTEXITCODE -ne 0) {
        throw "安装 PyInstaller / Pillow 失败。"
    }

    Write-Host "==> 生成图标" -ForegroundColor Cyan
    python scripts\generate_icon.py
    if ($LASTEXITCODE -ne 0) {
        throw "生成图标失败。"
    }

    Write-Host "==> PyInstaller 打包" -ForegroundColor Cyan
    $arguments = @(
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name", "恐鬼症启动器",
        "--icon", "assets\app.ico",
        "--version-file", "assets\version_info.txt",
        "--add-data", "assets;assets",
        "--paths", "src",
        "main.py"
    )
    if ($OneFile) {
        $arguments += "--onefile"
    }
    else {
        $arguments += "--onedir"
    }

    python -m PyInstaller @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 打包失败。"
    }

    if ($OneFile) {
        $exe = Join-Path $root "dist\恐鬼症启动器.exe"
        if (-not (Test-Path $exe)) {
            throw "未找到打包产物：$exe"
        }
        Write-Host ""
        Write-Host "构建完成：$exe" -ForegroundColor Green
        Get-Item $exe | Select-Object FullName, Length, LastWriteTime | Format-List
    }
    else {
        $folder = Join-Path $root "dist\恐鬼症启动器"
        $exe = Join-Path $folder "恐鬼症启动器.exe"
        if (-not (Test-Path $exe)) {
            throw "未找到打包产物：$exe"
        }
        $zip = Join-Path $root "dist\恐鬼症启动器-windows-x64.zip"
        if (Test-Path $zip) {
            Remove-Item $zip -Force
        }
        Compress-Archive -Path $folder -DestinationPath $zip -CompressionLevel Optimal
        Write-Host ""
        Write-Host "构建完成：" -ForegroundColor Green
        Write-Host "  文件夹：$folder"
        Write-Host "  压缩包：$zip"
        Get-Item $exe | Select-Object FullName, Length, LastWriteTime | Format-List
    }
}
finally {
    Pop-Location
}
