@echo off
chcp 65001 >nul
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 Docker CLI。请安装并启动 Docker Desktop。
  exit /b 1
)
if not exist ".env" (
  echo [错误] 缺少 .env。首次使用请双击 first-time.cmd。
  exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
  echo [错误] Docker Engine 未启动。请启动 Docker Desktop 后重试。
  exit /b 1
)
set PROJECT_RUNNING=
for /f %%C in ('docker compose --profile local-llm ps --status running -q 2^>nul') do set PROJECT_RUNNING=1
set OLLAMA_MODE=container
for /f %%M in ('powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\detect-ollama.ps1"') do set OLLAMA_MODE=%%M
if /i "%OLLAMA_MODE%"=="host-unavailable" (
  echo [警告] .env 选择复用本机 Ollama，但本机 Ollama 当前未运行。
  echo [提示] 将继续启动应用；模型功能暂不可用。启动 Ollama 后重新运行 start.cmd；不会切换模型目录或下载 Ollama。
  set OLLAMA_MODE=host
)
set OLLAMA_PORT_VALUE=11434
for /f "tokens=1,* delims==" %%A in ('findstr /b /c:"OLLAMA_PORT=" .env') do set OLLAMA_PORT_VALUE=%%B
if /i "%OLLAMA_MODE%"=="host" (
  set "OLLAMA_BASE_URL=http://host.docker.internal:%OLLAMA_PORT_VALUE%"
) else (
  set "OLLAMA_BASE_URL=http://ollama:11434"
)
if not defined PROJECT_RUNNING (
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\check-ports.ps1"
  if errorlevel 1 (
    echo [错误] 必需端口冲突。请停止占用进程或修改 .env 中的端口。
    exit /b 1
  )
)
if /i "%OLLAMA_MODE%"=="host" (
  echo 使用配置的本机 Ollama 地址，不会切换模型目录。
  docker compose up -d --wait --wait-timeout 300 backend frontend
) else (
  docker compose --profile local-llm up -d --wait --wait-timeout 300
)
if errorlevel 1 goto failed
echo 正在确认 Ollama、后端和前端可用...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$until=(Get-Date).AddSeconds(300); do { $ok=$true; foreach($u in @('http://localhost:8000/health','http://localhost:3000')) { try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 $u | Out-Null } catch { $ok=$false } }; if($ok){exit 0}; Start-Sleep 3 } while((Get-Date) -lt $until); exit 1"
if errorlevel 1 goto failed
echo 真知 Agent 已启动：http://localhost:3000
start "" "http://localhost:3000"
exit /b 0

:failed
echo [错误] 服务启动或健康检查失败。当前容器状态：
docker compose --profile local-llm ps
echo 后端最近 30 行日志：
docker compose logs --tail=30 backend
exit /b 1
