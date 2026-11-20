@echo off
chcp 65001 >nul
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (
  echo [错误] 请先安装 Docker Desktop。
  exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
  echo [错误] 请先启动 Docker Desktop。
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\init.ps1"
if errorlevel 1 exit /b 1
docker compose --profile local-llm build
if errorlevel 1 exit /b 1
call start.cmd
if errorlevel 1 exit /b 1
echo 首次准备本地模型 deepseek-r1:7b，下载时间取决于网络...
set MODEL_NAME=deepseek-r1:7b
for /f "tokens=1,* delims==" %%A in ('findstr /b /c:"OLLAMA_MODEL=" .env') do set MODEL_NAME=%%B
call model.cmd pull "%MODEL_NAME%"
if errorlevel 1 (
  echo [错误] 模型下载失败。可稍后运行 model.cmd pull "%MODEL_NAME%"。
  exit /b 1
)
echo 首次安装完成。
