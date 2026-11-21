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
set MODEL_NAME=deepseek-r1:7b
for /f "tokens=1,* delims==" %%A in ('findstr /b /c:"OLLAMA_MODEL=" .env') do set MODEL_NAME=%%B
set MODEL_PRESENT=
for /f "tokens=1" %%M in ('call model.cmd list ^| findstr /b /c:"%MODEL_NAME%"') do set MODEL_PRESENT=1
if defined MODEL_PRESENT (
  echo 已存在模型 %MODEL_NAME%，跳过下载。
) else (
  echo 未找到模型 %MODEL_NAME%，正在首次下载，时间取决于网络...
call model.cmd pull "%MODEL_NAME%"
if errorlevel 1 (
  echo [错误] 模型下载失败。可稍后运行 model.cmd pull "%MODEL_NAME%"。
  exit /b 1
)
)
echo 首次安装完成。
